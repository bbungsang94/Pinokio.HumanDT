#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""@author: MnS Team
"""
import os
import datetime
import time
import utilities.config_mapper as config_mapper
<<<<<<< HEAD
from Runners import run
=======
from utilities.helpers import post_iou_checker, draw_box_label, transform
from utilities.projection_helper import ProjectionManager

>>>>>>> a4ea42d767d4680fe4dc28d8dfb31f705d889e1b

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


<<<<<<< HEAD
=======
class DictToStruct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def pipeliningSingle(args):
    # 0. Init
    tracker_model_args = args[args['tracker_model_name']]
    primary_model_args = args[args['primary_model_name']]
    recovery_model_args = args[args['recovery_model_name']]

    plan_image = ImageManager.load_cv(args['plan_path'])

    (name, extension) = args['video_name'].split('.')
    matrices = []
    for idx in range(args['num_of_projection']):
        with open(args['projection_path'] + name + '-' + str(idx + 1) + '.pickle', 'rb') as matrix:
            matrices.append(pickle.load(matrix))

    # 1. Video loaded
    video_handle = PipeliningVideoManager()
    plan_handle = PipeliningVideoManager()
    image_handle = ImageManager()
    frame_rate, image_size = video_handle.load_video(args['video_path'] + args['video_name'])
    # 1-1. Making Output video object
    video_handle.activate_video_object(args['output_base_path'] + args['run_name'] +
                                       args['tracking_path'] + args['video_name'])
    plan_handle.activate_video_object(args['output_base_path'] + args['run_name'] +
                                      args['trajectory_path'] + args['video_name'],
                                      v_info=(frame_rate, image_size[0], image_size[1]))

    # 2. Model loaded
    tracker_model_args['image_size'] = image_size
    trackers = trk_REGISTRY[tracker_model_args['model_name']](**tracker_model_args)
    primary_detector = det_REGISTRY[primary_model_args['model_name']](**primary_model_args)
    recovery_detector = det_REGISTRY[recovery_model_args['model_name']](**recovery_model_args)

    while True:
        _, np_image = video_handle.pop()
        if np_image is None:
            break
        TimeDict['Whole_Frame'] += 1

        if args['save']:
            begin_time = time.time()
            ImageManager.save_image(np_image, args['output_base_path'] + args['run_name'] +
                                    args['image_path'] + video_handle.make_image_name())
            TimeDict['Save_Time'] += time.time() - begin_time

        # 2. To detection
        # np_image # cv2
        # tensor_image # RGB 배열을 바꾼 tensor로 변환해야됨
        tensor_image = ImageManager.convert_tensor(np_image)

        begin_time = time.time()
        raw_image, boxes, classes, scores = primary_detector.detection(tensor_image)
        TimeDict['Inference_Time'] += time.time() - begin_time

        z_box = primary_detector.get_zboxes(boxes, image_size[0], image_size[1])

        if args['save']:
            begin_time = time.time()
            temp_img = raw_image.numpy()
            detected_img = image_handle.draw_boxes(temp_img[0], z_box, classes, scores)
            ImageManager.save_tensor(detected_img, args['output_base_path'] + args['run_name'] +
                                     args['detected_path'] + video_handle.make_image_name())
            TimeDict['Save_Time'] += time.time() - begin_time

        # 3. To Tracker
        begin_time = time.time()
        trackers.assign_detections_to_trackers(detections=z_box)
        deleted_tracks = trackers.update_trackers()
        TimeDict['Tracking_Time'] += time.time() - begin_time

        for trk in deleted_tracks:
            # SSD Network 에도 잡히지 않는지 확인
            begin_time = time.time()
            recovery_image, boxes, classes, scores = recovery_detector.detection(tensor_image)
            TimeDict['Recovery_Time'] += time.time() - begin_time

            post_box = recovery_detector.get_zboxes(boxes, image_size[0], image_size[1])
            post_pass, box = post_iou_checker(trk.box, post_box, thr=0.2, offset=0.3)
            if post_pass:
                TimeDict['Recovery_Count'] += 1
                trackers.revive_tracker(revive_trk=trk, new_box=box)
            else:
                trackers.delete_tracker(delete_id=trk.id)

        # The list of tracks to be annotated
        for trk in trackers.get_trackers():
            np_image = draw_box_label(np_image, trk.box,
                                      image_handle.Colors[trk.id % len(image_handle.Colors)])
            plan_image = ProjectionManager.transform(trk.box, np_image, plan_image, matrices,
                                                     image_handle.Colors[trk.id % len(image_handle.Colors)])

            # plan_image = transform(trk.box, np_image, plan_image, matrices, name,
            #                        image_handle.Colors[trk.id % len(image_handle.Colors)])

        if args['debug']:
            print('Ending tracker_list: ', len(trackers.get_trackers()))

        if args['save']:
            begin_time = time.time()
            ImageManager.save_image(np_image,
                                    args['output_base_path'] + args['run_name'] +
                                    args['tracking_path'] + video_handle.make_image_name())
            ImageManager.save_image(plan_image,
                                    args['output_base_path'] + args['run_name'] +
                                    args['trajectory_path'] + video_handle.make_image_name())
            TimeDict['Save_Time'] += time.time() - begin_time
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


class InferenceParallel(threading.Thread):
    def __init__(self, info: dict, name: str):
        super().__init__()
        self.model = info[name]

    def run(self):
        model = self.model
        _, np_image = model['video_handle'].pop()
        if np_image is None:
            model['results'] = (None, None, None, None)
            return
        model['image'] = np_image
        tensor_image = ImageManager.convert_tensor(np_image)

        raw_image, boxes, classes, scores = model['detector'].detection(tensor_image)
        boxes = model['detector'].get_zboxes(boxes, model['image_size'][0], model['image_size'][1])
        model['results'] = (raw_image, boxes, classes, scores)


class SaveImgParallel(threading.Thread):
    def __init__(self, info: dict, name: str):
        super().__init__()
        self.model = info[name]
        self.__init_t = False

    def run(self):
        if self.__init_t is False:
            self.__init_t = True
            return

        (test_img, detected_img, tracking_img) = self.model['images']
        # Test
        ImageManager.save_image(test_img,
                                self.model['test_path'] + self.model['model']['video_handle'].make_image_name())
        # Detection
        ImageManager.save_tensor(detected_img,
                                 self.model['detected_path'] + self.model['model']['video_handle'].make_image_name())
        # Tracking
        ImageManager.save_image(tracking_img,
                                self.model['tracking_path'] + self.model['model']['video_handle'].make_image_name())


def pipeliningParallel(args):
    # 0. Init
    tracker_model_args = args[args['tracker_model_name']]
    primary_model_args = args[args['primary_model_name']]
    recovery_model_args = args[args['recovery_model_name']]

    video_handles = []
    frame_rate = 0
    image_size = (0, 0)
    matrices = dict()
    for video_name in args['parallel_list']:
        (name, extension) = video_name.split('.')

        clear_folder([args['trajectory_path']], args['output_base_path'] + args['run_name'])

        clear_folder(
            [args['detected_path'], args['tracking_path'], args['image_path']],
            args['output_base_path'] + args['run_name'] + name + '/')
        matrices[name] = []
        for idx in range(args['num_of_projection']):
            with open(args['projection_path'] + name + '-' + str(idx + 1) + '.pickle', 'rb') as matrix:
                matrices[name].append(pickle.load(matrix))
        # 1. Video loaded
        video_handle = PipeliningVideoManager()
        frame_rate, image_size = video_handle.load_video(args['video_path'] + video_name)
        video_handle.activate_video_object(args['output_base_path'] + args['run_name'] + name + '/' +
                                           args['tracking_path'] + video_name)
        video_handles.append(video_handle)

    plan_image = ImageManager.load_cv(args['plan_path'])
    plan_handle = PipeliningVideoManager()
    image_handle = ImageManager()
    plan_handle.activate_video_object(args['output_base_path'] + args['run_name'] +
                                      args['trajectory_path'] + 'Total_Trajectory.avi',
                                      v_info=(frame_rate, image_size[0], image_size[1]))

    # 2. Model loaded
    tracker_model_args['image_size'] = image_size
    trackers = trk_REGISTRY[tracker_model_args['model_name']](**tracker_model_args)
    running_threads = []
    save_threads = []
    primary_models = dict()
    save_models = dict()
    for video_name in args['parallel_list']:
        (name, extension) = video_name.split('.')
        output_path = args['output_base_path'] + args['run_name'] + name + '/'
        primary_models[name] = {'detector': det_REGISTRY[primary_model_args['model_name']](**primary_model_args),
                                'video_handle': video_handles.pop(0),
                                'image_size': image_size,
                                'image': None,
                                'output_path': output_path,
                                'results': tuple()}

        save_models[name] = {'test_path': output_path + args['image_path'],
                             'detected_path': output_path + args['detected_path'],
                             'tracking_path': output_path + args['tracking_path'],
                             'images': (),
                             'model': primary_models[name]}

        run_t = InferenceParallel(info=primary_models, name=name)
        run_t.start()
        running_threads.append(run_t)
        run_t.join()
        save_t = SaveImgParallel(info=save_models, name=name)
        save_t.start()
        save_threads.append(save_t)
        save_t.join()

    recovery_detector = det_REGISTRY[recovery_model_args['model_name']](**recovery_model_args)

    while True:
        begin_time = time.time()
        for t in running_threads:
            t.run()
        for t in running_threads:
            t.join()

        local_count = 0
        deleted_models = []
        for name, model_info in primary_models.items():
            model_info = running_threads[local_count].model
            save_models[name]['model'] = model_info
            local_count += 1
            (raw_image, boxes, classes, scores) = model_info['results']
            if raw_image is None:
                model_info["video_handle"].release_video_object()
                deleted_models.append(name)

        for deleted_model in deleted_models:
            del primary_models[deleted_model]

        if len(primary_models) == 0:
            plan_handle.release_video_object()
            return

        TimeDict['Whole_Frame'] += 1
        TimeDict['Inference_Time'] += time.time() - begin_time

        # To Tracker
        begin_time = time.time()
        local_count = 0
        for name, model_info in primary_models.items():
            (raw_image, boxes, classes, scores) = model_info['results']
            np_image = model_info['image']
            trackers.assign_detections_to_trackers(detections=boxes)
            deleted_tracks = trackers.update_trackers()
            TimeDict['Tracking_Time'] += time.time() - begin_time

            tensor_image = ImageManager.convert_tensor(np_image)
            for trk in deleted_tracks:
                # SSD Network 에도 잡히지 않는지 확인
                begin_time = time.time()
                recovery_image, boxes, classes, scores = recovery_detector.detection(tensor_image)
                TimeDict['Recovery_Time'] += time.time() - begin_time

                post_box = recovery_detector.get_zboxes(boxes, image_size[0], image_size[1])
                post_pass, box = post_iou_checker(trk.box, post_box, thr=0.2, offset=0.3)
                if post_pass:
                    TimeDict['Recovery_Count'] += 1
                    trackers.revive_tracker(revive_trk=trk, new_box=box)
                else:
                    trackers.delete_tracker(delete_id=trk.id)

            # The list of tracks to be annotated
            for trk in trackers.get_trackers():
                np_image = draw_box_label(np_image, trk.box,
                                          image_handle.Colors[trk.id % len(image_handle.Colors)])
                plan_image = transform(trk.box, np_image, plan_image, matrices[name], name,
                                       image_handle.Colors[trk.id % len(image_handle.Colors)])

            if args['debug']:
                print('Ending tracker_list: ', len(trackers.get_trackers()))
            if args['save']:
                saver = save_models[name]
                temp_img = raw_image.numpy()
                detected_img = image_handle.draw_boxes(model_info['image'], boxes, classes, scores)
                saver['images'] = (temp_img[0], detected_img, np_image)
                save_threads[local_count].model[name] = saver
                local_count += 1

            model_info['video_handle'].append(np_image)
            plan_handle.append(plan_image)
        if args['save']:
            begin_time = time.time()
            for save_thread in save_threads:
                save_thread.run()
            for key in primary_models.keys():
                ImageManager.save_image(plan_image,
                                        args['output_base_path'] + args['run_name'] +
                                        args['trajectory_path'] +
                                        primary_models[key]['video_handle'].make_image_name())
                break
            for save_thread in save_threads:
                save_thread.join()
            TimeDict['Save_Time'] += time.time() - begin_time


>>>>>>> a4ea42d767d4680fe4dc28d8dfb31f705d889e1b
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
<<<<<<< HEAD
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
=======
    if config['parallel_mode']:
        config['parallel_list'] = ["LOADING DOCK F3 Rampa 13 - 14.avi",
                                   "LOADING DOCK F3 Rampa 11-12.avi",
                                   "LOADING DOCK F3 Rampa 9-10.avi"]
    else:
        config['video_name'] = "LOADING DOCK F3 Rampa 13 - 14.avi"
        clear_folder(
            [config['detected_path'], config['tracking_path'], config['trajectory_path'], config['image_path']],
            config['output_base_path'] + config['run_name'])

    # 빠른 처리에는 존재할 수가 있음
    ProjectionManager(video_list={0: ['test', 'test2'], 1: ['test3', 'test4']}, whole_image_size=(1600, 2560))

    pipeliningSingle(args=config)
    # pipeliningParallel(args=config)
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
>>>>>>> a4ea42d767d4680fe4dc28d8dfb31f705d889e1b
