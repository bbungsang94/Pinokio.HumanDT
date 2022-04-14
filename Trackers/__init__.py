from functools import partial

from Trackers.GeneralTracker import AbstractTracker
from Trackers.SORT.SORT_basic import SortTracker, SortTrackerEx
from Trackers.SORT.SORT_Color import ColorTracker


def get_tracker(tracker, **kwargs) -> AbstractTracker:
    return tracker(**kwargs)


REGISTRY = {'sort_basic': partial(get_tracker, tracker=SortTracker),
            'sort_ex': partial(get_tracker, tracker=SortTrackerEx),
            'sort_color': partial(get_tracker, tracker=ColorTracker)}
