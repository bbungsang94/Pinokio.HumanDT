class AbstractDetector(object):

    def detection(self, image):
        """Determines the locations of the vehicle in the image

                Args:
                    image: image path
                Returns:
                    list of bounding boxes: coordinates [y_up, x_left, y_down, x_right]

                """
        raise NotImplementedError

    def get_zboxes(self, boxes, im_width, im_height):
        raise NotImplementedError