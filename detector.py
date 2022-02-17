"""
Implement and test car detection (localization)
"""
import os
import time
import tempfile
import yaml
import imageio

from glob import glob
from PIL import Image, ImageColor
from PIL import ImageOps, ImageDraw, ImageFont

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub

from matplotlib import pyplot as plt
from six.moves.urllib.request import urlopen
from six import BytesIO

cwd = os.path.dirname(os.path.realpath(__file__))


# Uncomment the following two lines if need to use the Tensorflow visualization_units
# os.chdir(cwd+'/models')
# from object_detection.utils import visualization_utils as vis_util

def load_image_into_numpy_array(image):
    (im_width, im_height) = image.size
    return np.array(image.getdata()).reshape(
        (im_height, im_width, 3)).astype(np.uint8)
    # Helper function to convert normalized box coordinates to pixels


def box_normal_to_pixel(box, dim):
    height, width = dim[0], dim[1]
    box_pixel = [int(box[0] * height), int(box[1] * width), int(box[2] * height), int(box[3] * width)]
    return np.array(box_pixel)


def load_img(path):
    img = tf.io.read_file(path)
    img = tf.image.decode_jpeg(img, channels=3)
    return img


def display_image(image):
    return None
    # fig = plt.figure(figsize=(20, 15))
    # plt.grid(False)
    # plt.imshow(image)


def download_and_resize_image(url,
                              new_width=256, new_height=256,
                              display=False):
    _, filename = tempfile.mkstemp(suffix=".jpg")
    response = urlopen(url)
    image_data = response.read()
    image_data = BytesIO(image_data)
    pil_image = Image.open(image_data)
    pil_image = ImageOps.fit(pil_image, (new_width, new_height), Image.ANTIALIAS)
    pil_image_rgb = pil_image.convert("RGB")
    pil_image_rgb.save(filename, format="JPEG", quality=90)
    print("Image downloaded to %s." % filename)
    if display:
        display_image(pil_image)
    return filename


