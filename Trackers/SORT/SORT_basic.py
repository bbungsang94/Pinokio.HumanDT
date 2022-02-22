from collections import deque

import numpy as np
from numpy import dot
from scipy.linalg import inv, block_diag
from scipy.optimize import linear_sum_assignment

from Trackers.GeneralTracker import AbstractTracker
from utilities.helpers import box_iou2


class SortTracker(AbstractTracker):
    def __init__(self,
                 model_name='',
                 max_age=0,
                 min_hits=0,
                 iou_thrd=0.0,
                 max_trackers=10,
                 reassign_buffer=0.0,
                 image_size=[]
                 ):
        self.model_name = model_name
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_thrd = iou_thrd
        self.reassign_buffer = reassign_buffer
        self.image_size = image_size

        self.__tracker_list = []  # list for trackers
        self.__track_id_list = deque(range(max_trackers))  # list for track ID
        width_buffer = self.image_size[0] * self.reassign_buffer
        height_buffer = self.image_size[1] * self.reassign_buffer
        self.__reassign_location = (width_buffer, self.image_size[0] - width_buffer,
                                    height_buffer, self.image_size[1] - height_buffer)

        self.__matched_detections = np.array([])
        self.__unmatched_detections = np.array([])
        self.__unmatched_trackers = np.array([])

        self.__older_box = []

    def assign_detections_to_trackers(self, detections):
        """
        From current list of trackers and new detections, output matched detections,
        unmatched trackers, unmatched detections.
        """
        self.__older_box = detections
        IOU_mat = np.zeros((len(self.__tracker_list), len(detections)), dtype=np.float32)
        for t, trk in enumerate(self.__tracker_list):
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
        for t, trk in enumerate(self.__tracker_list):
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
        self.__update_matched()
        self.__update_assign()
        self.__update_loss()

        deleted_tracks = filter(lambda x: x.no_losses > self.max_age, self.__tracker_list)
        self.__tracker_list = [x for x in self.__tracker_list if x.no_losses <= self.max_age]
        return deleted_tracks

    def revive_tracker(self, revive_trk, new_box):
        x = np.array([[new_box[0], 0, new_box[1], 0, new_box[2], 0, new_box[3], 0]]).T
        revive_trk.x_state = x
        revive_trk.predict_only()
        xx = revive_trk.x_state
        xx = xx.T[0].tolist()
        xx = [xx[0], xx[2], xx[4], xx[6]]
        revive_trk.box = xx
        revive_trk.no_losses = self.max_age - 2

        self.__tracker_list.append(revive_trk)

    def delete_tracker(self, delete_id):
        self.__track_id_list.append(delete_id)

    def get_trackers(self):
        return self.__tracker_list

    def __update_matched(self):
        if self.__matched_detections.size > 0:
            for trk_idx, det_idx in self.__matched_detections:
                z = self.__older_box[det_idx]
                z = np.expand_dims(z, axis=0).T
                tmp_trk = self.__tracker_list[trk_idx]
                tmp_trk.kalman_filter(z)
                xx = tmp_trk.x_state.T[0].tolist()
                xx = [xx[0], xx[2], xx[4], xx[6]]
                tmp_trk.box = xx
                tmp_trk.hits += 1
                tmp_trk.no_losses = 0

    def __update_assign(self):
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
                tmp_trk.box = xx # Top, Left, Bottom, Right
                x_mid = (xx[3] + xx[1]) / 2
                y_bottom = xx[2]
                first_condition = self.__reassign_location[0] < x_mid < self.__reassign_location[1]
                second_condition = self.__reassign_location[2] < y_bottom < self.__reassign_location[3]
                if first_condition and second_condition:
                    tmp_trk.id = self.__track_id_list.pop()
                else:

                    tmp_trk.id = self.__track_id_list.popleft()  # assign an ID for the tracker
                self.__tracker_list.append(tmp_trk)

    def __update_loss(self):
        if len(self.__unmatched_trackers) > 0:
            for trk_idx in self.__unmatched_trackers:
                tmp_trk = self.__tracker_list[trk_idx]
                tmp_trk.no_losses += 1
                tmp_trk.predict_only()
                xx = tmp_trk.x_state
                xx = xx.T[0].tolist()
                xx = [xx[0], xx[2], xx[4], xx[6]]
                tmp_trk.box = xx


