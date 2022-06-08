import time

from Runners import REGISTRY as r_REGISTRY
from Runners import MergeRunner
from Runners.cacasde_run import CascadeRunner
from utilities.projection_helper import ProjectionManager


def standard_run(config, log=None):
    # check args sanity
    # _config = args_sanity_check(_config, _log)

    # setup loggers
    if log is not None:
        raise NotImplementedError
        # logger = Logger(log)

    # Run and train
    run_sequential(args=config, log=None)


def run_sequential(args, log=None):
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
    count = 0
    while True:
        count += 1
        image = runner.get_image()
        if image is None:
            runner.interaction_clear()
            return
        # if count < 2240 + 940:
        #     continue
        ProjectionManager.ColorChecker.new_folder(str(count))
        begin = time.time()
        detect_result, box_anchors = runner.detect(tensor_image=image)
        print("Detect time: ", (time.time() - begin) * 1000, "ms")
        begin = time.time()
        loss_trks = runner.tracking(detect_result, image)
        print("Tracking time: ", (time.time() - begin) * 1000, "ms")
        begin = time.time()
        state_trackers = runner.interaction_processing(box_anchors, loss_trks)
        print("Interaction time: ", (time.time() - begin) * 1000, "ms")
        begin = time.time()
        runner.post_processing(path=paths, state_trackers=state_trackers)
        print("Post processing time: ", (time.time() - begin) * 1000, "ms")


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
