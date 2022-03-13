import cv2


class ProjectionManager:
    instance = None
    video_list = dict()
    whole_image_size = tuple
    single_image_size = tuple
    matrices = dict()

    def __new__(cls, video_list, whole_image_size, single_image_size, matrices):
        cls.video_list = video_list
        cls.whole_image_size = whole_image_size
        cls.single_image_size = single_image_size
        cls.matrices = matrices
        if not hasattr(cls, 'instance'):
            cls.instance = super(ProjectionManager, cls).__new__(cls)
            return cls.instance

    @classmethod
    def transform(cls, bbox_cv2, video_idx):
        left, top, right, bottom = bbox_cv2[1], bbox_cv2[0], bbox_cv2[3], bbox_cv2[2]
        xPt = (left + right) / 2
        # yPt = (top + bottom) / 2

        # 하단 가운데
        yPt = bottom

        img_height = cls.single_image_size[1]
        yPt = img_height - yPt

        matrix = get_matrix(xPt, yPt, video_idx, cls.matrices)

        w = (xPt * matrix[2][0]) + (yPt * matrix[2][1]) + matrix[2][2]
        x = ((xPt * matrix[0][0]) + (yPt * matrix[0][1]) + matrix[0][2]) / w
        y = ((xPt * matrix[1][0]) + (yPt * matrix[1][1]) + matrix[1][2]) / w

        return x, y


    @classmethod
    def transform_in_merge(cls, bbox_cv2, img):
        left, top, right, bottom = bbox_cv2[1], bbox_cv2[0], bbox_cv2[3], bbox_cv2[2]
        xPt = (left + right) / 2
        # yPt = (top + bottom) / 2

        # 하단 가운데
        yPt = bottom

        img_height = img.shape[0]
        yPt = img_height - yPt

        xPt, yPt, video_name = cls.get_video_name_in_merge(xPt, yPt)

        matrix = get_matrix_in_merge(xPt, yPt, video_name, cls.matrices)

        w = (xPt * matrix[2][0]) + (yPt * matrix[2][1]) + matrix[2][2]
        x = ((xPt * matrix[0][0]) + (yPt * matrix[0][1]) + matrix[0][2]) / w
        y = ((xPt * matrix[1][0]) + (yPt * matrix[1][1]) + matrix[1][2]) / w

        return x, y

    @classmethod
    def draw_plan_image(cls, x, y, plan_img, box_color=(0, 255, 255)):
        if isinstance(box_color, tuple) is False:
            box_color = hex_to_rgb(box_color)
        plan_img_height = plan_img.shape[0]

        plan_image = cv2.circle(plan_img, (int(x), int(plan_img_height - y)), 2, box_color, thickness=-1)
        return plan_image

    @classmethod
    def get_video_name_in_merge(cls, xPt, yPt):
        max_Y_count = len(cls.video_list)
        max_X_count = len(cls.video_list[0])

        (whole_width, whole_height) = cls.whole_image_size
        (single_width, single_height) = cls.single_image_size
        rel_x = float(xPt / whole_width)
        rel_y = float(yPt / whole_height)
        x_level = 1 / max_X_count
        y_level = 1 / max_Y_count

        x_value = int(rel_x / x_level)
        y_value = int(rel_y / y_level)

        new_xPt = xPt - single_width * x_value
        new_yPt = yPt - single_height * y_value

        x_index = x_value
        y_index = max_Y_count - 1 - y_value
        (name, extension) = cls.video_list[y_index][x_index].split('.')
        return new_xPt, new_yPt, name


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def get_matrix(xPt, yPt, video_idx: int, matrix_list):
    matrices = matrix_list[video_idx]
    if video_idx == 0: # Shorts Test
        if ((47 / 462 * xPt + 130) <= yPt) and ((127 / 674 * xPt) < yPt):
            matrix = matrices[0]
        elif ((47 / 462 * xPt + 130) > yPt) and ((127 / 674 * xPt) <= yPt):
            matrix = matrices[1]
        elif ((47 / 462 * xPt + 130) > yPt) and ((127 / 674 * xPt) > yPt):
            matrix = matrices[2]
        return matrix
    # if video_idx == 0:
    #     if ((-988 / 400 * xPt + 1852.5) >= yPt) and ((-123 / 157 * xPt + 1497) > yPt):
    #         matrix = matrices[0]
    #     elif ((-988 / 400 * xPt + 1852.5) < yPt) and ((-123 / 157 * xPt + 1497) >= yPt):
    #         matrix = matrices[1]
    #     elif ((-988 / 400 * xPt + 1852.5) < yPt) and ((-123 / 157 * xPt + 1497) < yPt):
    #         matrix = matrices[2]
    #     return matrix
    elif video_idx == 1:
        if ((-24.7 * xPt + 16450) >= yPt) and ((-222 / 163 * xPt + 2268) > yPt):
            matrix = matrices[0]
        elif ((-24.7 * xPt + 16450) < yPt) and ((-222 / 163 * xPt + 2268) >= yPt):
            matrix = matrices[1]
        elif ((-24.7 * xPt + 16450) < yPt) and ((-222 / 163 * xPt + 2268) < yPt):
            matrix = matrices[2]
        return matrix
    elif video_idx == 2:
        if ((247 / 105 * xPt - 188) <= yPt) and ((-988 / 85 * xPt + 10461) > yPt):
            matrix = matrices[0]
        elif ((247 / 105 * xPt - 188) > yPt) and ((-988 / 85 * xPt + 10461) >= yPt):
            matrix = matrices[1]
        elif ((247 / 105 * xPt - 188) > yPt) and ((-988 / 85 * xPt + 10461) < yPt):
            matrix = matrices[2]
        return matrix


def get_matrix_in_merge(xPt, yPt, video_name: str, matrix_list):
    matrices = matrix_list[video_name]
    if video_name == "LOADING DOCK F3 Rampa 13 - 14":
        xPt -= 1592 * 0  # First Video
        if ((-988 / 400 * xPt + 1852.5) >= yPt) and ((-123 / 157 * xPt + 1497) > yPt):
            matrix = matrices[0]
        elif ((-988 / 400 * xPt + 1852.5) < yPt) and ((-123 / 157 * xPt + 1497) >= yPt):
            matrix = matrices[1]
        elif ((-988 / 400 * xPt + 1852.5) < yPt) and ((-123 / 157 * xPt + 1497) < yPt):
            matrix = matrices[2]
        return matrix
    elif video_name == "LOADING DOCK F3 Rampa 11-12":
        xPt -= 1592 * 1 # Second Video
        if ((-24.7 * xPt + 16450) >= yPt) and ((-222 / 163 * xPt + 2268) > yPt):
            matrix = matrices[0]
        elif ((-24.7 * xPt + 16450) < yPt) and ((-222 / 163 * xPt + 2268) >= yPt):
            matrix = matrices[1]
        elif ((-24.7 * xPt + 16450) < yPt) and ((-222 / 163 * xPt + 2268) < yPt):
            matrix = matrices[2]
        return matrix
    elif video_name == "LOADING DOCK F3 Rampa 9-10":
        xPt -= 1592 * 2  # Third Video
        if ((247 / 105 * xPt - 188) <= yPt) and ((-988 / 85 * xPt + 10461) > yPt):
            matrix = matrices[0]
        elif ((247 / 105 * xPt - 188) > yPt) and ((-988 / 85 * xPt + 10461) >= yPt):
            matrix = matrices[1]
        elif ((247 / 105 * xPt - 188) > yPt) and ((-988 / 85 * xPt + 10461) < yPt):
            matrix = matrices[2]
        return matrix
