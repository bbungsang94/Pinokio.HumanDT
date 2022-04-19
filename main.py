#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""@author: MnS Team
"""
import os
import datetime
import time
import utilities.config_mapper as config_mapper
from Runners import run


def clear_folder(folder_list: list, root: str, body: str, history: bool):
    import shutil
    if os.path.exists(root) is False:
        os.mkdir(root)

    if history is False:
        shutil.rmtree(root)
        os.mkdir(root)
    os.mkdir(root + body)

    append = root + body
    for folder in folder_list:
        if os.path.exists(append + folder):
            shutil.rmtree(append + folder)
        os.mkdir(append + folder)


if __name__ == "__main__":
    config = config_mapper.config_copy(
        config_mapper.get_config())

    config['run_name'] = datetime.datetime.now().strftime('%m-%d %H%M%S')
    config['run_name'] = config['run_name'] + '/'

    if config['run_mode'] != 'Single':
        # int(sqrt(counter)) - 1로 하면됨
        video_list = {0: ["LOADING DOCK F3 Rampa 13 - 14.avi",
                          "LOADING DOCK F3 Rampa 11-12.avi",
                          "LOADING DOCK F3 Rampa 9-10.avi"]
                      }
        config['video_list'] = video_list
    clear_folder(folder_list=[config['image_path'],
                              config['detected_path'],
                              config['tracking_path'],
                              config['trajectory_path']],
                 root=config['output_base_path'],
                 body=config['run_name'],
                 history=config['history'])
    run.standard_run(config)

# Hardware 요구사항, 컨셉, 롤 -> 차주 POC
# 작업세분화 + 기존: 색, 모니터링, 속도
# 요구사항 분석, 진행 마일스톤, 업무내용, 정량적 평가, 릴리즈방식, WSC 논문 요청인원, 양식, 파일첨부
