import math
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
        self.IdLength = 0

    def add_tracker(self, tracker, tracker_idx, max_trackers):
        self.__trackers[tracker_idx] = tracker
        self.__singleTrackersIds[tracker_idx] = deque(range(tracker_idx + 9, max_trackers, self.__video_len))
        self.__trackers[tracker_idx].MaxTrackers = len(self.__singleTrackersIds[tracker_idx])
        self.__singleTrackers[tracker_idx] = []

    def get_single_trackers(self):
        return self.__singleTrackers

    def get_trackers(self):
        return self.__trackers

    def get_color(self):
        return None

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

    def get_distance(self):
        return NotImplementedError

    def set_dock_info(self, tracker, dock_id):
        return NotImplementedError

    def get_dock_trackers(self):
        return NotImplementedError


class ColorWrapper:
    def __init__(self, local_trackers=None):
        # 지역별로 존재하는 로컬 트랙커의 아이디를 관리해주는 Wrapper
        self.model_name = 'ColorWrapper'
        self.IdleIds = []
        self.IdLength = 0
        # self.ColorMatcher =
        self.__PublicTracker = []
        self.__LocalTrackers = []
        self.__overlap_dist = 20
        if local_trackers is not None:
            for local_tracker in local_trackers:
                self.add_tracker(local_tracker)

    # Call Init section
    def add_tracker(self, tracker, tracker_idx=None, max_trackers=None):
        tracker.set_video_idx(len(self.__LocalTrackers))
        self.__LocalTrackers.append(tracker)
        if len(tracker.ColorID['hsv']) > self.IdLength:
            self.IdLength = len(tracker.ColorID['hsv'])
            self.IdleIds = []
            for key in range(0, self.IdLength):
                self.IdleIds.append(key)

    # Call Init section
    def sync_id(self):
        active_ids = [x for x in range(0, self.IdLength) if x not in self.IdleIds]
        for idx, local_tracker in enumerate(self.__LocalTrackers):
            local_tracker.set_tracker_id(self.IdleIds)
            # Public tracker랑 동기화
            single_trackers = self.__extract_tracker(idx)
            single_trackers = self.__LocalTrackers[idx].sync(single_trackers, self.__overlap_dist)
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
        overlap_idx = []
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
                            new_tracker.history = tracker.history + new_tracker.history
                            new_public_trackers.append((video_idx, new_tracker))
                            del_idx.append(alternative)
                            overlap_idx.append(new_tracker)

                        if new_tracker.id in self.IdleIds:
                            self.IdleIds.remove(new_tracker.id)
                        new_public_trackers.append((video_idx, new_tracker))

        while len(del_idx) > 0:
            alternative = del_idx.pop()
            self.__PublicTracker.remove(alternative)

        self.__PublicTracker += new_public_trackers
        return overlap_idx

    def get_single_trackers(self):
        rtn_tracker = dict()
        for (idx, tracker) in self.__PublicTracker:
            if idx not in rtn_tracker:
                rtn_tracker[idx] = []
            rtn_tracker[idx].append(tracker)
        return rtn_tracker

    def get_color(self):
        return self.__LocalTrackers[0].ColorID['rgb']

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


