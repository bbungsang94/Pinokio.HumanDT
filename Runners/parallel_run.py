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
    running_pool = Pool(processes=len(args['parallel_list']))
    save_pool = Pool(processes=len(args['parallel_list']))
    primary_models = []
    save_models = []
    for video_name in args['parallel_list']:
        (name, extension) = video_name.split('.')
        output_path = args['output_base_path'] + args['run_name'] + name + '/'
        primary_model = {'detector': det_REGISTRY[primary_model_args['model_name']](**primary_model_args),
                         'video_handle': video_handles.pop(0),
                         'image_size': image_size,
                         'video_name': name,
                         'image': None,
                         'output_path': output_path,
                         'results': tuple()}
        primary_models.append(primary_model)

        save_model = {'test_path': output_path + args['image_path'],
                      'detected_path': output_path + args['detected_path'],
                      'tracking_path': output_path + args['tracking_path'],
                      'images': (),
                      'model': primary_model}
        save_models.append(save_model)

    recovery_detector = det_REGISTRY[recovery_model_args['model_name']](**recovery_model_args)

    while True:
        begin_time = time.time()
        next_models = running_pool.map(func=inference, iterable=primary_models)
        print(time.time() - begin_time)
        deleted_models = []
        for idx, model in enumerate(primary_models):
            model = next_models[idx]
            save_models[idx]['model'] = model
            (raw_image, boxes, classes, scores) = model['results']
            if raw_image is None:
                model["video_handle"].release_video_object()
                deleted_models.append(idx)
        for delete_idx in deleted_models:
            del primary_models[delete_idx]

        if len(primary_models) == 0:
            plan_handle.release_video_object()
            return

        TimeDict['Whole_Frame'] += 1
        TimeDict['Inference_Time'] += time.time() - begin_time

        # To Tracker
        begin_time = time.time()
        for idx, model in enumerate(primary_models):
            (raw_image, boxes, classes, scores) = model['results']
            np_image = model['image']
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
                plan_image = transform(trk.box, np_image, plan_image, matrices[model['video_name']],
                                       model['video_name'], image_handle.Colors[trk.id % len(image_handle.Colors)])

            if args['debug']:
                print('Ending tracker_list: ', len(trackers.get_trackers()))
            if args['save']:
                saver = save_models[idx]
                temp_img = raw_image.numpy()
                detected_img = image_handle.draw_boxes(model['image'], boxes, classes, scores)
                saver['images'] = (temp_img[0], detected_img, np_image)

            model['video_handle'].append(np_image)
            plan_handle.append(plan_image)
        if args['save']:
            begin_time = time.time()
            save_pool.map(func=save_images, iterable=save_models)
            ImageManager.save_image(plan_image,
                                    args['output_base_path'] + args['run_name'] +
                                    args['trajectory_path'] +
                                    primary_models[0]['video_handle'].make_image_name())
            TimeDict['Save_Time'] += time.time() - begin_time