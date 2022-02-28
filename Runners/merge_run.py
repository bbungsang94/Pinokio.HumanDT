import os
import pickle
import cv2
import tensorflow as tf
from multiprocessing import Pool

import torch
from Detectors import REGISTRY as det_REGISTRY
from Trackers import REGISTRY as trk_REGISTRY
from utilities.media_handler import PipeliningVideoManager, ImageManager
from utilities.helpers import DictToStruct, post_iou_checker, draw_box_label
from utilities.projection_helper import ProjectionManager


class MergeRunner:

    def __init__(self, args, logger=None):
        self.__VideoMap = args['video_list']
        self.__VideoHandles = []
        self.__ImageHandle = ImageManager()
        self.__save = args['save']
        self.__OutputHandle = dict()
        plan_image = ImageManager.load_cv(args['plan_path'])
        self.FrameRate = 60
        self.SingleImageSize = None
        self.WholeImageSize = None
        self.MaxWidthIdx = 0

        self.OutputImages = {'raw_image': None, 'detected_image': None,
                             'tracking_image': None, 'plan_image': plan_image}

        self.Matrices = dict()
        count = 0
        for row, videos in self.__VideoMap.items():
            for idx, video_name in enumerate(videos):
                (name, extension) = video_name.split('.')
                video_handle = PipeliningVideoManager()
                frame_rate, image_size = video_handle.load_video(args['video_path'] + video_name)
                video_handle.video_name = name
                if frame_rate < self.FrameRate:
                    self.FrameRate = frame_rate
                if self.WholeImageSize is None:
                    self.WholeImageSize = image_size
                    self.SingleImageSize = image_size
                if idx > self.MaxWidthIdx:
                    self.MaxWidthIdx = idx

                self.__VideoHandles.append(video_handle)
                self.Matrices[name] = []
                for local_cnt in range(args['num_of_projection']):
                    with open(args['projection_path'] + name + '-' + str(local_cnt + 1) + '.pickle', 'rb') as matrix:
                        self.Matrices[name].append(pickle.load(matrix))

                # if args['save']:
                #     make_save_folders(args, name)
                count += 1

        self.WholeImageSize = (self.WholeImageSize[0] * (self.MaxWidthIdx + 1),
                               self.WholeImageSize[1] * len(self.__VideoMap))

        self.__VideoHandlePool = Pool(processes=len(self.__VideoHandles))
        ProjectionManager(video_list=args['video_list'], whole_image_size=self.WholeImageSize)

        video_handle = PipeliningVideoManager()
        height, width, _ = plan_image.shape
        video_handle.activate_video_object(args['output_base_path'] + args['run_name'] + 'plan.avi',
                                           v_info=(self.FrameRate, width, height))
        video_handle.video_name = 'plan'
        self.__OutputHandle[video_handle.video_name] = video_handle

        video_handle = PipeliningVideoManager()
        video_handle.activate_video_object(args['output_base_path'] + args['run_name'] + 'output.avi',
                                           v_info=(self.FrameRate, self.WholeImageSize[0], self.WholeImageSize[1]))
        video_handle.video_name = 'output'
        self.__OutputHandle[video_handle.video_name] = video_handle

        primary_model_args = args[args['primary_model_name']]
        recovery_model_args = args[args['recovery_model_name']]
        tracker_model_args = args[args['tracker_model_name']]
        tracker_model_args['image_size'] = [self.WholeImageSize[0], self.WholeImageSize[1]]
        self._Trackers = trk_REGISTRY[tracker_model_args['model_name']](**tracker_model_args)
        self._PrimaryDetector = det_REGISTRY[primary_model_args['model_name']](**primary_model_args)
        self._RecoveryDetector = det_REGISTRY[recovery_model_args['model_name']](**recovery_model_args)

    def pop_images(self, idx: int):
        handle = self.__VideoHandles[idx]
        rtn_value = (None, None, idx)
        _, np_bgr_image = handle.pop()
        if np_bgr_image is None:
            return rtn_value
        np_rgb_image = np_bgr_image[..., ::-1].copy()
        tensor_image = ImageManager.convert_tensor(np_bgr_image)
        rtn_value = (np_rgb_image, tensor_image, idx)
        return rtn_value

    def get_image(self):
        # np_tensor_images = self.__VideoHandlePool.map(func=self.pop_images, iterable=(range(len(self.__VideoHandles))))
        raw_images = dict()
        for idx, _ in enumerate(self.__VideoHandles):
            np_tensor_image = self.pop_images(idx)
            (np_image, tensor_image, idx) = np_tensor_image
            raw_images[idx] = (np_image, tensor_image)
            if np_image is None:
                for _, value in self.__OutputHandle.items():
                    value.release_video_object()
                return None

        width_merged = []
        for row, videos in self.__VideoMap.items():
            images = []
            count = 0
            for _ in videos:
                (np_image, tensor_image) = raw_images[count]
                images.append(tensor_image)
                count += 1
            if (self.MaxWidthIdx + 1) > len(videos):
                for add_idx in range((self.MaxWidthIdx + 1) - len(videos)):
                    empty_img = torch.empty(self.SingleImageSize[0], self.SingleImageSize[1], 3)
                    images.append(empty_img)
            width_image = tf.concat(images, axis=1)
            width_merged.append(width_image)
        whole_image = tf.concat(width_merged, axis=0)
        self.OutputImages['raw_image'] = whole_image
        return whole_image

    def detect(self, tensor_image):
        raw_image, veh_info, box_info = self._PrimaryDetector.detection(tensor_image)
        detected_image = self.__ImageHandle.draw_boxes_info(tensor_image, (veh_info, box_info))
        self.OutputImages['detected_image'] = detected_image
        (veh_boxes, veh_classes, veh_scores) = veh_info
        results = {'raw_image': raw_image, 'boxes': veh_boxes, 'classes': veh_classes, 'scores': veh_scores}
        return DictToStruct(**results)

    def tracking(self, results):
        self._Trackers.assign_detections_to_trackers(detections=results.boxes)
        deleted_tracks = self._Trackers.update_trackers()
        return deleted_tracks

    def post_tracking(self, deleted_trackers, whole_image):
        for trk in deleted_trackers:
            # SSD Network 에도 잡히지 않는지 확인
            recovery_image, boxes, classes, scores = self._RecoveryDetector.detection(whole_image)
            post_box = self._RecoveryDetector.get_zboxes(boxes=boxes,
                                                         im_width=self.WholeImageSize[0],
                                                         im_height=self.WholeImageSize[1])

            post_pass, box = post_iou_checker(trk.box, post_box, thr=0.2, offset=0.3)
            if post_pass:
                self._Trackers.revive_tracker(revive_trk=trk, new_box=box)
            else:
                self._Trackers.delete_tracker(delete_id=trk.id)

        np_image = whole_image.numpy()
        plan_image = self.OutputImages['plan_image']
        for trk in self._Trackers.get_trackers():
            np_image = draw_box_label(np_image, trk.box,
                                      self.__ImageHandle.Colors[trk.id % len(self.__ImageHandle.Colors)])
            plan_image = ProjectionManager.transform(trk.box, whole_image, plan_image,
                                                     self.Matrices,
                                                     self.__ImageHandle.Colors[trk.id % len(self.__ImageHandle.Colors)])
        self.OutputImages['tracking_image'] = np_image
        self.OutputImages['plan_image'] = plan_image

    def post_processing(self, path):
        if self.__save:
            file_name = self.__VideoHandles[0].make_image_name()
            # Test
            ImageManager.save_tensor(self.OutputImages['raw_image'],
                                     path['test_path'] + file_name)
            # Detection
            ImageManager.save_image(self.OutputImages['detected_image'],
                                    path['detected_path'] + file_name)
            # Tracking
            ImageManager.save_tensor(self.OutputImages['tracking_image'],
                                     path['tracking_path'] + file_name)
            # Plan
            ImageManager.save_image(self.OutputImages['plan_image'],
                                    path['plan_path'] + file_name)

        for key, value in self.__OutputHandle.items():
            if key == 'output':
                value.append(self.OutputImages['tracking_image'])
            else:
                value.append(self.OutputImages['plan_image'])
