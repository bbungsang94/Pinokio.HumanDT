import cv2
import numpy as np
import os
import datetime
import time

from utilities import config_mapper
from Runners import run
from Runners.cacasde_run import CascadeRunner
from utilities.media_handler import ImageManager
from utilities.projection_helper import ProjectionManager
from PIL import Image


class roi:
    def __init__(self):
        self.TestIdx = {0: 0, 1: 0, 2: 0, 3: 0}

    def run_roi(self, args):
        runner = CascadeRunner(args=args)
        base_root = args['output_base_path'] + args['run_name']
        paths = {'test_path': base_root + args['image_path'],
                 'detected_path': base_root + args['detected_path'],
                 'tracking_path': base_root + args['tracking_path'],
                 'plan_path': base_root + args['trajectory_path']}

        time_dict = {'Whole_Time': 0, 'Whole_Frame': 0,
                     'Inference_Time': 0, 'Inference_Mean': 0,
                     'Recovery_Time': 0, 'Recovery_Count': 0, 'Recovery_Mean': 0,
                     'Tracking_Time': 0, 'Tracking_Mean': 0, 'Max_Tracker': 0,
                     'Save_Time': 0, 'Save_Mean': 0}
        count = 0
        while True:
            count += 1
            if count % 5 == 0:
                image = runner.get_image()

                ProjectionManager.ColorChecker.new_folder(str(count))
                begin = time.time()
                detect_result, box_anchors = runner.detect(tensor_image=image)
                print("Detection Time:" + str(time.time() - begin))

                self.save_roi(detect_result, image)
            else:
                continue

    def save_roi(self, results, images):
        for idx, result in enumerate(results):
            for box in result.boxes:
                self.match_number(images[idx].numpy(), box, idx)

    def match_number(self, img, box, idx):
        height_min = int(min(box[0], box[2]))
        height_max = int(max(box[0], box[2]))
        width_min = int(min(box[1], box[3]))
        width_max = int(max(box[1], box[3]))
        convert_img = img[..., ::-1].copy()

        roi = convert_img[height_min:height_max, width_min:width_max]
        path = r"D:\source-D\respos-D\Pinokio.HumanDT\test"

        save_path = path + "/anchor/" + str(idx) + "/"
        origin_path = save_path + str(self.TestIdx[idx]) + ".jpeg"

        ImageManager.save_image(roi, origin_path)
        self.TestIdx[idx] += 1

        # blue_mean = 96.6667
        # green_mean = 110.3667
        # red_mean = 119.7667
        #
        # blue_std = 30.5132
        # green_std = 15.3432
        # red_std = 16.3869
        #
        # blue_threshold = int(blue_mean + 2 * blue_std)
        # green_threshold = int(green_mean + 2 * green_std)
        # red_threshold = int(red_mean + 2 * red_std)
        # max_bgr_threshold = [blue_threshold, green_threshold, red_threshold]
        # min_bgr_threshold = [blue_mean - 2 * blue_std, green_mean - 2 * green_std, red_mean - 2 * red_std]
        #
        # blue_condition = (roi[:, :, 0] < min_bgr_threshold[0]) | (max_bgr_threshold[0] < roi[:, :, 0])
        # green_condition = (roi[:, :, 1] < min_bgr_threshold[1]) | (max_bgr_threshold[1] < roi[:, :, 1])
        # red_condition = (roi[:, :, 2] < min_bgr_threshold[2]) | (max_bgr_threshold[2] < roi[:, :, 2])
        # thresholds = (blue_condition | green_condition | red_condition)
        # origin_path = save_path + "/origin/" + str(self.TestIdx) + ".jpeg"
        # convert_path = save_path + "/converted/" + str(self.TestIdx) + ".jpeg"
        # ImageManager.save_image(roi, origin_path)
        # roi[thresholds] = [0, 0, 0]
        #
        # ImageManager.save_image(roi, convert_path)
        # self.TestIdx += 1


if __name__ == "__main__":
    config = config_mapper.config_copy(config_mapper.get_config())
    config['run_name'] = datetime.datetime.now().strftime('%m-%d %H%M%S')
    config['run_name'] = config['run_name'] + '/'

    test = roi()

    test.run_roi(config)


