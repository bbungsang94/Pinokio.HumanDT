import pickle
import copy
import Runners.general_runner
from Runners.general_runner import AbstractRunner
from utilities.helpers import DictToStruct, post_iou_checker, draw_box_label
from utilities.media_handler import ImageManager, PipeliningVideoManager
from utilities.projection_helper import ProjectionManager
from Detectors import REGISTRY as det_REGISTRY
from Trackers import REGISTRY as trk_REGISTRY


class CascadeRunner(AbstractRunner):
    def __init__(self, args, logger=None):
        self.__VideoMap = args['video_list']
        self.__VideoHandles = []
        self.__ImageHandle = ImageManager()
        self.__save = args['save']
        plan_image = ImageManager.load_cv(args['plan_path'])
        self.FrameRate = 60
        self.SingleImageSize = None
        self.WholeImageSize = None
        self.MaxWidthIdx = 0

        self.OutputImages = {'raw_image': [], 'detected_image': [],
                             'tracking_image': [], 'plan_image': plan_image}

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
                self.Matrices[name] = []
                for local_cnt in range(args['num_of_projection']):
                    with open(args['projection_path'] + name + '-' + str(local_cnt + 1) + '.pickle', 'rb') as matrix:
                        self.Matrices[name].append(pickle.load(matrix))

                if args['save']:
                    Runners.general_runner.make_save_folders(args=args, name=name)
                count += 1

        self.WholeImageSize = (self.WholeImageSize[0], self.WholeImageSize[1])

        ProjectionManager(video_list=args['video_list'], whole_image_size=self.WholeImageSize, single_image_size=self.SingleImageSize)

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
            tracker = trk_REGISTRY[tracker_model_args['model_name']](**tracker_model_args)
            self._Trackers.append(copy.deepcopy(tracker))
        self._PrimaryDetector = det_REGISTRY[primary_model_args['model_name']](**primary_model_args)
        self._RecoveryDetector = det_REGISTRY[recovery_model_args['model_name']](**recovery_model_args)

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
        for image in tensor_image:
            raw_image, veh_info, box_info = self._PrimaryDetector.detection(image)
            detected_image = self.__ImageHandle.draw_boxes_info(image, (veh_info, box_info))
            (veh_boxes, veh_classes, veh_scores) = veh_info
            results = {'raw_image': raw_image, 'boxes': veh_boxes, 'classes': veh_classes, 'scores': veh_scores}
            results = DictToStruct(**results)
            self.OutputImages['detected_image'].append(detected_image)
            result_list.append(results)

        return result_list

    def tracking(self, results):
        del_list = []
        for idx in range(len(self.__VideoHandles)):
            result = results[idx]
            self._Trackers[idx].assign_detections_to_trackers(detections=result.boxes)
            deleted_tracks = self._Trackers[idx].update_trackers()
            del_list.append(deleted_tracks)
        return del_list

    def post_tracking(self, deleted_trackers, whole_image):
        plan_image = self.OutputImages['plan_image']
        for idx, del_tracker in enumerate(deleted_trackers):
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

            np_image = whole_image[idx].numpy()
            for trk in self._Trackers[idx].get_trackers():

                np_image = draw_box_label(np_image, trk.box,
                                          self.__ImageHandle.Colors[trk.id % len(self.__ImageHandle.Colors)])
                plan_image = ProjectionManager.transform(trk.box, whole_image[idx], plan_image,
                                                         self.Matrices,
                                                         self.__ImageHandle.Colors[
                                                             trk.id % len(self.__ImageHandle.Colors)])
            self.OutputImages['tracking_image'].append(np_image)
        self.OutputImages['plan_image'] = plan_image

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
