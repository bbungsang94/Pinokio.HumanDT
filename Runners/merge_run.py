import tensorflow as tf
from multiprocessing import Pool

import torch

from Detectors import REGISTRY as det_REGISTRY
from Trackers import REGISTRY as trk_REGISTRY
from utilities.media_handler import PipeliningVideoManager, ImageManager

def pop_images(info: (PipeliningVideoManager, int)):
    handle = info[0]
    handle_idx = info[1]
    rtn_value = (None, None, handle_idx)
    _, np_bgr_image = handle.pop()
    if np_bgr_image is None:
        return rtn_value
    np_rgb_image = np_bgr_image[..., ::-1].copy()
    tensor_image = ImageManager.convert_tensor(np_bgr_image)
    rtn_value = (np_rgb_image, tensor_image, handle_idx)
    return rtn_value

class MergeRunner:

    def __init__(self, args, logger=None):
        tracker_model_args = args[args['tracker_model_name']]
        primary_model_args = args[args['primary_model_name']]
        recovery_model_args = args[args['recovery_model_name']]

        self._PrimaryDetector = det_REGISTRY[primary_model_args['model_name']](**primary_model_args)
        self._RecoveryDetector = det_REGISTRY[recovery_model_args['model_name']](**recovery_model_args)
        self._Trackers = trk_REGISTRY[tracker_model_args['model_name']](**tracker_model_args)
        self.__VideoMap = args['video_list']
        self.__VideoHandles = []
        self.FrameRate = 60
        self.SingleImageSize = None
        self.WholeImageSize = None

        self.MaxWidthIdx = 0
        count = 0
        for row, videos in self.__VideoMap.items():
            for idx, video_name in enumerate(videos):
                (name, extension) = video_name.split('.')
                video_handle = PipeliningVideoManager()
                frame_rate, image_size = video_handle.load_video(args['video_path'] + video_name)
                video_handle.activate_video_object(args['output_base_path'] + args['run_name'] + name + '/' +
                                                   args['tracking_path'] + video_name)

                if frame_rate < self.frame_rate:
                    self.frame_rate = frame_rate
                if self.WholeImageSize is None:
                    self.WholeImageSize = image_size
                    self.SingleImageSize = image_size
                if idx > self.MaxWidthIdx:
                    self.MaxWidthIdx = idx

                self.__VideoHandles.append((video_handle, count))
                count += 1
        self.WholeImageSize = (self.WholeImageSize[0] * (self.MaxWidthIdx + 1),
                               self.WholeImageSize[1] * len(self.__VideoMap))

        self.__VideoHandlePool = Pool(processes=len(self.__VideoHandles))

    def get_image(self):
        np_tensor_images = self.__VideoHandlePool.map(func=pop_images, iterable=self.__VideoHandles)

        raw_images = dict()
        for np_tensor_image in np_tensor_images:
            (np_image, tensor_image, idx) = np_tensor_image
            raw_images[idx] = (np_image, tensor_image)

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
        col_image = tf.concat(width_merged, axis=0)
        whole_image = tf.image.convert_image_dtype(col_image, tf.float32)[tf.newaxis, ...]
        return whole_image

    def detect(self):

    def tracking(self):

    def postprocessing(self):

