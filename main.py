#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""@author: MnS Team
"""
import os
import datetime

import numpy as np
from collections import deque
from scipy.optimize import linear_sum_assignment

import helpers
import tracker
import pickle

from utilities.media_handler import PipeliningVideoManager, ImageManager
from Detectors import REGISTRY as det_REGISTRY
import utilities.config_mapper as config_mapper


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
    primary_detector = det_REGISTRY[primary_model_args['model_name']](**primary_model_args)
    recovery_detector = det_REGISTRY[recovery_model_args['model_name']](**recovery_model_args)
    tracker_list = []  # list for trackers
    track_id_list = deque(range(255))  # list for track ID
    plan_image = ImageManager.load_cv(args['plan_path'])
    x_box = []

    (name, extension) = args['video_name'].split('.')

    with open(args['projection_path'] + name + '.pickle', 'rb') as matrix:
        transform_matrix = pickle.load(matrix)

    # 1. Video loaded
    video_handle = PipeliningVideoManager()
    plan_handle = PipeliningVideoManager()
    image_handle = ImageManager()
    frame_rate, image_size = video_handle.load_video(args['video_path'] + args['video_name'])
    # 1-1. Making Output video object
    video_handle.activate_video_object(config['output_base_path'] + config['run_name'] +
                                       args['tracking_path'] + args['video_name'])
    plan_handle.activate_video_object(config['output_base_path'] + config['run_name'] +
                                      args['trajectory_path'] + args['video_name'],
                                      v_info=(frame_rate, image_size[0], image_size[1]))

    while True:
        _, np_image = video_handle.pop()
        if np_image is None:
            break

        if args['save']:
            ImageManager.save_image(np_image, config['output_base_path'] + config['run_name'] +
                                    args['image_path'] + video_handle.make_image_name())

        # 2. To detection
        # np_image # cv2
        # tensor_image # RGB 배열을 바꾼 tensor로 변환해야됨
        tensor_image = ImageManager.convert_tensor(np_image)
        test = tensor_image.shape
        raw_image, boxes, classes, scores = primary_detector.detection(tensor_image)
        z_box = primary_detector.get_zboxes(boxes, image_size[0], image_size[1])

        if args['save']:
            temp_img = raw_image.numpy()
            detected_img = image_handle.draw_boxes(temp_img[0], z_box, classes, scores)
            ImageManager.save_tensor(detected_img, args['output_base_path'] + config['run_name'] +
                                     args['detected_path'] + video_handle.make_image_name())

        # 3. To Tracker
        x_box.clear()
        if len(tracker_list) > 0:
            for trk in tracker_list:
                x_box.append(trk.box)

        matched, unmatched_dets, unmatched_trks \
            = assign_detections_to_trackers(x_box, z_box, iou_thrd=0.3)
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
        deleted_tracks = filter(lambda x: x.no_losses > args['max_age'], tracker_list)

        for trk in deleted_tracks:
            # SSD Network 에도 잡히지 않는지 확인
            recovery_image, boxes, classes, scores = recovery_detector.detection(tensor_image)
            post_box = recovery_detector.get_zboxes(boxes, image_size[0], image_size[1])
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
        for trk in tracker_list:
            if (trk.hits >= args['min_hits']) and (trk.no_losses <= args['max_age']):
                good_tracker_list.append(trk)
                x_cv2 = trk.box
                if args['debug']:
                    print('updated box: ', x_cv2)
                    print()

                np_image = helpers.draw_box_label(np_image,
                                                  x_cv2,
                                                  image_handle.Colors[trk.id % len(image_handle.Colors)])
                plan_image = helpers.transform(x_cv2, np_image,
                                               plan_image, transform_matrix,
                                               image_handle.Colors[trk.id % len(image_handle.Colors)])
                tracker_list = [x for x in tracker_list if x.no_losses <= args['max_age']]

        if args['debug']:
            print('Ending tracker_list: ', len(tracker_list))
            print('Ending good tracker_list: ', len(good_tracker_list))

        if args['save']:
            ImageManager.save_image(np_image,
                                    args['output_base_path'] + config['run_name'] +
                                    args['tracking_path'] + video_handle.make_image_name())
            ImageManager.save_image(plan_image,
                                    args['output_base_path'] + config['run_name'] +
                                    args['trajectory_path'] + video_handle.make_image_name())
        video_handle.append(np_image)
        plan_handle.append(plan_image)
    # ---- 쓰레드 안써도 될듯 ---
    # 2. Threading 활성화
    # 2-1. 비디오에서 이미지 만드는 쓰레드
    # 2-2. 이미지 불러와서 디텍션 + 트랙킹하는 쓰레드
    # 2-3. 처리하는대로 바로 파이프라인 비디오 매니저에 append
    # 3. 종료시 쓰레드 클리어, 비디오 생성
    video_handle.release_video_object()
    plan_handle.release_video_object()


if __name__ == "__main__":
    detectors = ['efficient', 'ssd_mobile', 'centernet']
    config = config_mapper.config_copy(config_mapper.get_config(detection_names=detectors))
    config['run_name'] = datetime.datetime.now().strftime('%m-%d %H%M%S')
    config['run_name'] = config['run_name'] + '/'
    config['video_name'] = "LOADING DOCK F3 Rampa 11-12.avi"

    primary_model_args = config[config['primary_model_name']]
    recovery_model_args = config[config['recovery_model_name']]

    # 빠른 처리에는 존재할 수가 있음
    clear_folder([config['detected_path'], config['tracking_path'], config['trajectory_path'], config['image_path']],
                 config['output_base_path'] + config['run_name'])

    pipelining(args=config)
