import argparse
import cv2
from media_handler import PipeliningVideoManager, ImageManager

parser = argparse.ArgumentParser()
parser.add_argument(
    "--video_path", type=str, default="", help="Video path"
)
parser.add_argument(
    "--save_path", type=str, default="", help="Save path"
)


class ImageExtractor:
    def __init__(self, video_path, save_path):
        self._VideoHandle = PipeliningVideoManager()
        self.FrameRate, self.ImageSize = self._VideoHandle.load_video(video_path)
        self.VideoPath = video_path
        self.SavePath = save_path

        self.extract()

    def extract(self):
        while True:
            _, np_bgr_image = self._VideoHandle.pop()

            if np_bgr_image is None:
                self._VideoHandle.release_video_object()
                return
            file_name = self._VideoHandle.make_image_name()
            ImageManager.save_image(img=np_bgr_image, path=self.SavePath + file_name)


if __name__ == "__main__":
    args = parser.parse_args()
    img_obj = ImageExtractor(video_path=args.video_path, save_path=args.save_path)
