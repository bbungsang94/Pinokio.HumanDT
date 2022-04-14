from collections import deque

import numpy as np
from scipy.optimize import linear_sum_assignment
from Trackers.single_tracker import SingleTracker
from Trackers.GeneralTracker import AbstractTracker
from utilities.helpers import box_iou2, get_distance


class SortTracker(AbstractTracker):
    def __init__(self,
                 model_name='',
                 max_age=0,
                 min_hits=0,
                 iou_thrd=0.0,
                 max_trackers=10,
                 reassign_buffer=0.0,
                 exist_division=9,
                 image_size=[],
                 video_idx=0,
                 video_len=1
                 ):
        self.model_name = model_name
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_thrd = iou_thrd
        self.reassign_buffer = reassign_buffer
        self.image_size = image_size
        self.video_idx = video_idx
        self.video_len = video_len
        self.exist_division = exist_division
        self.exist_threshold = get_distance((0, image_size[1]), (image_size[0], 0)) / self.exist_division

        self._tracker_list = []  # list for trackers
        self.reserved_tracker_list = []  # list for reserved trackers

        self._track_id_list = deque()
        self.max_trackers = 0
        width_buffer = self.image_size[0] * self.reassign_buffer
        height_buffer = self.image_size[1] * self.reassign_buffer
        self.__reassign_location = (width_buffer, self.image_size[0] - width_buffer,
                                    height_buffer, self.image_size[1] - height_buffer)

        self.__matched_detections = np.array([])
        self.__unmatched_detections = np.array([])
        self.__unmatched_trackers = np.array([])

        self.__older_box = []

    def adjust_division(self, down_step):
        if self.exist_division >= 4:
            self.exist_division -= down_step
            self.exist_threshold = get_distance((0, self.image_size[1]), (self.image_size[0], 0)) / self.exist_division
            print('adjust_division: ', self.exist_division)

    def assign_detections_to_trackers(self, detections, trackers, track_id_list):
        """
        From current list of trackers and new detections, output matched detections,
        unmatched trackers, unmatched detections.
        """
        self.__older_box = detections
        self._tracker_list = trackers
        self._track_id_list = track_id_list
        IOU_mat = np.zeros((len(self._tracker_list), len(detections)), dtype=np.float32)
        for t, trk in enumerate(self._tracker_list):
            # trk = convert_to_cv2bbox(trk)
            for d, det in enumerate(detections):
                #   det = convert_to_cv2bbox(det)
                IOU_mat[t, d] = box_iou2(trk.box, det)

        # Produces matches
        # Solve the maximizing the sum of IOU assignment problem using the
        # Hungarian algorithm (also known as Munkres algorithm)

        matched_idx = linear_sum_assignment(-IOU_mat)
        matched_idx = np.asarray(matched_idx)
        matched_idx = np.transpose(matched_idx)

        unmatched_trackers, unmatched_detections = [], []
        for t, trk in enumerate(self._tracker_list):
            if t not in matched_idx[:, 0]:
                unmatched_trackers.append(t)

        for d, det in enumerate(detections):
            if d not in matched_idx[:, 1]:
                unmatched_detections.append(d)

        matches = []

        # For creating trackers we consider any detection with an
        # overlap less than iou_thrd to signifiy the existence of
        # an untracked object

        for m in matched_idx:
            if IOU_mat[m[0], m[1]] < self.iou_thrd:
                unmatched_trackers.append(m[0])
                unmatched_detections.append(m[1])
            else:
                matches.append(m.reshape(1, 2))

        if len(matches) == 0:
            matches = np.empty((0, 2), dtype=int)
        else:
            matches = np.concatenate(matches, axis=0)

        self.__matched_detections = matches
        self.__unmatched_detections = np.array(unmatched_detections)
        self.__unmatched_trackers = np.array(unmatched_trackers)

    def update_trackers(self):
        """ update tracker's attributes"""
        self._update_matched()
        new_assigned_trks = self._update_assign()
        self._update_loss()

        deleted_tracks = filter(lambda x: x.no_losses > self.max_age, self._tracker_list)
        # self._tracker_list = [x for x in self._tracker_list if x.no_losses <= self.max_age]
        return self._tracker_list, self._track_id_list, deleted_tracks, new_assigned_trks

    def revive_tracker(self, revive_trk, new_box):
        x = np.array([[new_box[0], 0, new_box[1], 0, new_box[2], 0, new_box[3], 0]]).T
        revive_trk.x_state = x
        revive_trk.predict_only()
        xx = revive_trk.x_state
        xx = xx.T[0].tolist()
        xx = [xx[0], xx[2], xx[4], xx[6]]
        revive_trk.box = xx
        revive_trk.no_losses = self.max_age - 2

        # is_overlap = self._overlap_judge(revive_trk.box)
        # if is_overlap:
        #     self.reserved_tracker_list.append(revive_trk)
        # self._tracker_list.append(revive_trk)

    def delete_tracker(self, delete_id):
        for reserved_trk in self.reserved_tracker_list:  # reserved에 존재할 경우
            if reserved_trk.id == delete_id:
                return
        self._track_id_list.append(delete_id)

    def compare_reserved(self, target_id):
        for reserved_trk in self.reserved_tracker_list:  # reserved에 존재할 경우
            if reserved_trk.id == target_id:
                return True
        return False

    def clean_reserved(self, target_id):
        for reserved_trk in self.reserved_tracker_list:  # reserved에 존재할 경우
            if reserved_trk.id == target_id:
                self.reserved_tracker_list.remove(reserved_trk)
                return True
        return False

    def delete_tracker_forced(self, delete_id):
        if self.clean_reserved(delete_id):
            self._tracker_list = [x for x in self._tracker_list if x.id != delete_id]  # 쓸데없이 많이 탐색 할 수 있음
            self._track_id_list.append(delete_id)

    def get_single_trackers(self):
        return self._tracker_list

    def _update_matched(self):
        if self.__matched_detections.size > 0:
            for trk_idx, det_idx in self.__matched_detections:
                z = self.__older_box[det_idx]
                z = np.expand_dims(z, axis=0).T
                tmp_trk = self._tracker_list[trk_idx]
                tmp_trk.kalman_filter(z)
                xx = tmp_trk.x_state.T[0].tolist()
                xx = [xx[0], xx[2], xx[4], xx[6]]
                tmp_trk.box = xx
                tmp_trk.hits += 1
                tmp_trk.no_losses = 0

    def __is_exist_tracker(self, new_box, thr=0.6):
        for base_tracker in self._tracker_list:
            (xPt, yPt) = (base_tracker.box[0] + base_tracker.box[2]) / 2, \
                         (base_tracker.box[1] + base_tracker.box[3]) / 2
            (new_x, new_y) = (new_box[0] + new_box[2]) / 2, \
                             (new_box[1] + new_box[3]) / 2
            if get_distance((xPt, yPt), (new_x, new_y)) < self.exist_threshold:
                return True
            if box_iou2(base_tracker.box, new_box) > thr:
                return True
        return False

    def _update_assign(self):
        new_assigned_trks = []
        if len(self.__unmatched_detections) > 0:
            for idx in self.__unmatched_detections:
                z = self.__older_box[idx]
                z = np.expand_dims(z, axis=0).T
                tmp_trk = SingleTracker()  # Create a new tracker
                x = np.array([[z[0], 0, z[1], 0, z[2], 0, z[3], 0]]).T
                tmp_trk.x_state = x
                tmp_trk.predict_only()
                xx = tmp_trk.x_state
                xx = xx.T[0].tolist()
                xx = [xx[0], xx[2], xx[4], xx[6]]
                tmp_trk.box = xx  # Top, Left, Bottom, Right
                tmp_trk.video_idx = self.video_idx
                if self.__is_exist_tracker(xx):
                    continue
                x_mid = (xx[3] + xx[1]) / 2
                y_bottom = xx[2]
                reassign = self._reassign_judge(x=x_mid, y=y_bottom)
                reassign = False  # 테스트용

                # 아래부분 코드 병신같음 *****
                if reassign:  # 이미지 중간 부분
                    if self.max_trackers > len(self._track_id_list):
                        tmp_trk.id = self._track_id_list.pop()
                    else:
                        if len(self._tracker_list) > 0:
                            for alternative in self._tracker_list:
                                if box_iou2(tmp_trk.box, alternative.box) > self.iou_thrd:
                                    alternative.box = tmp_trk.box
                                else:
                                    tmp_trk.id = self._track_id_list.popleft()
                        else:
                            tmp_trk.id = self._track_id_list.popleft()
                else:  # 이미지 외곽 부분
                    if len(self._tracker_list) > 0:
                        for alternative in self._tracker_list:
                            if box_iou2(tmp_trk.box, alternative.box) > self.iou_thrd:
                                alternative.box = tmp_trk.box
                            else:
                                tmp_trk.id = self._track_id_list.popleft()  # assign an ID for the tracker
                    else:
                        tmp_trk.id = self._track_id_list.popleft()
                self._tracker_list.append(tmp_trk)
                new_assigned_trks.append(tmp_trk)
        return new_assigned_trks

    def _reassign_judge(self, x, y):
        first_condition = self.__reassign_location[0] < x < self.__reassign_location[1]
        second_condition = self.__reassign_location[2] < y < self.__reassign_location[3]
        return first_condition and second_condition

    def _overlap_judge(self, box):
        left, right = box[1], box[3]
        xPt = (left + right) / 2

        width_buffer = self.image_size[0] * self.reassign_buffer

        if self.video_idx == 0:  # 첫 영상
            if self.image_size[0] - width_buffer < xPt < self.image_size[0]:
                return True
        elif self.video_idx == self.video_len - 1:  # 마지막 영상
            if 0 < xPt < width_buffer:
                return True
        else:
            if (0 < xPt < width_buffer) or (self.image_size[0] - width_buffer < xPt < self.image_size[0]):
                return True
        return False

    def _update_loss(self):
        if len(self.__unmatched_trackers) > 0:
            for trk_idx in self.__unmatched_trackers:
                tmp_trk = self._tracker_list[trk_idx]
                tmp_trk.no_losses += 1
                tmp_trk.predict_only()
                xx = tmp_trk.x_state
                xx = xx.T[0].tolist()
                xx = [xx[0], xx[2], xx[4], xx[6]]
                tmp_trk.box = xx


