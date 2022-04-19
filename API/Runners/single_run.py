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
        for trk in trackers.get_single_trackers():
            np_image = draw_box_label(np_image, trk.box,
                                      image_handle.Colors[trk.id % len(image_handle.Colors)])
            plan_image = transform(trk.box, np_image, plan_image, matrices, name,
                                   image_handle.Colors[trk.id % len(image_handle.Colors)])

        if args['debug']:
            print('Ending tracker_list: ', len(trackers.get_single_trackers()))

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