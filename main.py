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
    config = config_mapper.config_copy(
        config_mapper.get_config())

    config['run_name'] = datetime.datetime.now().strftime('%m-%d %H%M%S')
    config['run_name'] = config['run_name'] + '/'

    if config['run_mode'] != 'Single':
        # int(sqrt(counter)) - 1로 하면됨
        # video_list = {0: ["LOADING DOCK F3 Rampa 13 - 14.avi",
        #                   "LOADING DOCK F3 Rampa 11-12.avi",
        #                   "LOADING DOCK F3 Rampa 9-10.avi"]
        #               }
        video_list = {0: ["Shorts.avi"]
                      }
        config['video_list'] = video_list
    clear_folder(folder_list=[config['image_path'],
                              config['detected_path'],
                              config['tracking_path'],
                              config['trajectory_path']],
                 root=config['output_base_path'] + config['run_name'])
    run.standard_run(config)

# State 결정 ( + Box Detector )
# 일정 (다음주 수요일까지)
# Tracking 개선
# 프레임워크 만들기
# land vehicle 너무 큰 것들 퍼센테이지 조정
# Id 전달 후 Plan 색 합쳐주기
