#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""@author: kyleguan
"""
import math
import os
import time
import argparse
import datetime

import imageio
import numpy as np
import torch
import matplotlib.pyplot as plt
import glob
from moviepy.editor import VideoFileClip
from collections import deque
from scipy.optimize import linear_sum_assignment

import helpers
import detector
import tracker
import pickle

from utilities.media_handler import PipeliningVideoManager, ImageManager
from Detectors import REGISTRY as det_REGISTRY
import utilities.config_mapper as config_mapper
import threading

debug = True


def assign_detections_to_trackers(trackers, detections, iou_thrd=0.3):
    """
    From current list of trackers and new detections, output matched detections,
    unmatched trackers, unmatched detections.
    """

    IOU_mat = np.zeros((len(trackers), len(detections)), dtype=np.float32)
    for t, trk in enumerate(trackers):
        # trk = convert_to_cv2bbox(trk)
        for d, det in enumerate(detections):
            #   det = convert_to_cv2bbox(det)
            IOU_mat[t, d] = helpers.box_iou2(trk, det)

            # Produces matches
    # Solve the maximizing the sum of IOU assignment problem using the
    # Hungarian algorithm (also known as Munkres algorithm)

    matched_idx = linear_sum_assignment(-IOU_mat)
    matched_idx = np.asarray(matched_idx)
    matched_idx = np.transpose(matched_idx)

    unmatched_trackers, unmatched_detections = [], []
    for t, trk in enumerate(trackers):
        if t not in matched_idx[:, 0]:
            unmatched_trackers.append(t)

    for d, det in enumerate(detections):
        if d not in matched_idx[:, 1]:
            unmatched_detections.append(d)

    matches = []

    # For creating trackers we consider any detection with an 
    # overlap less than iou_thrd to signifiy the existence of 
    # an untracked object

    for m in matched_idx:
        if IOU_mat[m[0], m[1]] < iou_thrd:
            unmatched_trackers.append(m[0])
            unmatched_detections.append(m[1])
        else:
            matches.append(m.reshape(1, 2))

    if len(matches) == 0:
        matches = np.empty((0, 2), dtype=int)
    else:
        matches = np.concatenate(matches, axis=0)

    return matches, np.array(unmatched_detections), np.array(unmatched_trackers)


def pipeline(path, plan_image, transform_matrix, args):
    """
    Pipeline function for detection and tracking
    """
    global frame_count
    global tracker_list
    global max_age
    global min_hits
    global track_id_list
    global debug

    frame_count += 1

    raw_image, boxes, classes, scores = det.detection(path, display=debug, save=True)  # box 여러개
    z_box = det.get_zboxes(image=raw_image, boxes=boxes)
    if debug:
        print('Frame:', frame_count)

    x_box = []

    if len(tracker_list) > 0:
        for trk in tracker_list:
            x_box.append(trk.box)

    matched, unmatched_dets, unmatched_trks \
        = assign_detections_to_trackers(x_box, z_box, iou_thrd=0.3)
    if debug:
        print('Detection: ', z_box)
        print('x_box: ', x_box)
        print('matched:', matched)
        print('unmatched_det:', unmatched_dets)
        print('unmatched_trks:', unmatched_trks)

    # Deal with matched detections     
    if matched.size > 0:
        for trk_idx, det_idx in matched:
            z = z_box[det_idx]
            z = np.expand_dims(z, axis=0).T
            tmp_trk = tracker_list[trk_idx]
            tmp_trk.kalman_filter(z)
            xx = tmp_trk.x_state.T[0].tolist()
            xx = [xx[0], xx[2], xx[4], xx[6]]
            x_box[trk_idx] = xx
            tmp_trk.box = xx
            tmp_trk.hits += 1
            tmp_trk.no_losses = 0

    # Deal with unmatched detections      
    if len(unmatched_dets) > 0:
        for idx in unmatched_dets:
            z = z_box[idx]
            z = np.expand_dims(z, axis=0).T
            tmp_trk = tracker.Tracker()  # Create a new tracker
            x = np.array([[z[0], 0, z[1], 0, z[2], 0, z[3], 0]]).T
            tmp_trk.x_state = x
            tmp_trk.predict_only()
            xx = tmp_trk.x_state
            xx = xx.T[0].tolist()
            xx = [xx[0], xx[2], xx[4], xx[6]]
            tmp_trk.box = xx
            tmp_trk.id = track_id_list.popleft()  # assign an ID for the tracker
            tracker_list.append(tmp_trk)
            x_box.append(xx)

    # Deal with unmatched tracks       
    if len(unmatched_trks) > 0:
        for trk_idx in unmatched_trks:
            tmp_trk = tracker_list[trk_idx]
            tmp_trk.no_losses += 1
            tmp_trk.predict_only()
            xx = tmp_trk.x_state
            xx = xx.T[0].tolist()
            xx = [xx[0], xx[2], xx[4], xx[6]]
            tmp_trk.box = xx
            x_box[trk_idx] = xx

    # Bookkeeping
    deleted_tracks = filter(lambda x: x.no_losses > max_age, tracker_list)

    for trk in deleted_tracks:
        # SSD Network 에도 잡히지 않는지 확인
        boxes = det.post_detection(raw_image)
        post_box = det.get_zboxes(image=raw_image, boxes=boxes, post='SSDNet')
        post_pass, box = helpers.post_iou_checker(trk.box, post_box, thr=0.2, offset=0.3)
        if post_pass:
            x = np.array([[box[0], 0, box[1], 0, box[2], 0, box[3], 0]]).T
            trk.x_state = x
            trk.predict_only()
            xx = trk.x_state
            xx = xx.T[0].tolist()
            xx = [xx[0], xx[2], xx[4], xx[6]]
            trk.box = xx
            trk.no_losses -= 2
        else:
            track_id_list.append(trk.id)

    # The list of tracks to be annotated
    good_tracker_list = []
    np_image = raw_image.numpy()
    for trk in tracker_list:
        if (trk.hits >= min_hits) and (trk.no_losses <= max_age):
            good_tracker_list.append(trk)
            x_cv2 = trk.box
            if debug:
                print('updated box: ', x_cv2)
                print()

            np_image = helpers.draw_box_label(np_image, x_cv2, det.Colors[trk.id % len(det.Colors)])
            plan_image = helpers.transform(x_cv2, np_image, plan_image, transform_matrix,
                                           det.Colors[trk.id % len(det.Colors)])
            tracker_list = [x for x in tracker_list if x.no_losses <= max_age]

    if debug:
        print('Ending tracker_list: ', len(tracker_list))
        print('Ending good tracker_list: ', len(good_tracker_list))

    return np_image, plan_image



def clear_folder(folder_list: list, root: str):
    import shutil
    if root != '' and os.path.exists(root) is False:
        os.mkdir(root)
    for folder in folder_list:
        if os.path.exists(root + folder):
            shutil.rmtree(root + folder)
        os.mkdir(root + folder)


class DictToStruct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def pipelining(args):
    # 0. Init

    # 1. Video loaded
    video_handle = PipeliningVideoManager()
    video_handle.load_video(args['video_path'])
    video_handle.activate_video_object(args['video_path'])
    _, np_image = video_handle.pop()

    if args['debug']:
        ImageManager.save_image(np_image, args.image_path)
    # 2. To detection
    tensor_image = ImageManager.convert_tensor(np_image)
    raw_image, boxes, classes, scores = det.detection(tensor_image, display=args['visible'], save=args['save'])  # box 여러개

    # ---- 쓰레드 안써도 될듯 ---
    # 2. Threading 활성화
    # 2-1. 비디오에서 이미지 만드는 쓰레드
    # 2-2. 이미지 불러와서 디텍션 + 트랙킹하는 쓰레드
    # 2-3. 처리하는대로 바로 파이프라인 비디오 매니저에 append
    # 3. 종료시 쓰레드 클리어, 비디오 생성
    video_handle.release_video_object()


if __name__ == "__main__":
    detectors = ['efficient', 'ssd_mobile']
    config = config_mapper.config_copy(config_mapper.get_config(detection_names=detectors))
    config['run_name'] = datetime.datetime.now().strftime('%m-%d %H%M%S')
    config['video_path'] = "./video/LOADING DOCK F3 Rampa 11-12.avi"

    args.video_path = "LOADING DOCK F3 Rampa 11-12.avi"	primary_detector = det_REGISTRY[primary_model_args['model_name']](**primary_model_args)
    recovery_detector = det_REGISTRY[recovery_model_args['model_name']](**primary_model_args)    # 빠른 처리에는 존재할 수가 있음
    clear_folder([config['detected_path'], config['tracking_path'], config['trajectory_path']],
                 config['output_base_path'] + config['run_name'])
    clear_folder([config['image_path']], "")

    pipelining(args=config)

    # # 민구 transform
    # plan_image = detector.load_img("./params/testPlan.JPG")
    # plan_image = plan_image.numpy()
    # with open('./params/LOADING DOCK F3 Rampa 13 - 14.pickle', 'rb') as matrix:
    #     transform_matrix = pickle.load(matrix)
    #
    # det = dict
    # det_list = ['primary', 'recovery', 'box']
    # for i, model in enumerate(args.model_name):
    #     det[det_list[i]] = det_REGISTRY[model](**args.detector_args)
    #
    # det['recovery'].detection(img)
    #
    # args.model_name = "efficient"
    # args.model_handle = "primary link"
    # det = detector.VehicleDetector(args=args)
    # vehicleDetector = EFF(args)
    # SSDDetector
    # MobileDetector
    # EffDetector
    # args.model_name = "mobile"
    # args.model_handle = "recovery link"
    # det = detector.VehicleDetector(args=args)
    # if debug:  # test on a sequence of images
    #     images = det.Dataset
    #     if args.merged_mode:
    #         min_len = math.inf
    #         for image_list in det.Dataset:
    #             if len(image_list) < min_len:
    #                 min_len = len(image_list)
    #                 images = image_list
    #     for image in images:
    #         result_img, plan_img = pipeline(image, plan_image, transform_matrix, args)
    #         if args.tracking_path != '':
    #             imageio.imwrite(args.tracking_path + image, result_img)
    #             imageio.imwrite(args.plan_path + image, plan_img)
    #
    # else:  # test on a video file.
    #
    #     start = time.time()
    #     output = 'test_v7.mp4'
    #     clip1 = VideoFileClip("project_video.mp4")  # .subclip(4,49) # The first 8 seconds doesn't have any cars...
    #     clip = clip1.fl_image(pipeline)
    #     clip.write_videofile(output, audio=False)
    #     end = time.time()
    #
    #     print(round(end - start, 2), 'Seconds to finish')
# 파이프라이닝 작업해야됨
# 노이즈 트랙킹 제거
# z 좌표 확실하게
# KPI 산출
# 자체모델 학습 / 공용 모델 단점
