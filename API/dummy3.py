import copy

import cv2
import numpy as np
import pandas as pd
from models.experimental import attempt_load
import torch
import torch.nn.functional as nnf
from utils.general import check_img_size, check_requirements, non_max_suppression, scale_coords, xyxy2xywh
import tensorflow as tf
from utilities.media_handler import ImageManager


class dummy3:
    def __init__(self):
        self.Detector = attempt_load(
            r"D:\source-D\respos-D\Pinokio.HumanDT\API\config\model\weights\yolov5_color_0529.pt",
            map_location=torch.device('cuda:0'))

    def run(self):
        rgb_chart = pd.read_excel(r"D:\source-D\respos-D\Pinokio.HumanDT\test\RGB.xlsx")
        new_raw = {"idx": "", "roi": "",
                   "blue": 0, "green": 0, "red": 0,
                   "hue": 0, "saturation": 0, "value": 0,
                   "width": 0, "height": 0, "confidence": 0}
        for idx in range(0, 2300):
            for folder in range(0, 4):
                img = ImageManager.load_cv(r"D:/source-D/respos-D/Pinokio.HumanDT/test/anchor/" +
                                           str(folder) + "/" + str(idx) + ".jpeg")

                converted_img = ImageManager.convert_tensor(img)

                raw_image, label_info = self.detection(converted_img)

                temp_manager = ImageManager()
                detected_image = temp_manager.draw_boxes_info(image=converted_img, info=(label_info, None))
                ImageManager.save_image(detected_image, r"D:/source-D/respos-D/Pinokio.HumanDT/test/detect/" +
                                        str(folder) + "-" + str(idx) + ".jpeg")
                roi_boxes = label_info[0]
                np_image = converted_img.cpu().numpy()
                for roi_idx, roi_box in enumerate(roi_boxes):
                    height_min = int(min(roi_box[0], roi_box[2]))
                    height_max = int(max(roi_box[0], roi_box[2]))
                    width_min = int(min(roi_box[1], roi_box[3]))
                    width_max = int(max(roi_box[1], roi_box[3]))
                    # convert_img = img[..., ::-1].copy()

                    roi = np_image[height_min:height_max, width_min:width_max]
                    roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                    ImageManager.save_image(roi_rgb, r"D:/source-D/respos-D/Pinokio.HumanDT/test/roi/" +
                                            str(folder) + "-" + str(idx) + "-" + str(roi_idx) + ".jpeg")
                    new_raw["idx"] = str(folder) + "-" + str(idx)
                    new_raw["roi"] = str(roi_idx)
                    new_raw["width"] = width_max - width_min
                    new_raw["height"] = height_max - height_min
                    new_raw["blue"] = np.mean(roi[:, :, 0])
                    new_raw["green"] = np.mean(roi[:, :, 1])
                    new_raw["red"] = np.mean(roi[:, :, 2])
                    new_raw["hue"] = np.mean(roi_hsv[:, :, 0])
                    new_raw["saturation"] = np.mean(roi_hsv[:, :, 1])
                    new_raw["value"] = np.mean(roi_hsv[:, :, 2])
                    new_raw["confidence"] = label_info[2][roi_idx]
                    rgb_chart = rgb_chart.append(new_raw, ignore_index=True)
                    rgb_chart.to_excel(r"D:\source-D\respos-D\Pinokio.HumanDT\test\RGB_log.xlsx")

                np_image = raw_image.cpu().numpy()
                np_image = np_image[:, :]

    def detection(self, input_image):
        """Determines the locations of the vehicle in the image

                Args:
                    input_image: image(tensor)
                Returns:
                    list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

                """
        image = input_image.permute(2, 0, 1)
        # converted_img = tf.image.convert_image_dtype(image, tf.float32)
        device = torch.device('cuda:0')
        image = image.float().to(device)
        image /= 255
        if len(image.shape) == 3:
            converted_img = image[None]  # expand for batch dim
        else:
            converted_img = image
        # tf.reshape()
        # out = nnf.interpolate(converted_img, size=(converted_img.shape[3], converted_img.shape[2]), mode='bicubic', align_corners=False)
        out = nnf.interpolate(converted_img, size=(480, 640), mode='bicubic', align_corners=False)
        pred = self.Detector(out, augment=False, visualize=False)
        pred = non_max_suppression(pred[0], 0.2, 0.3)
        det = pred[0]
        # gn = torch.tensor([640, 480, 640, 480])
        gn = torch.tensor([336, 162, 336, 162])
        result = dict()
        result["detection_boxes"] = np.empty([0, 0])
        result["detection_class_labels"] = np.empty([0, 0])
        result["detection_scores"] = np.empty([0, 0])
        result["detection_class"] = np.empty([0, 0], dtype=np.str)

        detection_boxes = []
        detection_class_labels = []
        detection_scores = []
        detection_class = []
        if len(det):
            # Rescale boxes from img_size to img0 size

            det[:, :4] = scale_coords([480, 640], det[:, :4], input_image.shape).round()

            # Print results
            # for c in det[:, -1].unique():
            #     n = (det[:, -1] == c).sum()  # detections per class
            #
            #     s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

            # Write results
            for *xyxy, conf, cls in reversed(det):
                xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()
                detection_boxes.append(xywh)
                detection_class_labels.append(int(cls))
                detection_scores.append(float(conf))
                detection_class.append(None)

            converted_img = copy.deepcopy(det)
            converted_img[:, 0] = det[:, 1]
            converted_img[:, 1] = det[:, 0]
            converted_img[:, 2] = det[:, 3]
            converted_img[:, 3] = det[:, 2]

            result["detection_boxes"] = np.array(converted_img[:, :4].cpu())
            result["detection_class_labels"] = np.array(detection_class_labels)
            result["detection_scores"] = np.array(detection_scores)
            result["detection_class"] = np.array(detection_class)

            # print(f'Inferencing and Processing Done. ({time.time() - t0:.3f}s)')
            # result = {key: value.numpy() for key, value in result.items()}
        info = tf.shape(input_image)
        label_info = self.__post_process(result, info)
        return converted_img, label_info

    def __post_process(self, result, info):
        boxes = result["detection_boxes"]
        classes_idx = result["detection_class_labels"]
        classes = result["detection_class"]
        scores = result["detection_scores"]

        label_score_idx = scores > 0.2
        label_class_idx = classes_idx == 0
        label_idx = label_class_idx & label_score_idx
        classes[label_idx] = "Label"

        img_shape = np.array(info)
        label_boxes = boxes[label_idx]
        # label_boxes = self.get_zboxes(label_boxes, im_width=img_shape[1], im_height=img_shape[0])
        label_classes = classes[label_idx]
        label_scores = scores[label_idx]
        label_info = (label_boxes, label_classes, label_scores)

        return label_info

    def get_zboxes(self, boxes, im_width, im_height):
        z_boxes = []
        for i in range(min(boxes.shape[0], 100)):
            x_center, y_center, width, height = tuple(boxes[i])

            (left, right, top, bottom) = ((x_center - width / 2) * im_width, (x_center + width / 2) * im_width,
                                          (y_center - height / 2) * im_height, (y_center + height / 2) * im_height)
            z_boxes.append([top, left, bottom, right])
        return np.array(z_boxes)


if __name__ == "__main__":
    test = dummy3()
    test.run()
