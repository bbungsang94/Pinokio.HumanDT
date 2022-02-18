from Detectors.Abstract.AbstractDetector import AbstractDetector
from utilities.media_handler import *
import tensorflow_hub as hub
import time


class MobileDetector(AbstractDetector):
    def __init__(self, args):
        self.args = args

        if args['hub_mode'] is True:
            self.Detector = hub.load(args['model_handle'])
        else:# 로컬 모델
            self.Detector = None

    def detection(self, image, display=False, save=False):
        """Determines the locations of the vehicle in the image

                Args:
                    image: image(tensor)
                    display: show figure option
                    save: on display, furthermore you want to save image
                Returns:
                    list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

                """
        converted_img = tf.image.convert_image_dtype(image, tf.uint8)[tf.newaxis, ...]
        try:
            if self.Detector is not None:
                start_time = time.time()
                boxes, scores, classes, num_detections = self.Detector(converted_img)
                end_time = time.time()
                print("Found %d objects." % num_detections)
                boxes = boxes[0].numpy()
                classes = classes[0].numpy()
                scores = scores[0].numpy()
            else:
                return
        except AttributeError:
            raise "Wrong Model Name"
        print("Inference time: ", end_time - start_time)

        del_idx = self.__post_process(classes, scores)
        boxes = boxes[del_idx]
        classes = classes[del_idx]
        classes[:] = 2.
        scores = scores[del_idx]

        return image, boxes, classes, scores




