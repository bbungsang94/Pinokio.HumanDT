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


def get_args_parser():
    """
    Hub_model links:
    # "https://tfhub.dev/tensorflow/efficientdet/lite4/detection/1"
    # "https://tfhub.dev/tensorflow/efficientdet/lite3/detection/1"
    # "https://tfhub.dev/tensorflow/centernet/resnet101v1_fpn_512x512/1"
    # "https://tfhub.dev/tensorflow/centernet/hourglass_512x512/1"
    # "https://tfhub.dev/tensorflow/ssd_mobilenet_v2/2"
    """
    parser = argparse.ArgumentParser('HumanDT', add_help=False)
    # Get a model on internet
    parser.add_argument('--hub_mode', default=True, type=bool,
                        help="get a model from tensorflow-hub")
    # Model parameters
    parser.add_argument('--model_name', default="efficientdet", type=str,
                        help="name using the model(efficientdet / centernet / ssd_mobilenet")
    parser.add_argument('--model_primary_handle', default="https://tfhub.dev/tensorflow/efficientdet/lite4/detection/1",
                        type=str, help="primary model path about checkpoint or retrained model")
    parser.add_argument('--model_recovery_handle', default="https://tfhub.dev/tensorflow/ssd_mobilenet_v2/2",
                        type=str, help="recovery model path about checkpoint or retrained model")

    # DataSet path
    parser.add_argument('--merged_mode', default=False, type=bool)
    parser.add_argument('--merged_list', default=["13-14_Clips/", "11-12_Clips/", "9-10_Clips/"], type=str)
    parser.add_argument('--video_path', default="", type=str)
    parser.add_argument('--image_path', default="./test_images/", type=str)
    parser.add_argument('--label_path', default="./params/mscoco_label_map.yaml", type=str)
    parser.add_argument('--plan_path', default="./params/testPlan.JPG", type=float)

    # Output path
    parser.add_argument('--output_base_path', default="./output/", type=str)
    parser.add_argument('--run_name', default="", type=str)
    parser.add_argument('--detected_path', default="/detected_images/", type=str)
    parser.add_argument('--tracking_path', default="/tracking_result/", type=str)
    parser.add_argument('--trajectory_path', default="/plan_result/", type=str)

    # Detection / Tracking parameters
    parser.add_argument('--min_score', default=0.3, type=float)
    parser.add_argument('--primary_doi', default=0.3, type=float)
    parser.add_argument('--recovery_doi', default=0.3, type=float)
    parser.add_argument('--recovery_offset', default=0.3, type=float)
    parser.add_argument('--max_age', default=4, type=int)
    parser.add_argument('--min_hits', default=1, type=int)

    # Developer menu
    parser.add_argument('--debug', default=True, type=bool)
    parser.add_argument('--log', default=True, type=bool)
    parser.add_argument('--visible', default=False, type=bool)
    parser.add_argument('--save', default=True, type=bool)
    parser.add_argument('--pipeline', default=True, type=bool)
    parser.add_argument('--citation', default=True, type=bool)

    return parser


def clear_folder(folder_list, root = None):
    import shutil
    for folder in folder_list:
        if os.path.exists(root + folder):
            shutil.rmtree(root + folder)
        os.mkdir(root + folder)

def pipelining(args):
    # 1. Video loaded
    video_handle = PipeliningVideoManager()
    video_handle.update_video_property(args.)
    # 2. Threading 활성화
    # 2-1. 비디오에서 이미지 만드는 쓰레드
    # 2-2. 이미지 불러와서 디텍션 + 트랙킹하는 쓰레드
    # 2-3. 처리하는대로 바로 파이프라인 비디오 매니저에 append
    # 3. 종료시 쓰레드 클리어, 비디오 생성

if __name__ == "__main__":

    parser = argparse.ArgumentParser('Pinokio.HumanDT Inference', parents=[get_args_parser()])
    args = parser.parse_args()
    args.run_name = datetime.datetime.now().strftime('%m-%d %H%M%S')

    # 빠른 처리에는 존재할 수가 있음
    clear_folder(args.output_base_path + args.run_name,
                 [args.detected_path, args.tracking_path, args.trajectory_path])

    pipelining(args=args)


    # 민구 transform
    plan_image = detector.load_img("./params/testPlan.JPG")
    plan_image = plan_image.numpy()
    with open('./params/LOADING DOCK F3 Rampa 13 - 14.pickle', 'rb') as matrix:
        transform_matrix = pickle.load(matrix)

    det = detector.VehicleDetector(args=args)
    if debug:  # test on a sequence of images
        images = det.Dataset
        if args.merged_mode:
            min_len = math.inf
            for image_list in det.Dataset:
                if len(image_list) < min_len:
                    min_len = len(image_list)
                    images = image_list
        for image in images:
            result_img, plan_img = pipeline(image, plan_image, transform_matrix, args)
            if args.tracking_path != '':
                imageio.imwrite(args.tracking_path + image, result_img)
                imageio.imwrite(args.plan_path + image, plan_img)

    else:  # test on a video file.

        start = time.time()
        output = 'test_v7.mp4'
        clip1 = VideoFileClip("project_video.mp4")  # .subclip(4,49) # The first 8 seconds doesn't have any cars...
        clip = clip1.fl_image(pipeline)
        clip.write_videofile(output, audio=False)
        end = time.time()

        print(round(end - start, 2), 'Seconds to finish')
# 파이프라이닝 작업해야됨
# 노이즈 트랙킹 제거
# z 좌표 확실하게
# KPI 산출
# 자체모델 학습 / 공용 모델 단점
