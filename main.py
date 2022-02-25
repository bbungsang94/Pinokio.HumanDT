#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""@author: MnS Team
"""
import os
import datetime
import time
import utilities.config_mapper as config_mapper
from Runners import run

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


if __name__ == "__main__":
    TimeDict = {'Whole_Time': 0, 'Whole_Frame': 0,
                'Inference_Time': 0, 'Inference_Mean': 0,
                'Recovery_Time': 0, 'Recovery_Count': 0, 'Recovery_Mean': 0,
                'Tracking_Time': 0, 'Tracking_Mean': 0, 'Max_Tracker': 0,
                'Save_Time': 0, 'Save_Mean': 0}
    whole_time_begin = time.time()
    # detector ['efficient', 'ssd_mobile', 'centernet']
    primary_detector_name = 'FasterRCNN'
    recovery_detector_name = 'ssd_mobile'
    # tracker
    trk_name = 'sort_basic'

    config = config_mapper.config_copy(
        config_mapper.get_config(
            detection_names=[primary_detector_name, recovery_detector_name],
            tracker_names=[trk_name]))

    config['run_name'] = datetime.datetime.now().strftime('%m-%d %H%M%S')
    config['run_name'] = config['run_name'] + '/'
    if config['run_mode'] != 'Single':
        # int(sqrt(counter)) - 1로 하면됨
        video_list = {0: ["LOADING DOCK F3 Rampa 13 - 14.avi",
                          "LOADING DOCK F3 Rampa 11-12.avi",
                          "LOADING DOCK F3 Rampa 9-10.avi"]
                      }
        config['video_list'] = video_list
    run.standard_run(config)


# State 결정 ( + Box Detector )
# 일정 (다음주 수요일까지)
# Tracking 개선
