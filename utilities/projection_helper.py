import cv2


class ProjectionManager:
    instance = None
    video_list = dict()
    whole_image_size = tuple

    def __new__(cls, video_list, whole_image_size):
        cls.video_list = video_list
        cls.whole_image_size = whole_image_size
        if not hasattr(cls, 'instance'):
            cls.instance = super(ProjectionManager, cls).__new__(cls)
            return cls.instance

    @classmethod
    def transform(cls, bbox_cv2, img, plan_img, matrices, box_color=(0, 255, 255)):
        if isinstance(box_color, tuple) is False:
            box_color = hex_to_rgb(box_color)
        left, top, right, bottom = bbox_cv2[1], bbox_cv2[0], bbox_cv2[3], bbox_cv2[2]
        xPt = (left + right) / 2
        # yPt = (top + bottom) / 2

        # 하단 가운데
        yPt = bottom

        img_height = img.shape[0]
        yPt = img_height - yPt

        xPt, yPt, video_name = cls.get_video_name(xPt, yPt)

        matrix = get_matrix(xPt, yPt, video_name, matrices)

        plan_img_height = plan_img.shape[0]
        w = (xPt * matrix[2][0]) + (yPt * matrix[2][1]) + matrix[2][2]
        x = ((xPt * matrix[0][0]) + (yPt * matrix[0][1]) + matrix[0][2]) / w
        y = ((xPt * matrix[1][0]) + (yPt * matrix[1][1]) + matrix[1][2]) / w

        plan_image = cv2.circle(plan_img, (int(x), int(plan_img_height - y)), 2, box_color, thickness=-1)
        return plan_image

    @classmethod
    def get_video_name(cls, xPt, yPt):
        max_Y_count = len(cls.video_list)
        max_X_count = len(cls.video_list[0])

        (whole_width, whole_height) = cls.whole_image_size

        rel_x = float(xPt / whole_width)
        rel_y = float(yPt / whole_height)
        x_level = 1 / max_X_count
        y_level = 1 / max_Y_count

        x_value = int(rel_x / x_level)
        y_value = int(rel_y / y_level)

        new_xPt = xPt - 1280 * x_value
        new_yPt = yPt - 800 * y_value

        x_index = x_value
        y_index = max_Y_count - 1 - y_value
        (name, extension) = cls.video_list[y_index][x_index].split('.')
        return new_xPt, new_yPt, name


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def get_matrix(xPt, yPt, video_name: str, matrix_list):
    matrices = matrix_list[video_name]
    if video_name == "LOADING DOCK F3 Rampa 13 - 14":
        xPt -= 1280 * 0  # First Video
        if ((-8 / 3 * xPt + 1600) >= yPt) and ((-25 / 39 * xPt + 1120) > yPt):
            matrix = matrices[0]
        elif ((-8 / 3 * xPt + 1600) < yPt) and ((-25 / 39 * xPt + 1120) >= yPt):
            matrix = matrices[1]
        elif ((-8 / 3 * xPt + 1600) < yPt) and ((-25 / 39 * xPt + 1120) < yPt):
            matrix = matrices[2]
        return matrix
    elif video_name == "LOADING DOCK F3 Rampa 11-12":
        xPt -= 1280 * 1 # Second Video
        if ((-8 * xPt + 4800) >= yPt) and ((-35 / 29 * xPt + 1645) > yPt):
            matrix = matrices[0]
        elif ((-8 * xPt + 4800) < yPt) and ((-35 / 29 * xPt + 1645) >= yPt):
            matrix = matrices[1]
        elif ((-8 * xPt + 4800) < yPt) and ((-35 / 29 * xPt + 1645) < yPt):
            matrix = matrices[2]
        return matrix
    elif video_name == "LOADING DOCK F3 Rampa 9-10":
        xPt -= 1280 * 2  # Third Video
        if ((2 * xPt - 100) <= yPt) and ((-80 / 9 * xPt + 6667) > yPt):
            matrix = matrices[0]
        elif ((2 * xPt - 100) > yPt) and ((-80 / 9 * xPt + 6667) >= yPt):
            matrix = matrices[1]
        elif ((2 * xPt - 100) > yPt) and ((-80 / 9 * xPt + 6667) < yPt):
            matrix = matrices[2]
        return matrix
