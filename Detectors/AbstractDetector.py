class AbstractDetector(object):

    def detection(self, path, display=False, save=False):
        """Determines the locations of the vehicle in the image

                Args:
                    path: image path
                    display: show figure option
                    save: on display, furthermore you want to save image
                Returns:
                    list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

                """
        raise NotImplementedError

    def draw_bounding_box_on_image(self, image,
                                   ymin, xmin, ymax, xmax,
                                   color, thickness=4, display_str_list=()):
        """Adds a bounding box to an image."""
        raise NotImplementedError


