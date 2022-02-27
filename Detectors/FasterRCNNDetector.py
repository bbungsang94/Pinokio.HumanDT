from Detectors.Abstract.AbstractDetector import AbstractDetector
from utilities.media_handler import *
import tensorflow_hub as hub


class OpenImageDetector(AbstractDetector):
    def __init__(self,
                 model_name: "",
                 hub_mode: True,
                 model_handle: "",
                 label_path: "",
                 box_min_score: 0.2,
                 vehicle_min_score: 0.4,
                 iou_score: 0,
                 offset_score: 0,
                 max_boxes: 0
                 ):
        self.model_name = model_name
        self.hub_mode = hub_mode
        self.model_handle = model_handle
        self.box_min_score = box_min_score
        self.vehicle_min_score = vehicle_min_score
        self.iou_score = iou_score
        self.offset_score = offset_score
        self.max_boxes = max_boxes

        if self.hub_mode is True:
            self.Detector = hub.load(self.model_handle).signatures['default']
        else:  # 로컬 모델
            raise NotImplementedError

    def detection(self, image):
        """Determines the locations of the vehicle in the image

                Args:
                    image: image(tensor)
                Returns:
                    list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

                """
        converted_img = tf.image.convert_image_dtype(image, tf.float32)[tf.newaxis, ...]
        result = self.Detector(converted_img)
        result = {key: value.numpy() for key, value in result.items()}
        info = tf.shape(converted_img)
        veh_info, box_info = self.__post_process(result, info)

        return converted_img, veh_info, box_info

    def __post_process(self, result, info):
        boxes = result["detection_boxes"]
        classes_idx = result["detection_class_labels"]
        classes = result["detection_class_entities"]
        scores = result["detection_scores"]

        veh_score_idx = scores > self.vehicle_min_score
        veh_class_idx = (classes_idx == 103) | (classes_idx == 404) | (classes_idx == 400)
        veh_idx = veh_score_idx & veh_class_idx
        classes[veh_idx] = "ForkLift"

        box_score_idx = scores > self.box_min_score
        # box_class_idx = classes_idx == 136
        box_idx = box_score_idx
        # classes[box_idx] = "Box"

        img_shape = np.array(info)
        veh_boxes = boxes[veh_idx]
        veh_boxes = self.get_zboxes(veh_boxes, im_width=img_shape[2], im_height=img_shape[1])
        veh_classes = classes[veh_idx]
        veh_scores = scores[veh_idx]
        veh_info = (veh_boxes, veh_classes, veh_scores)

        box_boxes = boxes[box_idx]
        box_boxes = self.get_zboxes(box_boxes, im_width=img_shape[2], im_height=img_shape[1])
        box_classes = classes[box_idx]
        box_scores = scores[box_idx]
        box_info = (box_boxes, box_classes, box_scores)
        return veh_info, box_info

    def get_zboxes(self, boxes, im_width, im_height):
        z_boxes = []
        for i in range(min(boxes.shape[0], self.max_boxes)):
            ymin, xmin, ymax, xmax = tuple(boxes[i])
            (left, right, top, bottom) = (xmin * im_width, xmax * im_width,
                                          ymin * im_height, ymax * im_height)
            z_boxes.append([top, left, bottom, right])
        return np.array(z_boxes)
