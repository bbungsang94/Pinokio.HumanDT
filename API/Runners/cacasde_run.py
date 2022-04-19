import pickle
import copy
import time
import cv2

import Runners.general_runner
from Runners.general_runner import AbstractRunner
from Trackers.TrackerManager import TrackerManager, ColorWrapper
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
        tracker_model_args = args[args['tracker_model_name']]
        tracker_model_args['image_size'] = [self.WholeImageSize[0], self.WholeImageSize[1]]

        if args['tracker_model_name'] == 'sort_color':
            self.TrackerManager = ColorWrapper()
            max_trackers = None
        else:
            self.TrackerManager = TrackerManager(len(self.__VideoHandles))
            tracker_model_args['video_len'] = len(self.__VideoHandles)
            max_trackers = tracker_model_args['max_trackers']

        for idx, _ in enumerate(self.__VideoHandles):
            if args['tracker_model_name'] == 'sort_basic':
                tracker_model_args['video_idx'] = idx

            tracker = trk_REGISTRY[tracker_model_args['model_name']](**tracker_model_args)
            self.TrackerManager.add_tracker(tracker_idx=idx,
                                            tracker=copy.deepcopy(tracker),
                                            max_trackers=max_trackers)

        if args['tracker_model_name'] == 'sort_color':
            self.TrackerManager.sync_id()

        self._PrimaryDetector = det_REGISTRY[primary_model_args['model_name']](**primary_model_args)
        self.__interactor = StateDecisionMaker(args['output_base_path'] + args['run_name'], self.DockInRegion, thr=0.4)

    def clean_trackers(self, deleted_ids):
        for video_idx, single_deleted_list in enumerate(deleted_ids):
            for deleted_id in single_deleted_list:
                # self._Trackers[video_idx].clean_reserved(deleted_id)
                self._Trackers[video_idx].delete_tracker_forced(deleted_id)
                target = deleted_id % 3
                if video_idx is not target:
                    self._Trackers[target].delete_tracker_forced(deleted_id)
                    # 페어된 다른 트래커도 제거해줘야함

    def check_overlap(self):
        newReservedTrkLen = dict()
        for idx in range(len(self.__VideoHandles)):
            newReservedTrkLen[idx] = len(self._Trackers[idx].reserved_tracker_list)
            if self.__oldReservedTrkLen[idx] < newReservedTrkLen[idx]:
                add_count = newReservedTrkLen[idx] - self.__oldReservedTrkLen[idx]
                tmp_list = copy.deepcopy(self._Trackers[idx].reserved_tracker_list)
                for new_idx in range(add_count):
                    self.delete_overlap(tmp_list.pop())
            self.__oldReservedTrkLen[idx] = newReservedTrkLen[idx]

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
        self.OutputImages['raw_image'] = []
        release_flag = False
        for handle in self.__VideoHandles:
            _, np_bgr_image = handle.pop()
            if np_bgr_image is None:
                self.__PlanHandle.release_video_object()
                release_flag = True
                break
            tensor_image = ImageManager.convert_tensor(np_bgr_image)
            rtn_images.append(tensor_image)
            self.OutputImages['raw_image'].append(copy.deepcopy(tensor_image))

        if release_flag:
            for handle in self.__VideoHandles:
                handle.release_video_object()
            return None

        return rtn_images

    def detect(self, tensor_image):
        result_list = []
        box_anchors = []
        for image in tensor_image:
            begin = time.time()
            raw_image, veh_info, box_info, person_info = self._PrimaryDetector.detection(image)
            print("Inference time: ", (time.time() - begin) * 1000, "ms")
            detected_image = self.__ImageHandle.draw_boxes_info(image, (veh_info, box_info))
            (box_boxes, _, _) = box_info
            (veh_boxes, veh_classes, veh_scores) = veh_info
            results = {'raw_image': raw_image, 'boxes': veh_boxes, 'classes': veh_classes, 'scores': veh_scores}
            results = DictToStruct(**results)
            self.OutputImages['detected_image'].append(detected_image)
            box_anchors.append(box_boxes)
            result_list.append(results)

        return result_list, box_anchors

    def tracking(self, results, images):
        target_trackers = dict()
        if self.TrackerManager.model_name == 'ColorWrapper':
            for idx, result in enumerate(results):
                new_trackers = self.TrackerManager.tracking(boxes=result.boxes, img=images[idx].numpy(), idx=idx)
                target_trackers[idx] = new_trackers
            self.TrackerManager.sync_id()

        else:
            target_trackers = self.TrackerManager.tracking(boxes=results)

        self.TrackerManager.post_tracking(target_trackers)

    def sub_detection(self, deleted_trks, image):
        deleted_ids = dict()
        for idx, deleted_list in deleted_trks.items():
            temp_del = []
            for trk in deleted_list:
                # SSD Network 에도 잡히지 않는지 확인
                recovery_image, boxes, classes, scores = self._RecoveryDetector.detection(image[idx])
                post_box = self._RecoveryDetector.get_zboxes(boxes=boxes,
                                                             im_width=self.WholeImageSize[0],
                                                             im_height=self.WholeImageSize[1])

                post_pass, box = post_iou_checker(trk.box, post_box, thr=0.2, offset=0.3)
                if post_pass is False:
                    temp_del.append(trk.id)
            deleted_ids[idx] = temp_del

        return deleted_ids

    def post_tracking(self, deleted_trackers, whole_image):
        self.TrackerManager.post_tracking()

    def delete_overlap(self, tracker):
        video_idx_dict = dict()
        tracker_idx_dict = dict()
        tmp_list = []  # 3개 Tracker 전체의 Reserved Trackers

        for video_idx, trk in enumerate(self._Trackers):
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
                trackers = self._Trackers[video_idx_dict[tracker.id]].get_single_trackers()
                target_trackers = self._Trackers[video_idx_dict[target_tracker.id]].get_single_trackers()
                if tracker.origin:
                    target_tracker.id = tracker.id
                    trackers.pop(tracker_idx_dict[tracker.id])
                    return
                else:
                    trackers[tracker_idx_dict[tracker.id]].id = target_tracker.id
                    target_trackers.pop(tracker_idx_dict[target_tracker.id])
                    return

    def post_processing(self, path, whole_image):
        plan_image = self.OutputImages['plan_image']
        trackers = self.TrackerManager.get_single_trackers()
        for idx in range(len(self.OutputImages['raw_image'])):
            np_image = whole_image[idx].numpy()
            if idx in trackers:
                for tracker in trackers[idx]:
                    color = self.__ImageHandle.Colors[tracker.id % len(self.__ImageHandle.Colors)]
                    np_image = draw_box_label(np_image, tracker.box, trk_id=tracker.id, box_color=color)
                    x, y = ProjectionManager.transform(tracker.box, idx)
                    plan_image = ProjectionManager.draw_plan_image(x, y, plan_image, color)
            self.OutputImages['tracking_image'].append(np_image)
        self.OutputImages['plan_image'] = plan_image

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
                temp_img = self.OutputImages['plan_image']
                converted = cv2.cvtColor(temp_img, cv2.COLOR_BGR2RGB)
                ImageManager.save_image(converted, path['plan_path'] + self.__VideoHandles[0].make_image_name())

        for idx, handle in enumerate(self.__VideoHandles):
            handle.append(self.OutputImages['tracking_image'][idx])
        self.__PlanHandle.append(self.OutputImages['plan_image'])

        self.OutputImages = {'raw_image': [], 'detected_image': [],
                             'tracking_image': [], 'plan_image': self.OutputImages['plan_image']}

    def interaction_processing(self, box_anchors, deleted_trackers):
        results = self.__interactor.get_decision(trackers_list=self.TrackerManager.get_trackers(),
                                                 boxes_list=box_anchors)
        self.__interactor.update_decision(image_name=self.__VideoHandles[0].make_image_name(), results=results)
        self.__interactor.loss_tracker(deleted_trackers)
