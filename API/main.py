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

    clear_folder(folder_list=[config['image_path'],
                              config['detected_path'],
                              config['tracking_path'],
                              config['trajectory_path']],
                 root=config['output_base_path'],
                 body=config['run_name'],
                 history=config['history'])
    run.standard_run(config)
