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
    count = 0
    while True:
        image = runner.get_image()
        if image is None:
            return
        if count < 153:
            count += 1
            continue
        detect_result, box_anchors = runner.detect(tensor_image=image)
        delete_candidates = runner.tracking(detect_result)
        deleted_tracker_ids = runner.post_tracking(deleted_trackers=delete_candidates, whole_image=image)
        runner.clean_trackers(deleted_tracker_ids)
        runner.post_processing(paths)
        runner.interaction_processing(box_anchors, deleted_tracker_ids)


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