class DockWrapper:
    def __init__(self, drawing_scale):
        # 지역별로 존재하는 로컬 트랙커의 아이디를 관리해주는 Wrapper
        self.model_name = 'DockWrapper'
        self.IdLength = 0
        self.__PublicTracker = []
        self.__LocalTrackers = []
        self.__overlap_dist = 20
        self.__DrawingScale = drawing_scale
        self.__DockTrackers = dict()
        self.__ElseTrackers = []
        self.__Distances = dict()

    # Call Init section
    def add_tracker(self, tracker, tracker_idx=None, max_trackers=None):
        tracker.set_video_idx(len(self.__LocalTrackers))
        self.__LocalTrackers.append(tracker)

    # # Call Init section
    # def sync_id(self):
    #     for idx, local_tracker in enumerate(self.__LocalTrackers):
    #         # Public tracker랑 동기화
    #         single_trackers = self.__extract_tracker(idx)
    #         single_trackers = self.__LocalTrackers[idx].sync(single_trackers, self.__overlap_dist)
    #         for tracker in single_trackers:
    #             if tracker.dockNumber != 0:
    #                 self.__DockAssignedTracker.append((tracker.dockNumber, tracker))
    #             self.__PublicTracker.append((idx, tracker))

    # Call running section
    def tracking(self, boxes, img: np.array, idx: int):
        self.__LocalTrackers[idx].assign_detections_to_trackers(detections=boxes)
        singleTrks = self.__LocalTrackers[idx].update_trackers(img=img)
        return singleTrks

    # def sync(self):
    #     for idx, local_tracker in enumerate(self.__LocalTrackers):
    #         # Public tracker랑 동기화
    #         single_trackers = self.__extract_tracker(idx)
    #         single_trackers = self.__LocalTrackers[idx].sync(single_trackers, self.__overlap_dist)
    #         for tracker in single_trackers:
    #             if tracker.dockNumber != 0:
    #                 self.__DockTrackers[tracker.dockNumber] = tracker
    #             else:
    #                 self.__ElseTrackers.append(tracker)

    # Call running section
    def post_tracking(self, new_trackers: dict):
        new_del_trks = []
        ori_del_trks = []
        overlap_trks = []
        new_tracker_list = []
        dock_losses = []
        for trackers in new_trackers.values():
            new_tracker_list += trackers
        tempTrks = []
        for (dock_tracker, _) in self.__DockTrackers.values():
            tempTrks.append(dock_tracker)
        tempTrks += self.__ElseTrackers
        for tempTrk in tempTrks:
            updated = False
            for new_tracker in new_tracker_list:
                if self.__overlap_check(tempTrk, new_tracker):
                    if updated is False:
                        if tempTrk is not new_tracker:
                            if tempTrk.dockNumber == 0:
                                tempTrk.id = new_tracker.id
                            tr_x, tr_y = ProjectionManager.transform(tempTrk.box, tempTrk.video_idx)
                            tempTrk.history.append([tr_x, tr_y])
                            tempTrk.box = new_tracker.box
                        updated = True
                    new_del_trks.append(new_tracker)
            if updated is False:
                ori_del_trks.append(tempTrk)
            overlap_trks += new_del_trks

            while len(new_del_trks) > 0:
                del_trk = new_del_trks.pop()
                new_tracker_list.remove(del_trk)

        while len(ori_del_trks) > 0:
            del_trk = ori_del_trks.pop()
            if del_trk.dockNumber != 0:
                (trk, mileage) = self.__DockTrackers[del_trk.dockNumber]
                trk.state = "NA"
                trk.box = None
                self.__DockTrackers[del_trk.dockNumber] = (trk, mileage)
                dock_losses.append(del_trk.dockNumber)
            tempTrks.remove(del_trk)

        self.__ElseTrackers.clear()
        tempTrks += new_tracker_list
        for tempTrk in tempTrks:
            if tempTrk.dockNumber == 0:
                self.__ElseTrackers.append(tempTrk)

        self.__calculate_dist()
        return dock_losses

    def get_single_trackers(self):
        tempTrks = []
        for (dock_tracker, _) in self.__DockTrackers.values():
            tempTrks.append(dock_tracker)
        tempTrks += self.__ElseTrackers
        rtn_tracker = dict()
        for tracker in tempTrks:
            if tracker.video_idx not in rtn_tracker:
                rtn_tracker[tracker.video_idx] = []
            rtn_tracker[tracker.video_idx].append(tracker)
        return rtn_tracker

    def get_dock_trackers(self):
        return self.__DockTrackers

    def set_dock_info(self, tracker, dock_id):
        if tracker in self.__ElseTrackers:
            if dock_id not in self.__DockTrackers:
                tracker.dockNumber = dock_id
                self.__DockTrackers[dock_id] = (tracker, tracker.Mileage)
            else:
                (old_tracker, mileage) = self.__DockTrackers[dock_id]
                tracker.history = old_tracker.history + tracker.history
                tracker.dockNumber = dock_id
                self.__DockTrackers[dock_id] = (tracker, tracker.Mileage + mileage)
            self.__ElseTrackers.remove(tracker)
            tracker.id = dock_id
            return True
        else:
            return False

    def __calculate_dist(self):
        tempTrks = []
        for (dock_tracker, _) in self.__DockTrackers.values():
            tempTrks.append(dock_tracker)
        tempTrks += self.__ElseTrackers
        for tracker in tempTrks:
            if len(tracker.history) <= 1:
                dist = 0
            else:
                pre_x = tracker.history[-1][0] - tracker.history[-2][0]
                pre_y = tracker.history[-1][1] - tracker.history[-2][1]
                pre_dist = math.sqrt(pre_x ** 2 + pre_y ** 2)
                if tracker.box is None:
                    continue
                tr_x, tr_y = ProjectionManager.transform(tracker.box, tracker.video_idx)
                x = tr_x - tracker.history[-1][0]
                y = tr_y - tracker.history[-1][1]
                dist = math.sqrt(x ** 2 + y ** 2)
                if pre_dist + 1 < dist:
                    dist = 0
                tracker.Distance = dist * self.__DrawingScale
                tracker.Mileage += dist * self.__DrawingScale
        for dock_id, (dock_tracker, dist) in self.__DockTrackers.items():
            old_dist = dock_tracker.Distance
            dock_tracker.Distance = 0
            self.__DockTrackers[dock_id] = (dock_tracker, dist + old_dist)

    def __overlap_check(self, ori_tracker, new_tracker):
        ori_video_idx = ori_tracker.video_idx
        new_video_idx = new_tracker.video_idx

        if ori_tracker.box is not None and new_tracker.box is not None:
            ori_x, ori_y = ProjectionManager.transform(ori_tracker.box, ori_video_idx)
            new_x, new_y = ProjectionManager.transform(new_tracker.box, new_video_idx)

            distance = get_distance((ori_x, ori_y), (new_x, new_y))
            if distance < self.__overlap_dist:
                return True
            else:
                return False
        return False

    def __extract_tracker(self, matched_idx: int):
        rtn_trackers = []
        for idx, (video_idx, tracker) in enumerate(self.__PublicTracker):
            if video_idx is matched_idx:
                rtn_trackers.append(tracker)
                del self.__PublicTracker[idx]
        return rtn_trackers
