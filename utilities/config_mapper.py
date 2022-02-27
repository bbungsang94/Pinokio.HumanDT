import collections
from copy import deepcopy
import yaml


def config_copy(config):
    if isinstance(config, dict):
        return {k: config_copy(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [config_copy(v) for v in config]
    else:
        return deepcopy(config)


def recursive_dict_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            d[k] = recursive_dict_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def get_config():
    config_dir = '{0}/{1}'
    config_dir2 = '{0}/{1}/{2}'
    config_dir3 = '{0}/{1}/{2}/{3}'

    with open(config_dir.format('config', "{}.yaml".format('default')), "r") as f:
        try:
            config = yaml.load(f, Loader=yaml.FullLoader)
        except yaml.YAMLError as exc:
            assert False, "default.yaml error: {}".format(exc)
    detection_names = [config['primary_model_name'], config['recovery_model_name']]
    for model_name in detection_names:
        with open(config_dir3.format('config', 'model', 'detection', "{}.yaml".format(model_name)), "r") as f:
            try:
                model_dict = yaml.load(f, Loader=yaml.FullLoader)
            except yaml.YAMLError as exc:
                assert False, "model.yaml error: {}".format(exc)
            config = recursive_dict_update(config, model_dict)
    tracker_names = [config['tracker_model_name']]
    for model_name in tracker_names:
        with open(config_dir3.format('config', 'model', 'tracking', "{}.yaml".format(model_name)), "r") as f:
            try:
                model_dict = yaml.load(f, Loader=yaml.FullLoader)
            except yaml.YAMLError as exc:
                assert False, "model.yaml error: {}".format(exc)
            config = recursive_dict_update(config, model_dict)

    return config