class VehicleDetector:
    def __init__(self, args):
        self.args = args
        print(tf.__version__)
        print("사용가능한 GPU : %s" % tf.test.gpu_device_name())
        if args.hub_mode:
            self.Detector = hub.load(args.model_main_handle)
            self.SubDetector = hub.load(args.model_sub_handle)
        else:
            raise NotImplementedError

        self.Dataset = []
        if args.merged_mode:
            for title in args.merged_list:
                img_list = os.listdir(args.image_path + title)
                for file in img_list:
                    if file.endswith(".jpg") or file.endswith(".jpeg"):
                        continue
                    else:
                        img_list.remove(file)
                self.Dataset.append(img_list.copy())
        else:
            img_list = os.listdir(args.image_path)
            for file in img_list:
                if file.endswith(".jpg") or file.endswith(".jpeg"):
                    continue
                else:
                    img_list.remove(file)
            self.Dataset = img_list

        with open(args.label_path) as f:
            self.LabelList = yaml.load(f, Loader=yaml.FullLoader)

        self.Colors = list(ImageColor.colormap.values())

        try:
            self.Font = ImageFont.truetype(
                "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Regular.ttf", 25)
        except IOError:
            print("Font not found, using default font.")
            self.Font = ImageFont.load_default()

    def __post_process(self, classes, scores, min_score = None):
        if min_score is None:
            min_score = self.args.detect_min_score
        score_idx = scores > min_score
        class_idx = (10 > classes) & (classes > 1)
        total_idx = score_idx & class_idx
        return total_idx

    def post_detection(self, img):
        converted_img = tf.image.convert_image_dtype(img, tf.uint8)[tf.newaxis, ...]

        result = self.SubDetector(converted_img)
        end_time = time.time()
        result = {key: value.numpy() for key, value in result.items()}

        boxes = result["detection_boxes"][0]
        classes = result["detection_classes"][0]
        scores = result["detection_scores"][0]

        del_idx = self.__post_process(classes, scores, min_score=0.3)
        boxes = boxes[del_idx]
        classes = classes[del_idx]
        classes[:] = 2.
        scores = scores[del_idx]

        return boxes

    def detection(self, path, display=False, save=False):
        """Determines the locations of the vehicle in the image

        Args:
            path: image path
            display: show figure option
            save: on display, furthermore you want to save image
        Returns:
            list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

        """
        if self.args.merged_mode:
            temp_img = []
            for i in range(len(self.args.merged_list)):
                try:
                    temp_img.append(load_img(self.args.image_path + self.args.merged_list[i] + self.Dataset[i].pop(0)))
                except IndexError:
                    raise NotImplementedError
            img = tf.concat([temp_img[0], temp_img[1], temp_img[2]], axis=1)
        else:
            img = load_img(self.args.image_path + path)

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
            image_with_boxes = self.draw_boxes(img.numpy(), boxes, classes, scores)
            display_image(image_with_boxes)
            if save:
                imageio.imwrite(self.args.detected_path + path, image_with_boxes)

        return img, boxes, classes, scores

    def draw_bounding_box_on_image(self, image,
                                   ymin, xmin, ymax, xmax,
                                   color, thickness=4, display_str_list=()):
        """Adds a bounding box to an image."""
        draw = ImageDraw.Draw(image)
        im_width, im_height = image.size
        if self.args.model_name == "efficientdet":
            (left, right, top, bottom) = (xmin, xmax, ymin, ymax)
        else:
            (left, right, top, bottom) = (xmin * im_width, xmax * im_width,
                                          ymin * im_height, ymax * im_height)
        draw.line([(left, top), (left, bottom), (right, bottom), (right, top),
                   (left, top)],
                  width=thickness,
                  fill=color)

        # If the total height of the display strings added to the top of the bounding
        # box exceeds the top of the image, stack the strings below the bounding box
        # instead of above.
        display_str_heights = [self.Font.getsize(ds)[1] for ds in display_str_list]
        # Each display_str has a top and bottom margin of 0.05x.
        total_display_str_height = (1 + 2 * 0.05) * sum(display_str_heights)

        if top > total_display_str_height:
            text_bottom = top
        else:
            text_bottom = bottom + total_display_str_height
        # Reverse list and print from bottom to top.
        for display_str in display_str_list[::-1]:
            text_width, text_height = self.Font.getsize(display_str)
            margin = np.ceil(0.05 * text_height)
            draw.rectangle([(left, text_bottom - text_height - 2 * margin),
                            (left + text_width, text_bottom)],
                           fill=color)
            draw.text((left + margin, text_bottom - text_height - margin),
                      display_str,
                      fill="black",
                      font=self.Font)
            text_bottom -= text_height - 2 * margin

    def draw_boxes(self, image, boxes, class_idx, scores, max_boxes=10, min_score=0.1):
        """Overlay labeled boxes on an image with formatted scores and label names."""
        class_idx = class_idx.astype(np.int32)
        for i in range(min(boxes.shape[0], max_boxes)):
            if scores[i] >= min_score:
                ymin, xmin, ymax, xmax = tuple(boxes[i])
                display_str = "{}: {}%".format(self.LabelList[class_idx[i]],
                                               int(100 * scores[i]))
                color = self.Colors[class_idx[i] % len(self.Colors)]
                image_pil = Image.fromarray(np.uint8(image)).convert("RGB")
                self.draw_bounding_box_on_image(
                    image_pil,
                    ymin,
                    xmin,
                    ymax,
                    xmax,
                    color,
                    display_str_list=[display_str])
                np.copyto(image, np.array(image_pil))
        return image

    def get_zboxes(self, image, boxes, max_boxes=10, post=None):
        model_name = self.args.model_name
        if post is not None:
            model_name = post
        if model_name == "efficientdet":
            return boxes
        else:
            image = Image.fromarray(np.uint8(image)).convert("RGB")
            z_boxes = []
            for i in range(min(boxes.shape[0], max_boxes)):
                ymin, xmin, ymax, xmax = tuple(boxes[i])
                im_width, im_height = image.size
                (left, right, top, bottom) = (xmin * im_width, xmax * im_width,
                                              ymin * im_height, ymax * im_height)
                z_boxes.append([top, left, bottom, right])
            return np.array(z_boxes)


if __name__ == '__main__':
    # Test the performance of the detector
    det = CarDetector()
    os.chdir(cwd)
    TEST_IMAGE_PATHS = glob(os.path.join('test_images/', '*.jpg'))

    for i, image_path in enumerate(TEST_IMAGE_PATHS[0:2]):
        print('')
        print('*************************************************')

        img_full = Image.open(image_path)
        img_full_np = load_image_into_numpy_array(img_full)
        img_full_np_copy = np.copy(img_full_np)
        start = time.time()
        b = det.get_localization(img_full_np, visual=False)
        end = time.time()
        print('Localization time: ', end - start)
#
