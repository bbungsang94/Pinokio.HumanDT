from functools import partial
from Detectors.EfficientDetector import EfficientDetector
from Detectors.CenternetDetector import CenternetDetector
from Detectors.MobileDetector import MobileDetector
from Detectors.FasterRCNNDetector import OpenImageDetector
from Detectors.PrimarySSD import OpenImageSSD
from Detectors.Yolov5Detector import Yolov5Detector
from Detectors.Abstract.AbstractDetector import AbstractDetector
import sys
import os


def get_detector(detector, **kwargs) -> AbstractDetector:
    return detector(**kwargs)


REGISTRY = {'efficient': partial(get_detector, detector=EfficientDetector),
            'ssd_mobile': partial(get_detector, detector=MobileDetector),
            'centernet': partial(get_detector, detector=CenternetDetector),
            'FasterRCNN': partial(get_detector, detector=OpenImageDetector),
            'PrimarySSD': partial(get_detector, detector=OpenImageSSD),
            'Yolov5': partial(get_detector, detector=Yolov5Detector)}

if sys.platform == "linux":
    os.environ.setdefault("AGV_Path",
                          os.path.join(os.getcwd(), "3rdparty", "./"))