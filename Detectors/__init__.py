from functools import partial
from Detectors.EfficientDetector import EfficientDetector
from Detectors.CenternetDetector import CenternetDetector
from Detectors.MobileDetector import MobileDetector
from Detectors.Abstract.AbstractDetector import AbstractDetector
import sys
import os


def get_detector(detector, **kwargs) -> AbstractDetector:
    return detector(**kwargs)


REGISTRY = {'efficient': partial(get_detector, detector=EfficientDetector),
            'ssd_mobile': partial(get_detector, detector=MobileDetector),
            'centernet': partial(get_detector, detector=CenternetDetector)}

if sys.platform == "linux":
    os.environ.setdefault("AGV_Path",
                          os.path.join(os.getcwd(), "3rdparty", "./"))