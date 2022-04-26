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
from utilities.config_mapper import get_yaml


class CascadeRunner(AbstractRunner):
    def __init__(self, args, logger=None):
        # Private members
        self.__Provide = args['provide']
        self.__VideoMap = args[self.__Provide]['list']
        self.__ImageHandle = ImageManager()
        self.__Save = args['save']
        self.__OldReservedTrkLen = dict()
        self.__VideoHandles = []

        # Public members (to use as an output)
        plan_image = ImageManager.load_cv(args['plan_path'])
        self.FrameRate = 60
        self.SingleImageSize = None
        self.WholeImageSize = None
        self.MaxWidthIdx = 0
        self.DockInRegion = get_yaml(args['projection_path'] + "DockEntrance.yaml")['DockRegion']
        self.MappingInfo = get_yaml(args['projection_path'] + "MappingMatrix.yaml")

        with open(args['projection_path'] + "DockEntrance.pickle", 'rb') as f:
            test = pickle.load(f)
        self.Matrices = dict()
        self.OutputImages = {'raw_image': [], 'detected_image': [],
                             'tracking_image': [], 'plan_image': plan_image}

        # Initialize about Video
        count = 0
        for row, videos in self.__VideoMap.items():
            for idx, video_name in enumerate(videos):
                (name, _) = video_name.split('.')
                video_handle = PipeliningVideoManager()
                frame_count = -1
                if self.__Provide == "Image":
                    config = get_yaml(args[self.__Provide]['path'] + name + ".yaml")
                    frame_rate = config['FrameRate']
                    image_size = tuple(config['VideoSize'])
                    frame_count = config['StartCount']
                    width, height = image_size
                    v_info = (frame_rate, width, height)
                    video_handle.input_path = args[self.__Provide]['path'] + name + "/"
                else:
                    frame_rate, image_size = video_handle.load_video(args[self.__Provide]['path'] + video_name)
                    v_info = None

                video_handle.activate_video_object(args['output_base_path'] + args['run_name'] + video_name,
                                                   v_info=v_info)
                video_handle.video_name = name
                if frame_rate < self.FrameRate:
                    self.FrameRate = frame_rate
                if self.WholeImageSize is None:
                    self.WholeImageSize = image_size
                    self.SingleImageSize = image_size
                self.__VideoHandles.append((frame_count, video_handle))
                self.__OldReservedTrkLen[idx] = 0

                self.Matrices[idx] = []
                for local_cnt in range(args['num_of_projection']):
                    with open(args['projection_path'] + name + '-' + str(local_cnt + 1) + '.pickle', 'rb') as matrix:
                        self.Matrices[idx].append(pickle.load(matrix))

                if args['save']:
                    Runners.general_runner.make_save_folders(args=args, name=name)
                count += 1

        self.WholeImageSize = (self.WholeImageSize[0], self.WholeImageSize[1])
        ProjectionManager(video_list=args[self.__Provide]['list'], whole_image_size=self.WholeImageSize,
                          single_image_size=self.SingleImageSize, mapping_info=self.MappingInfo)
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

    def get_image(self):
        rtn_images = []
        self.OutputImages['raw_image'] = []
        release_flag = False
        for iteration in range(0, len(self.__VideoHandles)):
            frame_count, handle = self.__VideoHandles[iteration]
            if frame_count is -1:
                _, np_bgr_image = handle.pop()
            else:
                image_path = handle.make_image_name(frame_count)
                np_bgr_image = ImageManager.load_cv(handle.input_path + image_path)
                frame_count += 1
                self.__VideoHandles[iteration] = (frame_count, handle)

            if np_bgr_image is None:
                self.__PlanHandle.release_video_object()
                release_flag = True
                break
            tensor_image = ImageManager.convert_tensor(np_bgr_image)
            rtn_images.append(tensor_image)
            self.OutputImages['raw_image'].append(copy.deepcopy(tensor_image))

        if release_flag:
            for (_, handle) in self.__VideoHandles:
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

        if self.__Save:
            for iteration in range(0, len(self.__VideoHandles)):
                frame_count, handle = self.__VideoHandles[iteration]
                file_name = handle.video_name + '/' + handle.make_image_name(frame_count)
                # Test
                ImageManager.save_tensor(self.OutputImages['raw_image'][iteration],
                                         path['test_path'] + file_name)
                # Detection
                ImageManager.save_image(self.OutputImages['detected_image'][iteration],
                                        path['detected_path'] + file_name)
                # Tracking
                ImageManager.save_tensor(self.OutputImages['tracking_image'][iteration],
                                         path['tracking_path'] + file_name)

            frame_count, handle = self.__VideoHandles[0]
            # Plan
            temp_img = self.OutputImages['plan_image']
            converted = cv2.cvtColor(temp_img, cv2.COLOR_BGR2RGB)
            ImageManager.save_image(converted, path['plan_path'] + handle.make_image_name(frame_count))

        for idx, (_, handle) in enumerate(self.__VideoHandles):
            handle.append(self.OutputImages['tracking_image'][idx])
        self.__PlanHandle.append(self.OutputImages['plan_image'])

        self.OutputImages = {'raw_image': [], 'detected_image': [],
                             'tracking_image': [], 'plan_image': self.OutputImages['plan_image']}

    def interaction_processing(self, box_anchors, deleted_trackers):
        results = self.__interactor.get_decision(trackers_list=self.TrackerManager.get_trackers(),
                                                 boxes_list=box_anchors)
        frame_count, handle = self.__VideoHandles[0]
        self.__interactor.update_decision(image_name=handle.make_image_name(frame_count), results=results)
        self.__interactor.loss_tracker(deleted_trackers)
