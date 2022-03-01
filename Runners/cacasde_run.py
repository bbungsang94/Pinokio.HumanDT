import math
import pickle
import copy
import time

import Runners.general_runner
from Runners.general_runner import AbstractRunner
from utilities.helpers import DictToStruct, post_iou_checker, draw_box_label, get_distance
from utilities.media_handler import ImageManager, PipeliningVideoManager
from utilities.projection_helper import ProjectionManager
from Detectors import REGISTRY as det_REGISTRY
from Trackers import REGISTRY as trk_REGISTRY
from utilities.state_manager import StateDecisionMaker


class CascadeRunner(AbstractRunner):
    def __init__(self, args, logger=None):
        self.__VideoMap = args['video_list']
        self.__VideoHandles = []
        self.__ImageHandle = ImageManager()
        self.__save = args['save']
        self.__oldReservedTrkLen = dict()

        plan_image = ImageManager.load_cv(args['plan_path'])
        self.FrameRate = 60
        self.SingleImageSize = None
        self.WholeImageSize = None
        self.MaxWidthIdx = 0
        self.OutputImages = {'raw_image': [], 'detected_image': [],
                             'tracking_image': [], 'plan_image': plan_image}

        self.DockInRegion = dict()
        with open(args['projection_path'] + "DockEntrance.pickle", 'rb') as f:
            self.DockInRegion = pickle.load(f)

        self.Matrices = dict()
        count = 0
        for row, videos in self.__VideoMap.items():
            for idx, video_name in enumerate(videos):
                (name, extension) = video_name.split('.')
                video_handle = PipeliningVideoManager()
                frame_rate, image_size = video_handle.load_video(args['video_path'] + video_name)
                video_handle.activate_video_object(args['output_base_path'] + args['run_name'] + video_name)
                video_handle.video_name = name
                if frame_rate < self.FrameRate:
                    self.FrameRate = frame_rate
                if self.WholeImageSize is None:
                    self.WholeImageSize = image_size
                    self.SingleImageSize = image_size

                self.__VideoHandles.append(video_handle)
                self.__oldReservedTrkLen[idx] = 0

                self.Matrices[idx] = []
                for local_cnt in range(args['num_of_projection']):
                    with open(args['projection_path'] + name + '-' + str(local_cnt + 1) + '.pickle', 'rb') as matrix:
                        self.Matrices[idx].append(pickle.load(matrix))

                if args['save']:
                    Runners.general_runner.make_save_folders(args=args, name=name)
                count += 1

        self.WholeImageSize = (self.WholeImageSize[0], self.WholeImageSize[1])

        ProjectionManager(video_list=args['video_list'], whole_image_size=self.WholeImageSize,
                          single_image_size=self.SingleImageSize, matrices=self.Matrices)

        self.__PlanHandle = PipeliningVideoManager()
        height, width, _ = plan_image.shape
        self.__PlanHandle.activate_video_object(args['output_base_path'] + args['run_name'] + 'plan.avi',
                                                v_info=(self.FrameRate, width, height))
        self.__PlanHandle.video_name = 'plan'

        primary_model_args = args[args['primary_model_name']]
        recovery_model_args = args[args['recovery_model_name']]
        tracker_model_args = args[args['tracker_model_name']]
        tracker_model_args['image_size'] = [self.WholeImageSize[0], self.WholeImageSize[1]]
        self._Trackers = []
        for idx, _ in enumerate(self.__VideoHandles):
            tracker_model_args['video_idx'] = idx
            tracker_model_args['video_len'] = len(self.__VideoHandles)
            tracker = trk_REGISTRY[tracker_model_args['model_name']](**tracker_model_args)
            self._Trackers.append(copy.deepcopy(tracker))
        # deleted id -> recovery_ -> <delete id> -> tracker[idx] % 3 != idx -> tracker[idx].forced delete
        self._PrimaryDetector = det_REGISTRY[primary_model_args['model_name']](**primary_model_args)
        self._RecoveryDetector = det_REGISTRY[recovery_model_args['model_name']](**recovery_model_args)
        self.__interactor = StateDecisionMaker(args['output_base_path'] + args['run_name'], self.DockInRegion, thr=0.4)

    def clean_trackers(self, deleted_ids):
        for video_idx, single_deleted_list in enumerate(deleted_ids):
            for deleted_id in single_deleted_list:
                target = deleted_id % 3
                if video_idx is not target:
                    self._Trackers[target].delete_tracker_forced(deleted_id)

    def pop_images(self, idx: int):
        handle = self.__VideoHandles[idx]
        rtn_value = (None, None, idx)
        _, np_bgr_image = handle.pop()
        if np_bgr_image is None:
            handle.release_video_object()
            return rtn_value
        np_rgb_image = np_bgr_image[..., ::-1].copy()
        tensor_image = ImageManager.convert_tensor(np_bgr_image)
        rtn_value = (np_rgb_image, tensor_image, idx)
        return rtn_value

    def get_image(self):
        rtn_images = []
        for handle in self.__VideoHandles:
            _, np_bgr_image = handle.pop()
            if np_bgr_image is None:
                self.__PlanHandle.release_video_object()
                return rtn_images
            tensor_image = ImageManager.convert_tensor(np_bgr_image)
            rtn_images.append(tensor_image)
            self.OutputImages['raw_image'].append(copy.deepcopy(tensor_image))
        return rtn_images

    def detect(self, tensor_image):
        result_list = []
        box_anchors = []
        for image in tensor_image:
            begin = time.time()
            raw_image, veh_info, box_info = self._PrimaryDetector.detection(image)
            print("Inference time: ", time.time() - begin)
            detected_image = self.__ImageHandle.draw_boxes_info(image, (veh_info, box_info))
            (box_boxes, _, _) = box_info
            (veh_boxes, veh_classes, veh_scores) = veh_info
            results = {'raw_image': raw_image, 'boxes': veh_boxes, 'classes': veh_classes, 'scores': veh_scores}
            results = DictToStruct(**results)
            self.OutputImages['detected_image'].append(detected_image)
            box_anchors.append(box_boxes)
            result_list.append(results)

        return result_list, box_anchors

    def tracking(self, results):
        del_list = []
        newReservedTrkLen = dict()
        for idx in range(len(self.__VideoHandles)):
            result = results[idx]
            self._Trackers[idx].assign_detections_to_trackers(detections=result.boxes)
            deleted_tracks = self._Trackers[idx].update_trackers()
            del_list.append(deleted_tracks)
            newReservedTrkLen[idx] = len(self._Trackers[idx].reserved_tracker_list)
        for idx in range(len(self.__VideoHandles)):
            if self.__oldReservedTrkLen[idx] != newReservedTrkLen[idx]:
                add_count = newReservedTrkLen[idx] - self.__oldReservedTrkLen[idx]
                tmp_list = copy.deepcopy(self._Trackers[idx].reserved_tracker_list)
                for new_idx in range(add_count):
                    self.delete_overlap(tmp_list.pop())
                self.__oldReservedTrkLen[idx] = newReservedTrkLen[idx]
        return del_list

    # tracking 이후에 새로 생선된 애가 하나가 있음
    # 근데 걔가 오버랩 대상자임
    # 그래서 오버랩되는지 분석해봄
    # 오버랩됨
    #
    # overlap check -> True
    # 둘 중에 최근에 추가된 놈의 tracker_list를 가져옴
    # tracker_list.pop()
    # id 반환
    # delete_tracker(trk.id)
    # [1, 2, 3, 4, 5]

    def post_tracking(self, deleted_trackers, whole_image):
        deleted_ids = []
        plan_image = self.OutputImages['plan_image']
        for idx, del_tracker in enumerate(deleted_trackers):
            temp_del = []
            for trk in del_tracker:
                # SSD Network 에도 잡히지 않는지 확인
                recovery_image, boxes, classes, scores = self._RecoveryDetector.detection(whole_image[idx])
                post_box = self._RecoveryDetector.get_zboxes(boxes=boxes,
                                                             im_width=self.WholeImageSize[0],
                                                             im_height=self.WholeImageSize[1])

                post_pass, box = post_iou_checker(trk.box, post_box, thr=0.2, offset=0.3)
                if post_pass:
                    self._Trackers[idx].revive_tracker(revive_trk=trk, new_box=box)
                else:
                    self._Trackers[idx].delete_tracker(delete_id=trk.id)
                    temp_del.append(trk.id)
            deleted_ids.append(temp_del)
            np_image = whole_image[idx].numpy()
            for trk in self._Trackers[idx].get_trackers():
                color = self.__ImageHandle.Colors[trk.id % len(self.__ImageHandle.Colors)]
                np_image = draw_box_label(np_image, trk.box, trk_id=trk.id, box_color=color)
                x, y = ProjectionManager.transform(trk.box, idx)
                plan_image = ProjectionManager.draw_plan_image(x, y, plan_image, color)

            self.OutputImages['tracking_image'].append(np_image)
        self.OutputImages['plan_image'] = plan_image
        return deleted_ids

    def delete_overlap(self, tracker):
        video_idx_dict = dict()
        tracker_idx_dict = dict()
        tmp_list = []  # 3개 Tracker 전체의 Reserved Trackers
        if tracker.id == 0:
            test = True
        for video_idx, trk in enumerate(self._Trackers):
            if video_idx == 1:
                test111 = True
            tracker_idx = 0
            for tmp_reserve_trk in trk.reserved_tracker_list:
                video_idx_dict[tmp_reserve_trk.id] = video_idx
                tracker_idx_dict[tmp_reserve_trk.id] = tracker_idx
                tmp_list.append(tmp_reserve_trk)
                tracker_idx += 1

        xPt, yPt = ProjectionManager.transform(tracker.box, video_idx_dict[tracker.id])

        for target_tracker in tmp_list:
            if tracker.id == target_tracker.id:
                continue
            target_xPt, target_yPt = ProjectionManager.transform(target_tracker.box, video_idx_dict[target_tracker.id])
            distance = get_distance((xPt, yPt), (target_xPt, target_yPt))
            if distance < 20:
                if video_idx_dict[tracker.id] is video_idx_dict[target_tracker.id]:
                    for idx in range(len(self._Trackers)):
                        self._Trackers[idx].adjust_division(1)
                    self._Trackers[video_idx_dict[target_tracker.id]].delete_tracker_forced(target_tracker.id)
                    return
                trackers = self._Trackers[video_idx_dict[tracker.id]].get_trackers()
                target_trackers = self._Trackers[video_idx_dict[target_tracker.id]].get_trackers()
                if tracker_idx_dict[tracker.id] >= len(trackers):
                    test = True
                if tracker.origin:
                    target_tracker.id = tracker.id
                    trackers.pop(tracker_idx_dict[tracker.id])
                    return
                else:
                    trackers[tracker_idx_dict[tracker.id]].id = target_tracker.id
                    target_trackers.pop(tracker_idx_dict[target_tracker.id])
                    return


        # for target_idx in range(len(tmp_list)):
        #     if tracker.id == tmp_list[target_idx].id: # 본인 등판
        #         continue
        #     target_xPt, target_yPt = ProjectionManager.transform(tmp_list[target_idx].box,
        #                                                          video_idx_dict[tmp_list[target_idx].id])
        #     distance = math.sqrt((xPt - target_xPt) ** 2 + (yPt - target_yPt) ** 2)
        #     if distance < 100:
        #         trackers = self._Trackers[video_idx_dict[tmp_list[target_idx].id]].get_trackers
        #         if tracker.origin:
        #             trackers[tracker_idx_dict[tmp_list[target_idx].id]].id = tracker.id
        #             break
        #         elif trackers[tracker_idx_dict[tmp_list[target_idx].id]].origin:
        #             tracker.id = trackers[tracker_idx_dict[tmp_list[target_idx].id]].id
        #             break
        #         else:
        #             Exception("Fucking Y?")

        # for idx, reserved_trk in enumerate(tmp_list):
        #     xPt, yPt = ProjectionManager.transform(reserved_trk.box, video_idx_dict[reserved_trk])
        #     for target_idx in range(idx + 1, len(tmp_list)):
        #         if target_idx == len(tmp_list):
        #             break
        #         target_xPt, target_yPt = ProjectionManager.transform(tmp_list[target_idx].box,
        #                                                              video_idx_dict[tmp_list[target_idx]])
        #         distance = math.sqrt((xPt - target_xPt)**2 + (yPt - target_yPt)**2)
        #         if distance < 100:
        #
        #             continue

    def post_processing(self, path):
        if self.__save:
            for idx, handle in enumerate(self.__VideoHandles):
                file_name = handle.video_name + '/' + handle.make_image_name()
                # Test
                ImageManager.save_tensor(self.OutputImages['raw_image'][idx],
                                         path['test_path'] + file_name)
                # Detection
                ImageManager.save_image(self.OutputImages['detected_image'][idx],
                                        path['detected_path'] + file_name)
                # Tracking
                ImageManager.save_tensor(self.OutputImages['tracking_image'][idx],
                                         path['tracking_path'] + file_name)
            # Plan
            ImageManager.save_image(self.OutputImages['plan_image'],
                                    path['plan_path'] + self.__VideoHandles[0].make_image_name())

        for idx, handle in enumerate(self.__VideoHandles):
            handle.append(self.OutputImages['tracking_image'][idx])
        self.__PlanHandle.append(self.OutputImages['plan_image'])

        self.OutputImages = {'raw_image': [], 'detected_image': [],
                             'tracking_image': [], 'plan_image': self.OutputImages['plan_image']}

    def interaction_processing(self, box_anchors, deleted_trackers):
        results = self.__interactor.get_decision(trackers_list=self._Trackers, boxes_list=box_anchors)
        self.__interactor.update_decision(image_name=self.__VideoHandles[0].make_image_name(), results=results)
        self.__interactor.loss_tracker(deleted_trackers)