class SortTrackerEx(SortTracker):
    def update_trackers(self):
        """ update tracker's attributes"""
        self._update_matched()
        self._update_assign()
        self._update_loss()

        deleted_tracks = filter(lambda x: x.no_losses > self.max_age, self._tracker_list)
        self._tracker_list = [x for x in self._tracker_list if x.no_losses <= self.max_age]
        return deleted_tracks

    def _update_assign(self):
        if len(self.__unmatched_detections) > 0:
            for idx in self.__unmatched_detections:
                z = self.__older_box[idx]
                z = np.expand_dims(z, axis=0).T
                tmp_trk = SingleTracker()  # Create a new tracker
                x = np.array([[z[0], 0, z[1], 0, z[2], 0, z[3], 0]]).T
                tmp_trk.x_state = x
                tmp_trk.predict_only()
                xx = tmp_trk.x_state
                xx = xx.T[0].tolist()
                xx = [xx[0], xx[2], xx[4], xx[6]]
                tmp_trk.box = xx  # Top, Left, Bottom, Right
                tmp_trk.video_idx = self.video_idx
                x_mid = (xx[3] + xx[1]) / 2
                y_bottom = xx[2]
                new_assign = self._reassign_judge(x=x_mid, y=y_bottom)
                if new_assign:
                    tmp_trk.id = self._track_id_list.pop()
                else:
                    tmp_trk.id = self._track_id_list.popleft()  # assign an ID for the tracker
                self._tracker_list.append(tmp_trk)
