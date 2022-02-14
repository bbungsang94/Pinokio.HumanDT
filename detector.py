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
    fig = plt.figure(figsize=(20, 15))
    plt.grid(False)
    plt.imshow(image)


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
            self.Detector = hub.load(args.model_handle)
        else:
            raise NotImplementedError

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

    def detection(self, path, display=False, save=False):
        """Determines the locations of the vehicle in the image

        Args:
            path: image path
            display: show figure option
            save: on display, furthermore you want to save image
        Returns:
            list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

        """
        img = load_img(self.args.image_path + path)

        converted_img = tf.image.convert_image_dtype(img, tf.uint8)[tf.newaxis, ...]
        start_time = time.time()
        result = self.Detector(converted_img)
        end_time = time.time()

        result = {key: value.numpy() for key, value in result.items()}

        print("Found %d objects." % len(result["detection_scores"]))
        print("Inference time: ", end_time - start_time)

        boxes = result["detection_boxes"][0]
        classes = result["detection_classes"][0]
        scores = result["detection_scores"][0]

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

    def get_zboxes(self, image, boxes, max_boxes=10):
        image = Image.fromarray(np.uint8(image)).convert("RGB")
        z_boxes = []
        for i in range(min(boxes.shape[0], max_boxes)):
            ymin, xmin, ymax, xmax = tuple(boxes[i])
            im_width, im_height = image.size
            (left, right, top, bottom) = (xmin * im_width, xmax * im_width,
                                          ymin * im_height, ymax * im_height)
            z_boxes.append([top, left, bottom, right])
        return np.array(z_boxes)

class CarDetector(object):
    def __init__(self):

        self.car_boxes = []

        os.chdir(cwd)

        # Tensorflow localization/detection model
        # Single-shot-detection with mobile net architecture trained on COCO dataset

        detect_model_name = 'ssd_mobilenet_v1_coco_11_06_2017'

        PATH_TO_CKPT = detect_model_name + '/frozen_inference_graph.pb'

        # setup tensorflow graph
        self.detection_graph = tf.Graph()

        # configuration for possible GPU use
        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        # load frozen tensorflow detection model and initialize 
        # the tensorflow graph
        with self.detection_graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

            self.sess = tf.Session(graph=self.detection_graph, config=config)
            self.image_tensor = self.detection_graph.get_tensor_by_name('image_tensor:0')
            # Each box represents a part of the image where a particular object was detected.
            self.boxes = self.detection_graph.get_tensor_by_name('detection_boxes:0')
            # Each score represent how level of confidence for each of the objects.
            # Score is shown on the result image, together with the class label.
            self.scores = self.detection_graph.get_tensor_by_name('detection_scores:0')
            self.classes = self.detection_graph.get_tensor_by_name('detection_classes:0')
            self.num_detections = self.detection_graph.get_tensor_by_name('num_detections:0')

    # Helper function to convert image into numpy array

    def get_localization(self, image, visual=False):

        """Determines the locations of the cars in the image

        Args:
            image: camera image
            visual: show figure option
        Returns:
            list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

        """
        category_index = {1: {'id': 1, 'name': u'person'},
                          2: {'id': 2, 'name': u'bicycle'},
                          3: {'id': 3, 'name': u'car'},
                          4: {'id': 4, 'name': u'motorcycle'},
                          5: {'id': 5, 'name': u'airplane'},
                          6: {'id': 6, 'name': u'bus'},
                          7: {'id': 7, 'name': u'train'},
                          8: {'id': 8, 'name': u'truck'},
                          9: {'id': 9, 'name': u'boat'},
                          10: {'id': 10, 'name': u'traffic light'},
                          11: {'id': 11, 'name': u'fire hydrant'},
                          13: {'id': 13, 'name': u'stop sign'},
                          14: {'id': 14, 'name': u'parking meter'}}

        with self.detection_graph.as_default():
            image_expanded = np.expand_dims(image, axis=0)
            (boxes, scores, classes, num_detections) = self.sess.run(
                [self.boxes, self.scores, self.classes, self.num_detections],
                feed_dict={self.image_tensor: image_expanded})

            if visual:
                vis_util.visualize_boxes_and_labels_on_image_array(
                    image,
                    np.squeeze(boxes),
                    np.squeeze(classes).astype(np.int32),
                    np.squeeze(scores),
                    category_index,
                    use_normalized_coordinates=True, min_score_thresh=.4,
                    line_thickness=3)

                plt.figure(figsize=(9, 6))
                plt.imshow(image)
                plt.show()

            boxes = np.squeeze(boxes)
            classes = np.squeeze(classes)
            scores = np.squeeze(scores)

            cls = classes.tolist()

            # The ID for car in COCO data set is 3
            idx_vec = [class_id for class_id, v in enumerate(cls) if ((v == 3) and (scores[class_id] > 0.3))]

            if len(idx_vec) == 0:
                print('no detection!')
                self.car_boxes = []
            else:
                tmp_car_boxes = []
                for idx in idx_vec:
                    dim = image.shape[0:2]
                    box = box_normal_to_pixel(boxes[idx], dim)
                    box_h = box[2] - box[0]
                    box_w = box[3] - box[1]
                    ratio = box_h / (box_w + 0.01)

                    if (ratio < 0.8) and (box_h > 20) and (box_w > 20):
                        tmp_car_boxes.append(box)
                        print(box, ', confidence: ', scores[idx], 'ratio:', ratio)

                    else:
                        print('wrong ratio or wrong size, ', box, ', confidence: ', scores[idx], 'ratio:', ratio)

                self.car_boxes = tmp_car_boxes

        return self.car_boxes


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
