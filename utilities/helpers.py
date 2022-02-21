    #!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Helper classes and functions for detection and tracking
"""

import imageio
import numpy as np
import cv2

global count
count = 1

class Box:
    def __init__(self):
        self.x, self.y = float(), float()
        self.w, self.h = float(), float()
        self.c = float()
        self.prob = float()


def overlap(x1, w1, x2, w2):
    l1 = x1 - w1 / 2.
    l2 = x2 - w2 / 2.
    left = max(l1, l2)
    r1 = x1 + w1 / 2.
    r2 = x2 + w2 / 2.
    right = min(r1, r2)
    return right - left


def box_intersection(a, b):
    w = overlap(a.x, a.w, b.x, b.w)
    h = overlap(a.y, a.h, b.y, b.h)
    if w < 0 or h < 0:
        return 0
    area = w * h
    return area


def box_union(a, b):
    i = box_intersection(a, b)
    u = a.w * a.h + b.w * b.h - i
    return u


def box_iou(a, b):
    return box_intersection(a, b) / box_union(a, b)


def box_iou2(a, b):
    """
    Helper function to calculate the ratio between intersection and the union of
    two boxes a and b
    a[0], a[1], a[2], a[3] <-> left, up, right, bottom
    """

    w_intsec = np.maximum(0, (np.minimum(a[2], b[2]) - np.maximum(a[0], b[0])))
    h_intsec = np.maximum(0, (np.minimum(a[3], b[3]) - np.maximum(a[1], b[1])))
    s_intsec = w_intsec * h_intsec
    s_a = (a[2] - a[0]) * (a[3] - a[1])
    s_b = (b[2] - b[0]) * (b[3] - b[1])

    return float(s_intsec) / (s_a + s_b - s_intsec)


def post_iou_checker(target, candidates, thr=0.5, offset=0.2):
    width = abs(target[2] - target[0])
    height = abs(target[3] - target[1])
    surface = width * height
    for candidate in candidates:
        iou = box_iou2(target, candidate)
        if iou >= thr:
            # surface calculating
            w = abs(candidate[2] - candidate[0])
            h = abs(candidate[3] - candidate[1])
            if (surface * (1-offset)) < (w*h) < (surface * (1+offset)):
                return True, candidate
            else:
                print(surface/(w*h))
    return False, None


def convert_to_pixel(box_yolo, img, crop_range):
    """
    Helper function to convert (scaled) coordinates of a bounding box
    to pixel coordinates.

    Example (0.89361443264143803, 0.4880486045564924, 0.23544462956491041,
    0.36866588651069609)

    crop_range: specifies the part of image to be cropped
    """

    box = box_yolo
    imgcv = img
    [xmin, xmax] = crop_range[0]
    [ymin, ymax] = crop_range[1]
    h, w, _ = imgcv.shape

    # Calculate left, top, width, and height of the bounding box
    left = int((box.x - box.w / 2.) * (xmax - xmin) + xmin)
    top = int((box.y - box.h / 2.) * (ymax - ymin) + ymin)

    width = int(box.w * (xmax - xmin))
    height = int(box.h * (ymax - ymin))

    # Deal with corner cases
    if left < 0:
        left = 0
    if top < 0:
        top = 0

    # Return the coordinates (in the unit of the pixels)

    box_pixel = np.array([left, top, width, height])
    return box_pixel


def convert_to_cv2bbox(bbox, img_dim=(1280, 720)):
    """
    Helper fucntion for converting bbox to bbox_cv2
    bbox = [left, top, width, height]
    bbox_cv2 = [left, top, right, bottom]
    img_dim: dimension of the image, img_dim[0]<-> x
    img_dim[1]<-> y
    """
    left = np.maximum(0, bbox[0])
    top = np.maximum(0, bbox[1])
    right = np.minimum(img_dim[0], bbox[0] + bbox[2])
    bottom = np.minimum(img_dim[1], bbox[1] + bbox[3])

    return left, top, right, bottom


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def transform(bbox_cv2, img, plan_img, matrixes, box_color=(0, 255, 255)):
    global count
    if isinstance(box_color, tuple) is False:
        box_color = hex_to_rgb(box_color)
    left, top, right, bottom = bbox_cv2[1], bbox_cv2[0], bbox_cv2[3], bbox_cv2[2]
    xPt = (left + right) / 2
    # yPt = (top + bottom) / 2

    # 아래 하단
    yPt = bottom

    if ((-8 / 3 * xPt + 1600) > yPt) and ((-25 / 39 * xPt + 1120) > yPt):
        matrix = matrixes[0]
    elif ((-8 / 3 * xPt + 1600) < yPt) and ((-25 / 39 * xPt + 1120) > yPt):
        matrix = matrixes[1]
    elif ((-8 / 3 * xPt + 1600) < yPt) and ((-25 / 39 * xPt + 1120) < yPt):
        matrix = matrixes[2]

    img_height = img.shape[0]
    yPt = img_height - yPt
    plan_img_height = plan_img.shape[0]
    w = (xPt * matrix[2][0]) + (yPt * matrix[2][1]) + matrix[2][2]
    x = ((xPt * matrix[0][0]) + (yPt * matrix[0][1]) + matrix[0][2]) / w
    y = ((xPt * matrix[1][0]) + (yPt * matrix[1][1]) + matrix[1][2]) / w

    dummy_ypt = 300 + (int(plan_img_height - y) - 300) / 5
    # dummy_ypt = 300 + (int(plan_img_height - y) - 300) / 10

    plan_image = cv2.circle(plan_img, (int(x), int(plan_img_height - y)), 5, box_color, thickness=-1)
    return plan_image


def draw_box_label(img, bbox_cv2, box_color=(0, 255, 255), show_label=True):
    """
    Helper function for drawing the bounding boxes and the labels
    bbox_cv2 = [left, top, right, bottom]
    """
    if isinstance(box_color, tuple) is False:
        box_color = hex_to_rgb(box_color)
    # box_color= (0, 255, 255)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_size = 0.7
    font_color = (0, 0, 0)
    left, top, right, bottom = bbox_cv2[1], bbox_cv2[0], bbox_cv2[3], bbox_cv2[2]

    # Draw the bounding box
    cv2.rectangle(img, (left, top), (right, bottom), box_color, 4)

    if show_label:
        # Draw a filled box on top of the bounding box (as the background for the labels)
        cv2.rectangle(img, (left - 2, top - 45), (right + 2, top), box_color, -1, 1)

        # Output the labels that show the x and y coordinates of the bounding box center.
        text_x = 'x=' + str((left + right) / 2)
        cv2.putText(img, text_x, (left, top - 25), font, font_size, font_color, 1, cv2.LINE_AA)
        text_y = 'y=' + str((top + bottom) / 2)
        cv2.putText(img, text_y, (left, top - 5), font, font_size, font_color, 1, cv2.LINE_AA)
    return img
