from collections import deque

import numpy as np

from utilities.helpers import get_distance
from utilities.projection_helper import ProjectionManager


class TrackerManager:
    def __init__(self, video_len):
        self.model_name = 'TrackerManager'
        self.__singleTrackers = dict()
        self.__singleTrackersIds = dict()
        self.__trackers = dict()
        self.__video_len = video_len
        self.__new_assigned_trks = []

    def add_tracker(self, tracker, tracker_idx, max_trackers):
        self.__trackers[tracker_idx] = tracker
        self.__singleTrackersIds[tracker_idx] = deque(range(tracker_idx + 9, max_trackers, self.__video_len))
        self.__trackers[tracker_idx].max_trackers = len(self.__singleTrackersIds[tracker_idx])
        self.__singleTrackers[tracker_idx] = []

    def get_single_trackers(self):
        return self.__singleTrackers

    def get_trackers(self):
        return self.__trackers

    def remove_tracker(self, tracker_idx):
        self.__trackers.pop(tracker_idx)

    def sync_id(self):
        return NotImplementedError

    def tracking(self, boxes, img=None, idx=None):
        whole_deleted_trks = dict()
        self.__new_assigned_trks = []
        for tracker_idx in self.__trackers.keys():
            self.__trackers[tracker_idx].assign_detections_to_trackers(
                detections=boxes[tracker_idx].boxes, trackers=self.__singleTrackers[tracker_idx],
                track_id_list=self.__singleTrackersIds[tracker_idx])
            single_trks, single_trks_ids, deleted_single_trks, new_assigned_trks = self.__trackers[
                tracker_idx].update_trackers()
            self.__singleTrackers[tracker_idx] = single_trks
            self.__singleTrackersIds[tracker_idx] = single_trks_ids
            whole_deleted_trks[tracker_idx] = deleted_single_trks
            self.__new_assigned_trks += new_assigned_trks
        return whole_deleted_trks
        # Post Tracking
        # trks Delete
        # trks Overlap Check
        # trks Update

    def post_tracking(self, delete_ids: dict):
        self.delete_single_tracker(delete_ids)
        # self.overlap_check()

    def delete_single_tracker(self, delete_ids: dict):
        for tracker_idx in delete_ids.keys():
            for delete_trk in delete_ids[tracker_idx]:
                self.__singleTrackers[tracker_idx] = [x for x in self.__singleTrackers[tracker_idx] if
                                                      x.id != delete_trk.id]
                self.__singleTrackersIds[tracker_idx].append(delete_trk.id)

    def overlap_check(self):
        whole_single_trks = []
        for single_trks in self.__singleTrackers.values():
            for single_trk in single_trks:
                whole_single_trks.append(single_trk)

        del_id_list = []
        origin_id_dict = dict()
        for i in range(len(whole_single_trks)):
            one_trk = whole_single_trks[i]
            one_xPt, one_yPt = ProjectionManager.transform(one_trk.box, one_trk.video_idx)
            for j in range(i + 1, len(whole_single_trks)):
                two_trk = whole_single_trks[j]
                two_xPt, two_yPt = ProjectionManager.transform(two_trk.box, two_trk.video_idx)
                distance = get_distance((one_xPt, one_yPt), (two_xPt, two_yPt))
                if distance < 20:
                    if one_trk.hits > two_trk.hits:
                        two_trk.id = one_trk.id
                        one_trk.id = None
                    else:
                        one_trk.id = two_trk.id
                        two_trk.id = None

        for i in range(len(self.__singleTrackers.values())):
            self.__singleTrackers[i] = [x for x in self.__singleTrackers[i] if x.id != None]


class ColorWrapper:
    def __init__(self, local_trackers=None):
        # 지역별로 존재하는 로컬 트랙커의 아이디를 관리해주는 Wrapper
        self.model_name = 'ColorWrapper'
        self.IdleIds = []
        self.__PublicTracker = []
        self.__IdLength = 0
        self.__LocalTrackers = []
        self.__overlap_dist = 20
        if local_trackers is not None:
            for local_tracker in local_trackers:
                self.add_tracker(local_tracker)

    # Call Init section
    def add_tracker(self, tracker, tracker_idx=None, max_trackers=None):
        tracker.set_video_idx(len(self.__LocalTrackers))
        self.__LocalTrackers.append(tracker)
        if len(tracker.ColorID['hsv']) > self.__IdLength:
            self.__IdLength = len(tracker.ColorID['hsv'])
            self.IdleIds = []
            for key in range(0, self.__IdLength):
                self.IdleIds.append(key)

    # Call Init section
    def sync_id(self):
        active_ids = [x for x in range(0, self.__IdLength) if x not in self.IdleIds]
        for idx, local_tracker in enumerate(self.__LocalTrackers):
            local_tracker.set_tracker_id(self.IdleIds)
            # Public tracker랑 동기화
            single_trackers = self.__extract_tracker(idx)
            single_trackers = self.__LocalTrackers[idx].sync(single_trackers)
            for tracker in single_trackers:
                self.__PublicTracker.append((idx, tracker))
                if tracker.id in active_ids:
                    active_ids.remove(tracker.id)

        # 소멸된 ID 수집
        self.IdleIds += active_ids

    # Call running section
    def tracking(self, boxes, img: np.array, idx: int):
        self.__LocalTrackers[idx].assign_detections_to_trackers(detections=boxes)
        new_trk, chg_trk = self.__LocalTrackers[idx].update_trackers(img=img)
        return new_trk

    # Call running section
    def post_tracking(self, new_trackers: dict):
        new_public_trackers = []
        del_idx = []
        for video_idx, new_trackers in new_trackers.items():
            for new_tracker in new_trackers:
                if len(self.__PublicTracker) == 0:
                    self.__PublicTracker.append((video_idx, new_tracker))
                    if new_tracker.id in self.IdleIds:
                        self.IdleIds.remove(new_tracker.id)
                else:
                    for idx, alternative in enumerate(self.__PublicTracker):
                        if self.__overlap_check(alternative, (video_idx, new_tracker)):
                            (_, tracker) = alternative
                            new_tracker.id = tracker.id
                            new_tracker.history = new_tracker.history + tracker.history
                            new_public_trackers.append((video_idx, new_tracker))
                            del_idx.append(alternative)

                        if new_tracker.id in self.IdleIds:
                            self.IdleIds.remove(new_tracker.id)
                        new_public_trackers.append((video_idx, new_tracker))

        while len(del_idx) > 0:
            alternative = del_idx.pop()
            self.__PublicTracker.remove(alternative)

        self.__PublicTracker += new_public_trackers

    def get_single_trackers(self):
        rtn_tracker = dict()
        for (idx, tracker) in self.__PublicTracker:
            if idx not in rtn_tracker:
                rtn_tracker[idx] = []
            rtn_tracker[idx].append(tracker)
        return rtn_tracker

    def __overlap_check(self, a_tracker_info, b_tracker_info):
        (a_video_idx, a_tracker) = a_tracker_info
        (b_video_idx, b_tracker) = b_tracker_info

        a_x, a_y = ProjectionManager.transform(a_tracker.box, a_video_idx)
        b_x, b_y = ProjectionManager.transform(b_tracker.box, b_video_idx)
        distance = get_distance((a_x, a_y), (b_x, b_y))
        if distance < self.__overlap_dist:
            return True
        else:
            return False

    def __extract_tracker(self, matched_idx: int):
        rtn_trackers = []
        for idx, (video_idx, tracker) in enumerate(self.__PublicTracker):
            if video_idx is matched_idx:
                rtn_trackers.append(tracker)
                del self.__PublicTracker[idx]
        return rtn_trackers
