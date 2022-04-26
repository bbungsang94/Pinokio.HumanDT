import torchvision

from utils.general import check_img_size, check_requirements, non_max_suppression, scale_coords, xyxy2xywh
from Detectors.Abstract.AbstractDetector import AbstractDetector
from utilities.media_handler import *
import torch
import torch.nn.functional as nnf
import tensorflow_hub as hub
import numpy as np
import time
import cv2

from utils.general import xywh2xyxy


class Yolov5Detector(AbstractDetector):
    def __init__(self,
                 model_name: "",
                 hub_mode: False,
                 model_handle: "",
                 label_path: "",
                 box_min_score: 0.2,
                 vehicle_min_score: 0.4,
                 person_min_score: 0.4,
                 iou_score: 0,
                 offset_score: 0,
                 max_boxes: 0
                 ):
        self.model_name = model_name
        self.hub_mode = hub_mode
        self.model_handle = model_handle
        self.label_path = label_path
        self.box_min_score = box_min_score
        self.vehicle_min_score = vehicle_min_score
        self.person_min_score = person_min_score
        self.iou_score = iou_score
        self.offset_score = offset_score
        self.max_boxes = max_boxes

        if self.hub_mode is True:
            self.Detector = hub.load(self.model_handle).signatures['default']
        else:  # 로컬 모델
            from models.experimental import attempt_load
            self.Detector = attempt_load(self.model_handle, map_location=torch.device('cuda:0'))
            # self.Detector.eval()

    def detection(self, input_image):
        """Determines the locations of the vehicle in the image

                Args:
                    input_image: image(tensor)
                Returns:
                    list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

                """
        image = input_image.permute(2, 0, 1)
        # converted_img = tf.image.convert_image_dtype(image, tf.float32)
        device = torch.device('cuda:0')
        image = image.float().to(device)
        image /= 255
        if len(image.shape) == 3:
            converted_img = image[None]  # expand for batch dim
        else:
            converted_img = image

        out = nnf.interpolate(converted_img, size=(480, 640), mode='bicubic', align_corners=False)
        pred = self.Detector(out, augment=False, visualize=False)
        pred = non_max_suppression(pred[0], self.box_min_score, self.iou_score)
        det = pred[0]
        gn = torch.tensor([640, 480, 640, 480])
        result = dict()
        result["detection_boxes"] = np.empty([0, 0])
        result["detection_class_labels"] = np.empty([0, 0])
        result["detection_scores"] = np.empty([0, 0])
        result["detection_class"] = np.empty([0, 0], dtype=np.str)

        detection_boxes = []
        detection_class_labels = []
        detection_scores = []
        detection_class = []
        if len(det):
            # Rescale boxes from img_size to img0 size
            det[:, :4] = scale_coords(converted_img.shape[2:], det[:, :4], input_image.shape).round()

            # Print results
            # for c in det[:, -1].unique():
            #     n = (det[:, -1] == c).sum()  # detections per class
            #
            #     s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

            # Write results
            for *xyxy, conf, cls in reversed(det):
                xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()
                detection_boxes.append(xywh)
                detection_class_labels.append(int(cls))
                detection_scores.append(float(conf))
                detection_class.append(None)
            result["detection_boxes"] = np.array(detection_boxes)
            result["detection_class_labels"] = np.array(detection_class_labels)
            result["detection_scores"] = np.array(detection_scores)
            result["detection_class"] = np.array(detection_class)

            # print(f'Inferencing and Processing Done. ({time.time() - t0:.3f}s)')
            # result = {key: value.numpy() for key, value in result.items()}
        info = tf.shape(input_image)
        veh_info, box_info, person_info = self.__post_process(result, info)
        return converted_img, veh_info, box_info, person_info

    def __post_process(self, result, info):
        boxes = result["detection_boxes"]
        classes_idx = result["detection_class_labels"]
        classes = result["detection_class"]
        scores = result["detection_scores"]

        veh_score_idx = scores > self.vehicle_min_score
        veh_class_idx = classes_idx == 0

        veh_idx = veh_score_idx & veh_class_idx
        classes[veh_idx] = "ForkLift"

        box_score_idx = scores > self.box_min_score
        box_class_idx = classes_idx == 1
        box_idx = box_score_idx & box_class_idx
        classes[box_idx] = "Box"

        person_score_idx = scores > self.person_min_score
        person_class_idx = classes_idx == 2
        person_idx = person_score_idx & person_class_idx
        classes[person_idx] = "Person"

        img_shape = np.array(info)
        veh_boxes = boxes[veh_idx]
        veh_boxes = self.get_zboxes(veh_boxes, im_width=img_shape[1], im_height=img_shape[0])
        veh_classes = classes[veh_idx]
        veh_scores = scores[veh_idx]
        veh_info = (veh_boxes, veh_classes, veh_scores)

        box_boxes = boxes[box_idx]
        box_boxes = self.get_zboxes(box_boxes, im_width=img_shape[1], im_height=img_shape[0])
        box_classes = classes[box_idx]
        box_scores = scores[box_idx]
        box_info = (box_boxes, box_classes, box_scores)

        person_boxes = boxes[person_idx]
        person_boxes = self.get_zboxes(person_boxes, im_width=img_shape[1], im_height=img_shape[0])
        person_classes = classes[person_idx]
        person_scores = scores[box_idx]
        person_info = (person_boxes, person_classes, person_scores)
        return veh_info, box_info, person_info

    def get_zboxes(self, boxes, im_width, im_height):
        z_boxes = []
        for i in range(min(boxes.shape[0], self.max_boxes)):
            x_center, y_center, width, height = tuple(boxes[i])

            (left, right, top, bottom) = ((x_center - width / 2) * im_width, (x_center + width / 2) * im_width,
                                          (y_center - height / 2) * im_height, (y_center + height / 2) * im_height)
            z_boxes.append([top, left, bottom, right])
        return np.array(z_boxes)
