import copy

import cv2
import pickle
import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from Trackers.single_tracker import SingleTracker
from Trackers.GeneralTracker import AbstractTracker
from utilities.config_mapper import get_yaml
from utilities.helpers import box_iou2, get_distance
from utilities.media_handler import ImageManager
from collections import deque
from utilities.projection_helper import ProjectionManager
import pandas as pd
import torch
import torch.nn.functional as nnf
from utils.general import non_max_suppression, scale_coords
from models.experimental import attempt_load


class ColorTracker(AbstractTracker):
    def __init__(self,
                 model_name='',
                 max_age=0,
                 iou_thrd=0.0,
                 reassign_buffer=0.0,
                 exist_division=9,
                 image_size=None,
                 color_path=None,
                 color_model=None,
                 label_model=None,
                 max_trackers=255,
                 video_len=4,
                 video_idx=0,
                 ):
        if image_size is None:
            image_size = []
        if color_path is None:
            color_path = []

        self.ModelName = model_name
        self.MaxAge = max_age
        self.IouLim = iou_thrd
        self.ReassignLim = reassign_buffer
        self.ImageSize = image_size
        self.ColorID = get_yaml(color_path)
        self.ColorID = self.ColorID[model_name]
        self.ExistDivision = exist_division
        self.ExistLim = get_distance((0, image_size[1]), (image_size[0], 0)) / self.ExistDivision

        width_buffer = self.ImageSize[0] * self.ReassignLim
        height_buffer = self.ImageSize[1] * self.ReassignLim
        self.__reassign_location = (width_buffer, self.ImageSize[0] - width_buffer,
                                    height_buffer, self.ImageSize[1] - height_buffer)

        self.__MatchedDet = np.array([])
        self.__UnmatchedDet = np.array([])
        self.__UnmatchedTrk = np.array([])
        self.__OlderBox = []
        self.__Trackers = []  # list for trackers
        self.__Alternatives = []  # list for reserved trackers

        with open(color_model, 'rb') as f:
            self.__ColorDetector = pickle.load(f)
        self.__LabelFinder = attempt_load(
            label_model, map_location=torch.device('cuda:0'))

        self.MaxTrackers = max_trackers
        self.VideoLen = video_len
        self.VideoIdx = video_idx
        self.IdleIdList = deque(range(self.VideoIdx + len(self.ColorID['rgb']), self.MaxTrackers, self.VideoLen))

    def set_video_idx(self, idx):
        self.VideoIdx = idx

    def assign_detections_to_trackers(self, detections, trackers=None, track_id_list=None):
        """
        From current list of trackers and new detections, output matched detections,
        unmatched trackers, unmatched detections.
        """
        self.__OlderBox = detections
        iou_mat = self.__iou_calc(det=detections)

        # Produces matches
        # Solve the maximizing the sum of IOU assignment problem using the
        # Hungarian algorithm (also known as Munkres algorithm)

        matched_idx = linear_sum_assignment(-iou_mat)
        matched_idx = np.asarray(matched_idx)
        matched_idx = np.transpose(matched_idx)

        unmatched_trackers, unmatched_detections = self.__hungarian_filter(det=detections, matched_idx=matched_idx)
        matches = []

        # For creating trackers we consider any detection with an
        # overlap less than iou_thrd to signifiy the existence of
        # an untracked object

        for m in matched_idx:
            if iou_mat[m[0], m[1]] < self.IouLim:
                unmatched_trackers.append(m[0])
                unmatched_detections.append(m[1])
            else:
                matches.append(m.reshape(1, 2))

        if len(matches) == 0:
            matches = np.empty((0, 2), dtype=int)
        else:
            matches = np.concatenate(matches, axis=0)

        self.__MatchedDet = matches
        self.__UnmatchedDet = np.array(unmatched_detections)
        self.__UnmatchedTrk = np.array(unmatched_trackers)

    def update_trackers(self, img=None):
        """ update tracker's attributes"""
        if img is None:
            raise "Please set args(image)"
        changed_trackers = self.__update_matched(input_image=img)
        new_assigned_trks = self.__update_assign(input_image=img)
        self.__update_loss()

        deleted_tracks = filter(lambda x: x.no_losses > self.MaxAge, self.__Trackers)
        self.__Trackers = [x for x in self.__Trackers if x.no_losses <= self.MaxAge]
        return self.__Trackers, None

    def change_tracker_id(self, idx, id_val):
        self.__Trackers[idx].id = id_val

    def __get_new_id(self):
        return self.IdleIdList.popleft()

    def __update_matched(self, input_image: np.array):
        changed_trackers = []
        for trk_idx, det_idx in self.__MatchedDet:
            z = self.__OlderBox[det_idx]
            tmp_trk = self.__Trackers[trk_idx]
            z = np.expand_dims(z, axis=0).T
            tmp_trk.kalman_filter(z)
            xx = tmp_trk.x_state.T[0].tolist()
            xx = [xx[0], xx[2], xx[4], xx[6]]
            transformed = ProjectionManager.transform(tmp_trk.box, self.VideoIdx)
            tmp_trk.history.append(list(transformed))
            tmp_trk.box = xx
            if tmp_trk.id > len(self.ColorID['rgb']):
                anchor_img = ImageManager.get_roi(input_image, z)
                tensor_img = ImageManager.convert_tensor(anchor_img, False)
                color_id = self.__get_color_id(tensor_img)
                if color_id is None:
                    color_id = self.__get_new_id()
                else:
                    self.IdleIdList.append(tmp_trk.id)
                tmp_trk.id = color_id

            tmp_trk.video_idx = self.VideoIdx
            tmp_trk.no_losses = 0
            changed_trackers.append(tmp_trk)

        return changed_trackers

    def __update_assign(self, input_image: np.array):
        new_assigned_trks = []
        if len(self.__UnmatchedDet) > 0:
            for idx in self.__UnmatchedDet:
                z = self.__OlderBox[idx]
                tmp_trk = SingleTracker()  # Create a new tracker
                anchor_img = ImageManager.get_roi(input_image, z)
                tensor_img = ImageManager.convert_tensor(anchor_img, False)
                cv2.imwrite(img=input_image, filename=r'D:/source-D/respos-D/Pinokio.HumanDT/API/testdummy/input.jpeg')
                color_id = self.__get_color_id(tensor_img)
                if color_id is None:
                    color_id = self.__get_new_id()
                else:
                    self.IdleIdList.append(tmp_trk.id)
                tmp_trk.id = color_id

                z = np.expand_dims(z, axis=0).T
                x = np.array([[z[0], 0, z[1], 0, z[2], 0, z[3], 0]]).T
                tmp_trk.x_state = x
                tmp_trk.predict_only()
                xx = tmp_trk.x_state
                xx = xx.T[0].tolist()
                xx = [xx[0], xx[2], xx[4], xx[6]]
                tmp_trk.box = xx  # Top, Left, Bottom, Right
                self.__Trackers.append(tmp_trk)
                new_assigned_trks.append(tmp_trk)

        return new_assigned_trks

    def __update_loss(self):
        if len(self.__UnmatchedTrk) > 0:
            for trk_idx in self.__UnmatchedTrk:
                tmp_trk = self.__Trackers[trk_idx]
                tmp_trk.no_losses += 1
                tmp_trk.predict_only()
                xx = tmp_trk.x_state
                xx = xx.T[0].tolist()
                xx = [xx[0], xx[2], xx[4], xx[6]]
                tmp_trk.box = xx

    def __iou_calc(self, det):
        IOU_mat = np.zeros((len(self.__Trackers), len(det)), dtype=np.float32)
        for t, trk in enumerate(self.__Trackers):
            for d, in_det in enumerate(det):
                IOU_mat[t, d] = box_iou2(trk.box, in_det)

        return IOU_mat

    def __hungarian_filter(self, det, matched_idx):
        unmatched_trackers, unmatched_detections = [], []
        for t, trk in enumerate(self.__Trackers):
            if t not in matched_idx[:, 0]:
                unmatched_trackers.append(t)

        for d, det in enumerate(det):
            if d not in matched_idx[:, 1]:
                unmatched_detections.append(d)

        return unmatched_trackers, unmatched_detections

    def __get_color_id(self, img):
        result = self.__find_label(img=img)
        return self.__get_color(result, img)

    def __get_color(self, result, img):
        input_data = {"roi": 0,
                      "blue": 0, "green": 0, "red": 0,
                      "hue": 0, "saturation": 0, "value": 0,
                      "width": 0, "height": 0, "confidence": 0}

        boxes = result["detection_boxes"]
        scores = result["detection_scores"]
        label_score_idx = scores > 0.7
        label_boxes = boxes[label_score_idx]
        color = None
        for roi_idx, roi_box in enumerate(label_boxes):
            height_min = int(min(roi_box[0], roi_box[2]))
            height_max = int(max(roi_box[0], roi_box[2]))
            width_min = int(min(roi_box[1], roi_box[3]))
            width_max = int(max(roi_box[1], roi_box[3]))

            np_image = img.cpu().numpy()
            roi = np_image[height_min:height_max, width_min:width_max]
            roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            input_data["roi"] = roi_idx
            input_data["width"] = width_max - width_min
            input_data["height"] = height_max - height_min
            input_data["blue"] = np.mean(roi[:, :, 0])
            input_data["green"] = np.mean(roi[:, :, 1])
            input_data["red"] = np.mean(roi[:, :, 2])
            input_data["hue"] = np.mean(roi_hsv[:, :, 0])
            input_data["saturation"] = np.mean(roi_hsv[:, :, 1])
            input_data["value"] = np.mean(roi_hsv[:, :, 2])
            input_data["confidence"] = scores[roi_idx]

            df = pd.DataFrame([input_data])

            color = self.__ColorDetector.predict(df)
            if color[0] < len(self.ColorID['rgb']):
                color = color[0]
        return color

    def __find_label(self, img):
        # img - tensor
        image = img.permute(2, 0, 1)
        device = torch.device('cuda:0')
        image = image.float().to(device)
        image /= 255
        if len(image.shape) == 3:
            converted_img = image[None]  # expand for batch dim
        else:
            converted_img = image
        out = nnf.interpolate(converted_img, size=(480, 640), mode='bicubic', align_corners=False)
        pred = self.__LabelFinder(out, augment=False, visualize=False)
        pred = non_max_suppression(pred[0], 0.2, 0.3)
        det = pred[0]
        result = dict()
        result["detection_boxes"] = np.empty([0, 0])
        result["detection_class_labels"] = np.empty([0, 0])
        result["detection_scores"] = np.empty([0, 0])
        result["detection_class"] = np.empty([0, 0], dtype=np.str)

        detection_class_labels = []
        detection_scores = []
        detection_class = []
        if len(det):
            det[:, :4] = scale_coords([480, 640], det[:, :4], img.shape).round()
            for *xyxy, conf, cls in reversed(det):
                detection_class_labels.append(int(cls))
                detection_scores.append(float(conf))
                detection_class.append(None)

            converted_img = copy.deepcopy(det)
            converted_img[:, 0] = det[:, 1]
            converted_img[:, 1] = det[:, 0]
            converted_img[:, 2] = det[:, 3]
            converted_img[:, 3] = det[:, 2]

            result["detection_boxes"] = np.array(converted_img[:, :4].cpu())
            result["detection_class_labels"] = np.array(detection_class_labels)
            result["detection_scores"] = np.array(detection_scores)
            result["detection_class"] = np.array(detection_class)

        return result

if __name__ == "__main__":
    test = ColorTracker(model_name='sort_color',
                        max_age=4,
                        iou_thrd=0.3,
                        reassign_buffer=0.3,
                        exist_division=7,
                        image_size=[],
                        color_path="D:/MnS/HumanDT/Pinokio.HumanDT/config/model/tracking/tracking_color.yaml")
    test2 = None
