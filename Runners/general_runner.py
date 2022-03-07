import os


def make_save_folders(args, name):
    root = args['output_base_path'] + args['run_name']
    folder_list = [args['image_path'], args['detected_path'], args['tracking_path']]
    for folder in folder_list:
        if os.path.exists(root + folder):
            os.mkdir(root + folder + name)


class AbstractRunner:

    def get_image(self):
        raise NotImplementedError

    def detect(self, tensor_image):
        raise NotImplementedError

    def tracking(self, results):
        raise NotImplementedError

    def post_tracking(self, deleted_trackers, whole_image):
        raise NotImplementedError

    def post_processing(self, path, whole_image):
        raise NotImplementedError
