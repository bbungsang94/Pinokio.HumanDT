import time

from Runners import REGISTRY as r_REGISTRY
from Runners import MergeRunner
from Runners.cacasde_run import CascadeRunner


def standard_run(config, log=None):
    # check args sanity
    # _config = args_sanity_check(_config, _log)

    args = config

    # setup loggers
    if log is not None:
        raise NotImplementedError
        # logger = Logger(log)

    # Run and train
    run_sequential(args=args, log=None)


def run_sequential(args, log=None):
    #runner = r_REGISTRY[args['run_mode']](args=args)
    #runner = MergeRunner(args=args)
    runner = CascadeRunner(args=args)
    base_root = args['output_base_path'] + args['run_name']
    paths = {'test_path': base_root + args['image_path'],
             'detected_path': base_root + args['detected_path'],
             'tracking_path': base_root + args['tracking_path'],
             'plan_path': base_root + args['trajectory_path']}

    time_dict = {'Whole_Time': 0, 'Whole_Frame': 0,
                 'Inference_Time': 0, 'Inference_Mean': 0,
                 'Recovery_Time': 0, 'Recovery_Count': 0, 'Recovery_Mean': 0,
                 'Tracking_Time': 0, 'Tracking_Mean': 0, 'Max_Tracker': 0,
                 'Save_Time': 0, 'Save_Mean': 0}

    while True:
        image = runner.get_image()
        if image is None:
            return
        begin = time.time()
        detect_result, box_anchors = runner.detect(tensor_image=image)
        print("Detect time: ", time.time() - begin)
        begin = time.time()
        delete_candidates = runner.tracking(detect_result)
        print("Tracking time: ", time.time() - begin)
        begin = time.time()
        deleted_tracker_ids = runner.post_tracking(deleted_trackers=delete_candidates, whole_image=image)
        print("Post Tracking time: ", time.time() - begin)
        begin = time.time()
        runner.clean_trackers(deleted_tracker_ids)
        print("Clean tracker time: ", time.time() - begin)
        begin = time.time()
        runner.post_processing(paths)
        print("Post processing time: ", time.time() - begin)
        begin = time.time()
        runner.interaction_processing(box_anchors, deleted_tracker_ids)
        print("Interaction time: ", time.time() - begin)


def args_sanity_check(config, _log):
    # set CUDA flags
    # config["use_cuda"] = True # Use cuda whenever possible!
    if config["use_cuda"] and not th.cuda.is_available():
        config["use_cuda"] = False
        _log.warning("CUDA flag use_cuda was switched OFF automatically because no CUDA devices are available!")

    if config["test_nepisode"] < config["batch_size_run"]:
        config["test_nepisode"] = config["batch_size_run"]
    else:
        config["test_nepisode"] = (config["test_nepisode"] // config["batch_size_run"]) * config["batch_size_run"]

    return config
