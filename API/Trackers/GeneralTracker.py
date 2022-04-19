class AbstractTracker(object):
    def assign_detections_to_trackers(self, detections, trackers, track_id_list):
        """
        From current list of trackers and new detections, output matched detections,
        unmatched trackers, unmatched detections.
        """
        raise NotImplementedError

    def update_trackers(self):
        """ update tracker's attributes"""
        raise NotImplementedError
