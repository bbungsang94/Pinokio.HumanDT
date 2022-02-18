import yaml
from PIL import ImageColor

from Detectors.Abstract.AbstractDetector import AbstractDetector
from utilities.media_handler import *
import tensorflow_hub as hub
import time


class EfficientDetector(AbstractDetector):
    def __init__(self,
                 model_name: "",
                 hub_mode: True,
                 model_handle: "",
                 label_path: "",
                 min_score: 0,
                 iou_score: 0,
                 offset_score: 0,
                 max_boxes: 0
                 ):
        self.model_name = model_name
        self.hub_mode = hub_mode
        self.model_handle = model_handle
        self.label_path = label_path
        self.min_score = min_score
        self.iou_score = iou_score
        self.offset_score = offset_score
        self.max_boxes = max_boxes

        if self.hub_mode is True:
            self.Detector = hub.load(self.model_handle)
        else:  # 로컬 모델
            raise NotImplementedError

        with open(self.label_path) as f:
            self.LabelList = yaml.load(f, Loader=yaml.FullLoader)

    def detection(self, image):
        """Determines the locations of the vehicle in the image

                Args:
                    image: image(tensor)
                Returns:
                    list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

                """
        converted_img = tf.image.convert_image_dtype(image, tf.uint8)[tf.newaxis, ...]
        try:
            if self.Detector is not None:
                start_time = time.time()
                boxes, scores, classes, num_detections = self.Detector(converted_img)
                end_time = time.time()
                print("Found %d objects." % num_detections)
                boxes = boxes[0].numpy()
                classes = classes[0].numpy()
                scores = scores[0].numpy()
            else:
                return
        except AttributeError:
            raise "Wrong Model Name"
        print("Inference time: ", end_time - start_time)

        del_idx = self.__post_process(classes, scores, self.min_score)
        boxes = boxes[del_idx]
        classes = classes[del_idx]
        classes = classes.astype(np.str)
        classes[:] = self.LabelList[3]
        scores = scores[del_idx]

        return converted_img, boxes, classes, scores

    def __post_process(self, classes, scores, min_score=None):
        if min_score is None:
            min_score = self.min_score
        score_idx = scores > min_score

        class_idx = (10 > classes) & (classes > 1)
        total_idx = score_idx & class_idx
        return total_idx

    def get_zboxes(self, boxes, im_width, im_height):
        return boxes
