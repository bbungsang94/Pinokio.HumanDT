from collections import deque

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from Trackers.single_tracker import SingleTracker
from Trackers.GeneralTracker import AbstractTracker
from utilities.config_mapper import get_yaml
from utilities.helpers import box_iou2, get_distance
from utilities.media_handler import ImageManager
from utilities.projection_helper import ProjectionManager


class DockTracker(AbstractTracker):
    def __init__(self,
                 model_name='',
                 max_age=0,
                 iou_thrd=0.0,
                 reassign_buffer=0.0,
                 exist_division=9,
                 image_size=None,
                 max_trackers=255,
                 video_len=4,
                 video_idx=0,
                 ):
        if image_size is None:
            image_size = []

        self.ModelName = model_name
        self.MaxAge = max_age
        self.IouLim = iou_thrd
        self.ReassignLim = reassign_buffer
        self.ImageSize = image_size
        self.ExistDivision = exist_division
        self.ExistLim = get_distance((0, image_size[1]), (image_size[0], 0)) / self.ExistDivision

        self.MaxTrackers = max_trackers
        self.VideoLen = video_len
        self.VideoIdx = video_idx

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
        self.__TrackerIDs = []

        self.IdleIdList = deque(range(self.VideoIdx, self.MaxTrackers, self.VideoLen))

        self.TestIdx = 0

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
        self.__update_matched(input_image=img)
        self.__update_assign(input_image=img)
        self.__update_loss()

        deleted_tracks = filter(lambda x: x.no_losses > self.MaxAge, self.__Trackers)
        self.__Trackers = [x for x in self.__Trackers if x.no_losses <= self.MaxAge]
        return self.__Trackers

    def sync(self, parents, overlap_dist):
        updated_trackers = []
        for current_tracker in self.__Trackers:
            if len(current_tracker.history) > 0:
                for idx, old_tracker in enumerate(parents):
                    transformed = ProjectionManager.transform(old_tracker.box, self.VideoIdx)
                    distance = get_distance(current_tracker.history[-1], transformed)
                    if distance <= overlap_dist:
                        updated_trackers.append(current_tracker)
                        break

        return updated_trackers

    def __get_new_id(self):
        return self.IdleIdList.popleft()

    def __update_matched(self, input_image: np.array):
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
            tmp_trk.no_losses = 0

    def __update_assign(self, input_image: np.array):
        new_assigned_trks = []
        if len(self.__UnmatchedDet) > 0:
            for idx in self.__UnmatchedDet:
                z = self.__OlderBox[idx]
                tmp_trk = SingleTracker()  # Create a new tracker
                z = np.expand_dims(z, axis=0).T
                x = np.array([[z[0], 0, z[1], 0, z[2], 0, z[3], 0]]).T
                tmp_trk.x_state = x
                tmp_trk.predict_only()
                xx = tmp_trk.x_state
                xx = xx.T[0].tolist()
                xx = [xx[0], xx[2], xx[4], xx[6]]
                tmp_trk.box = xx  # Top, Left, Bottom, Right
                tmp_trk.id = self.__get_new_id()
                tmp_trk.video_idx = self.VideoIdx
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

    def __is_exist_tracker(self, key: int):
        return key in self.__TrackerIDs


if __name__ == "__main__":
    test = DockTracker(model_name='sort_color',
                       max_age=4,
                       iou_thrd=0.3,
                       reassign_buffer=0.3,
                       exist_division=7,
                       image_size=[],
                       color_path="D:/MnS/HumanDT/Pinokio.HumanDT/config/model/tracking/tracking_color.yaml")
    test2 = None
