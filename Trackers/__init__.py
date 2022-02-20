from functools import partial

from Trackers.GeneralTracker import AbstractTracker
from Trackers.SORT.SORT_basic import SortTracker


def get_tracker(tracker, **kwargs) -> AbstractTracker:
    return tracker(**kwargs)


REGISTRY = {'sort_basic': partial(get_tracker, tracker=SortTracker)}
