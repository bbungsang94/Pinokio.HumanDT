#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""@author: MnS Team
"""
import os
import datetime
import pickle
import time
import threading
from multiprocessing import Pool

from Detectors import REGISTRY as det_REGISTRY
from Trackers import REGISTRY as trk_REGISTRY
from utilities.media_handler import PipeliningVideoManager, ImageManager
import utilities.config_mapper as config_mapper
from utilities.helpers import post_iou_checker, draw_box_label, transform


def clear_folder(folder_list: list, root: str):
    import shutil
    try:
        if root != '' and os.path.exists(root) is False:
            os.mkdir(root)
    except FileNotFoundError:
        (dot, output, runtime, name, empty) = root.split('/')
        os.mkdir(dot + '/' + output + '/' + runtime)
        os.mkdir(dot + '/' + output + '/' + runtime + '/' + name)
    for folder in folder_list:
        if os.path.exists(root + folder):
            shutil.rmtree(root + folder)
        os.mkdir(root + folder)


class DictToStruct:
    def __init__(self, **entries):
        self.__dict__.update(entries)





def inference(model):
    _, np_image = model['video_handle'].pop()
    if np_image is None:
        model['results'] = (None, None, None, None)
        return
    model['image'] = np_image
    tensor_image = ImageManager.convert_tensor(np_image)

    raw_image, boxes, classes, scores = model['detector'].detection(tensor_image)
    boxes = model['detector'].get_zboxes(boxes, model['image_size'][0], model['image_size'][1])
    model['results'] = (raw_image, boxes, classes, scores)
    return model


def save_images(info):
    (test_img, detected_img, tracking_img) = info['images']
    # Test
    ImageManager.save_image(test_img,
                            info['test_path'] + info['model']['video_handle'].make_image_name())
    # Detection
    ImageManager.save_tensor(detected_img,
                             info['detected_path'] + info['model']['video_handle'].make_image_name())
    # Tracking
    ImageManager.save_image(tracking_img,
                            info['tracking_path'] + info['model']['video_handle'].make_image_name())


def pipeliningMerge(args):

if __name__ == "__main__":
    TimeDict = {'Whole_Time': 0, 'Whole_Frame': 0,
                'Inference_Time': 0, 'Inference_Mean': 0,
                'Recovery_Time': 0, 'Recovery_Count': 0, 'Recovery_Mean': 0,
                'Tracking_Time': 0, 'Tracking_Mean': 0, 'Max_Tracker': 0,
                'Save_Time': 0, 'Save_Mean': 0}
    whole_time_begin = time.time()
    # detector ['efficient', 'ssd_mobile', 'centernet']
    primary_detector_name = 'efficient'
    recovery_detector_name = 'ssd_mobile'
    # tracker
    trk_name = 'sort_basic'

    config = config_mapper.config_copy(
        config_mapper.get_config(
            detection_names=[primary_detector_name, recovery_detector_name],
            tracker_names=[trk_name]))

    config['run_name'] = datetime.datetime.now().strftime('%m-%d %H%M%S')
    config['run_name'] = config['run_name'] + '/'
    if config['parallel_mode']:
        # int(sqrt(counter)) - 1로 하면됨
        video_list = {0: ["LOADING DOCK F3 Rampa 13 - 14.avi",
                          "LOADING DOCK F3 Rampa 11-12.avi",
                          "LOADING DOCK F3 Rampa 9-10.avi"]
                      }
    else:
        config['video_name'] = "LOADING DOCK F3 Rampa 9-10.avi"
        clear_folder(
            [config['detected_path'], config['tracking_path'], config['trajectory_path'], config['image_path']],
            config['output_base_path'] + config['run_name'])

    # 빠른 처리에는 존재할 수가 있음

    # pipeliningSingle(args=config)
    pipeliningParallel(args=config)
    TimeDict['Whole_Time'] = time.time() - whole_time_begin
    TimeDict['Inference_Mean'] = TimeDict['Inference_Time'] / TimeDict['Whole_Frame']
    TimeDict['Recovery_Mean'] = TimeDict['Recovery_Time'] / TimeDict['Recovery_Count']
    TimeDict['Tracking_Mean'] = TimeDict['Tracking_Time'] / TimeDict['Whole_Frame']

    print("[Whole time]: {0}, [Frame count]: {1}".format(TimeDict['Whole_Time'], TimeDict['Whole_Frame']))
    print("[Inference time]: {0}, [Inference Mean]: {1}".format(TimeDict['Inference_Time'], TimeDict['Inference_Mean']))
    print("[Recovery time]: {0}, [Recovery count]: {1}, [Recovery mean]: {2}".format(TimeDict['Recovery_Time'],
                                                                                     TimeDict['Recovery_Count'],
                                                                                     TimeDict['Recovery_Mean']))
    print("[Tracker time]: {0}, [Max Tracker]: {1}, [Tracker mean]: {2}".format(TimeDict['Tracking_Time'],
                                                                                TimeDict['Max_Tracker'],
                                                                                TimeDict['Tracking_Mean']))
    if config['save']:
        TimeDict['Save_Mean'] = TimeDict['Save_Time'] / TimeDict['Whole_Frame']
        print("[Save time]: {0}, [Save mean]: {1}".format(TimeDict['Save_Time'], TimeDict['Save_Mean']))

# State 결정 ( + Box Detector )
# 일정 (다음주 수요일까지)
# Tracking 개선
