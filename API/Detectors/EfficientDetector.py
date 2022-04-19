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
        boxes, scores, classes, num_detections = self.Detector(converted_img)
        boxes = boxes[0].numpy()
        classes = classes[0].numpy()
        scores = scores[0].numpy()

        veh_info = self.__post_process(boxes, classes, scores)
        box_info = (np.array([]), np.array([]), np.array([]))
        return converted_img, veh_info, box_info

    def __post_process(self, boxes, classes, scores):
        score_idx = scores > self.min_score
        class_idx = (10 > classes) & (classes > 1)
        total_idx = score_idx & class_idx

        veh_boxes = boxes[total_idx]
        veh_classes = classes[total_idx]
        veh_classes = veh_classes.astype(np.str)
        veh_classes[:] = "ForkLift"
        veh_scores = scores[total_idx]
        veh_info = (veh_boxes, veh_classes, veh_scores)

        return veh_info

    def get_zboxes(self, boxes, im_width, im_height):
        return boxes