class SingleTracker:  # class for Kalman Filter-based tracker
    def __init__(self):
        # Initialize parameters for tracker (history)
        self.id = 0  # tracker's id
        self.box = []  # list to store the coordinates for a bounding box
        self.hits = 0  # number of detection matches
        self.no_losses = 0  # number of unmatched tracks (track loss)

        # Initialize parameters for Kalman Filtering
        # The state is the (x, y) coordinates of the detection box
        # state: [up, up_dot, left, left_dot, down, down_dot, right, right_dot]
        # or[up, up_dot, left, left_dot, height, height_dot, width, width_dot]
        self.x_state = []
        self.dt = 1.  # time interval

        # Process matrix, assuming constant velocity model
        self.F = np.array([[1, self.dt, 0, 0, 0, 0, 0, 0],
                           [0, 1, 0, 0, 0, 0, 0, 0],
                           [0, 0, 1, self.dt, 0, 0, 0, 0],
                           [0, 0, 0, 1, 0, 0, 0, 0],
                           [0, 0, 0, 0, 1, self.dt, 0, 0],
                           [0, 0, 0, 0, 0, 1, 0, 0],
                           [0, 0, 0, 0, 0, 0, 1, self.dt],
                           [0, 0, 0, 0, 0, 0, 0, 1]])

        # Measurement matrix, assuming we can only measure the coordinates

        self.H = np.array([[1, 0, 0, 0, 0, 0, 0, 0],
                           [0, 0, 1, 0, 0, 0, 0, 0],
                           [0, 0, 0, 0, 1, 0, 0, 0],
                           [0, 0, 0, 0, 0, 0, 1, 0]])

        # Initialize the state covariance
        self.L = 10.0
        self.P = np.diag(self.L * np.ones(8))

        # Initialize the process covariance
        self.Q_comp_mat = np.array([[self.dt ** 4 / 4., self.dt ** 3 / 2.],
                                    [self.dt ** 3 / 2., self.dt ** 2]])
        self.Q = block_diag(self.Q_comp_mat, self.Q_comp_mat,
                            self.Q_comp_mat, self.Q_comp_mat)

        # Initialize the measurement covariance
        self.R_scaler = 1.0
        self.R_diag_array = self.R_scaler * np.array([self.L, self.L, self.L, self.L])
        self.R = np.diag(self.R_diag_array)

    def update_r(self):
        R_diag_array = self.R_scaler * np.array([self.L, self.L, self.L, self.L])
        self.R = np.diag(R_diag_array)

    def kalman_filter(self, measure):
        """
        Implement the Kalman Filter, including the predict and the update stages,
        with the measurement measure
        """
        x = self.x_state
        # Predict
        x = dot(self.F, x)
        self.P = dot(self.F, self.P).dot(self.F.T) + self.Q

        # Update
        S = dot(self.H, self.P).dot(self.H.T) + self.R
        K = dot(self.P, self.H.T).dot(inv(S))  # Kalman gain
        y = measure - dot(self.H, x)  # residual
        x += dot(K, y)
        self.P = self.P - dot(K, self.H).dot(self.P)
        self.x_state = x.astype(int)  # convert to integer coordinates
        # (pixel values)

    def predict_only(self):
        """
        Implement only the predict stage. This is used for unmatched detections and
        unmatched tracks
        """
        x = self.x_state
        # Predict
        x = dot(self.F, x)
        self.P = dot(self.F, self.P).dot(self.F.T) + self.Q
        self.x_state = x.astype(int)
