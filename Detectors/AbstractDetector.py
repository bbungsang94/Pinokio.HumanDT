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
