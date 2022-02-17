import os
import cv2
import imageio
import numpy as np

import tensorflow as tf
from matplotlib import pyplot as plt


class VideoManger:
    def __init__(self):
        self.__video_list = []
        self.__frame_list = []
        self.__video_object = None
        self.__frame_rate = 0

        self._frame_rate = None
        self._image_width = 0
        self._image_height = 0

    def scan_video(self, path):
        """ Scanning videos(mp4 and avi) of path

        Args:
            path: video folder
        Returns:
            video list: video filenames [A.avi, B.mp4, ..., N.avi or N.mp4]
        """

        self.__video_list = []
        files = os.listdir(path)
        for file in files:
            if '.mp4' in file or '.avi' in file:
                self.__video_list.append(file)

        return self.__video_list

    def load_video(self, path):
        """ Activate video object of path

                Args:
                    path: a video filename
                Returns:
                    process result: boolean {True, False}
        """
        self.__frame_list.clear()
        self.__video_object = cv2.VideoCapture(path)
        fps = self.__video_object.get(cv2.CAP_PROP_FPS)
        width = self.__video_object.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.__video_object.get(cv2.CAP_PROP_FRAME_HEIGHTE)
        print("Frames per second using video.get(cv2.CAP_PROP_FPS) : {0}".format(fps))
        print("Image Width using video.get(cv2.CAP_PROP_FRAME_WIDTH) : {0}".format(width))
        print("Image Height using video.get(cv2.CAP_PROP_FRAME_HEIGHT) : {0}".format(height))

        self._frame_rate = fps
        self._image_width = width
        self._image_height = height

        return True

    def update_video_property(self, path):
        if self.load_video(path):
            self.__video_object = None
            return True
        return False

    def append(self, img):
        """ for making output video, append image object

                Args:
                    img: an image using opencv2
                Returns:
                    None
        """
        self.__frame_list.append(img)

    def pop(self):
        if self.__video_object is None:
            return False, None
        else:
            rtn, img = self.__video_object.read()
            return rtn, img

    def write_video(self, path):
        """ for making output video, append image object

                Args:
                    path: save path conclude video name
                Returns:
                    process result: boolean {True, False}
        """
        out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'DIVX'),
                              self._frame_rate, (self._image_width, self._image_height))
        for i in range(len(self.__frame_list)):
            # writing to an image array
            out.write(self.__frame_list[i])
        out.release()


class PipeliningVideoManager(VideoManger):
    def __init__(self):
        super().__init__()
        self.__OutputVideo = None

    def activate_video_object(self, path):
        if self.__OutputVideo is None or self._frame_rate is None:
            return False
        else:
            self.__OutputVideo = cv2.VideoWriter(path,
                                                 cv2.VideoWriter_fourcc(*'DIVX'),
                                                 self._frame_rate,
                                                 (self._image_width, self._image_height))
            return True

    def append(self, img):
        self.__OutputVideo.write(img)

    def release_video_object(self):
        if self.__OutputVideo is not None:
            self.__OutputVideo.release()
            return True
        return False


class ImageManager:
    def __init__(self):
        self.test = True
        self.figure = None

    @staticmethod
    def load_tensor(path):
        img = tf.io.read_file(path)
        img = tf.image.decode_jpeg(img, channels=3)
        return img

    @staticmethod
    def load_cv(path):
        img = cv2.imread(path)
        return img

    @staticmethod
    def convert_uint(img):
        converted_img = tf.image.convert_image_dtype(img, tf.uint8)[tf.newaxis, ...]
        return converted_img

    @staticmethod
    def save_image(img: np.array, path):
        imageio.imwrite(path, img)

    def display_image(self, img):
        self.figure = plt.figure(figsize=(20, 15))
        plt.grid(False)
        plt.imshow(img)


if __name__ == "__main__":
    test = VideoManger()
    video_list = test.scan_video(path='../video')
    test.load_video('../video/' + video_list[0])
