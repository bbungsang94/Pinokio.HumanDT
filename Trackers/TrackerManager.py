from collections import deque

from utilities.helpers import get_distance
from utilities.projection_helper import ProjectionManager


class TrackerManager:
    def __init__(self, video_len):
        self.__singleTrackers = dict()
        self.__singleTrackersIds = dict()
        self.__trackers = dict()
        self.__video_len = video_len
        self.__new_assigned_trks = []

    def add_tracker(self, tracker_idx, tracker, max_trackers):
        self.__trackers[tracker_idx] = tracker
        self.__singleTrackersIds[tracker_idx] = deque(range(tracker_idx, max_trackers, self.__video_len))
        self.__trackers[tracker_idx].max_trackers = len(self.__singleTrackersIds[tracker_idx])
        self.__singleTrackers[tracker_idx] = []

    def get_trackers(self):
        return self.__trackers

    def remove_tracker(self, tracker_idx):
        self.__trackers.pop(tracker_idx)

    def tracking(self, det_result):
        whole_deleted_trks = dict()
        for tracker_idx in self.__trackers.keys():
            self.__trackers[tracker_idx].assign_detections_to_trackers(
                detections=det_result[tracker_idx].boxes, trackers=self.__singleTrackers[tracker_idx],
                track_id_list=self.__singleTrackersIds[tracker_idx])
            single_trks, single_trks_ids, deleted_single_trks, new_assigned_trks = self.__trackers[
                tracker_idx].update_trackers()
            self.__singleTrackers[tracker_idx] = single_trks
            self.__singleTrackersIds[tracker_idx] = single_trks_ids
            whole_deleted_trks[tracker_idx] = deleted_single_trks
            self.__new_assigned_trks = new_assigned_trks
        return whole_deleted_trks
        # Post Tracking
        # trks Delete
        # trks Overlap Check
        # trks Update

    def post_tracking(self, delete_ids: dict):
        self.delete_single_tracker(delete_ids)
        self.overlap_check()

    def delete_single_tracker(self, delete_ids: dict):
        for tracker_idx in delete_ids.keys():
            for delete_id in delete_ids[tracker_idx]:
                self.__singleTrackers[tracker_idx] = [x for x in self.__singleTrackers[tracker_idx] if
                                                      x.id != delete_id]
                self.__singleTrackersIds[tracker_idx].append(delete_id)

    def overlap_check(self):
        if len(self.__new_assigned_trks) > 0:
            whole_single_trks = []
            for single_trks in self.__singleTrackers.values():
                for single_trk in single_trks:
                    whole_single_trks.append(single_trk)

            for new_trk in self.__new_assigned_trks:
                xPt, yPt = ProjectionManager.transform(new_trk.box, new_trk.video_idx)
                for target_trk in whole_single_trks:
                    if new_trk.id == target_trk.id:
                        continue
                    target_xPt, target_yPt = ProjectionManager.transform(target_trk.box, target_trk.video_idx)
                    distance = get_distance((xPt, yPt), (target_xPt, target_yPt))
                    if distance < 20:
                        new_trk.id = target_trk.id
                        self.__singleTrackers[target_trk.video_idx].pop(target_trk)
                        self.__singleTrackersIds[target_trk.video_idx].append(target_trk.id)
