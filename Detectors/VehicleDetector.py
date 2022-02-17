from Detectors import AbstractDetector
from utilities.media_handler import *
import tensorflow_hub as hub
import time


class VehicleDetector(AbstractDetector):
    def __init__(self, args):
        self.args = args

        if args['hub_mode'] is True:
            self.primary_model = hub.load(args['model_primary_handle'])
        else:# 로컬 모델
            self.primary_model = None

        if args['merged_mode'] is True:
            self.recovery_model = hub.load(args['model_recovery_handle'])
        else:
            self.recovery_model = None

    def detection(self, path, display=False, save=False):
        """Determines the locations of the vehicle in the image

                Args:
                    path: image path
                    display: show figure option
                    save: on display, furthermore you want to save image
                Returns:
                    list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

                """
        if self.recovery_model is not None:
            temp_img = []
            for i in range(len(self.args['merged_list'])):
                try:
                    temp_img.append(ImageManager.load_tensor(self.args.image_path + self.args.merged_list[i] + \
                                                             self.Dataset[i].pop(0)))
                except IndexError:
                    raise NotImplementedError
            img = tf.concat([temp_img[0], temp_img[1], temp_img[2]], axis=1)
        else:
            img = ImageManager.load_tensor(self.args.image_path + path)
        if self.args.merged_mode:
            temp_img = []
            for i in range(len(self.args.merged_list)):
                try:
                    temp_img.append(ImageManager.load_tensor(self.args.image_path + self.args.merged_list[i] + \
                                                             self.Dataset[i].pop(0)))
                except IndexError:
                    raise NotImplementedError
            img = tf.concat([temp_img[0], temp_img[1], temp_img[2]], axis=1)
        else:
            img = ImageManager.load_tensor(self.args.image_path + path)

        converted_img = tf.image.convert_image_dtype(img, tf.uint8)[tf.newaxis, ...]
        try:
            if self.args.model_name == "efficientdet":
                start_time = time.time()
                boxes, scores, classes, num_detections = self.Detector(converted_img)
                end_time = time.time()
                print("Found %d objects." % num_detections)
                boxes = boxes[0].numpy()
                classes = classes[0].numpy()
                scores = scores[0].numpy()
            else:
                start_time = time.time()
                result = self.Detector(converted_img)
                end_time = time.time()
                result = {key: value.numpy() for key, value in result.items()}
                print("Found %d objects." % len(result["detection_scores"]))
                boxes = result["detection_boxes"][0]
                classes = result["detection_classes"][0]
                scores = result["detection_scores"][0]
        except AttributeError:
            raise "Wrong Model Name"
        print("Inference time: ", end_time - start_time)

        del_idx = self.__post_process(classes, scores)
        boxes = boxes[del_idx]
        classes = classes[del_idx]
        classes[:] = 2.
        scores = scores[del_idx]
        if display:
            # image_with_boxes = self.draw_boxes(img.numpy(), boxes, classes, scores)
            ImageManager.display_image(img.numpy())
            if save:
                # imageio.imwrite(self.args.detected_path + path, image_with_boxes)
                raise NotImplementedError


        return img, boxes, classes, scores




