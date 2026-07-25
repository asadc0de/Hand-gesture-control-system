"""
Camera module.
Wraps cv2.VideoCapture so the rest of the system never talks to OpenCV's
camera API directly. If you ever swap to a different capture source
(a video file, an IP camera), this is the only class that needs to change.
"""

import cv2
from gesture_mouse import config


class Camera:
    def __init__(self, index: int = config.CAMERA_INDEX,
                 width: int = config.FRAME_WIDTH,
                 height: int = config.FRAME_HEIGHT):
        self._index = index
        self._width = width
        self._height = height
        self._cap = None

    def start(self):
        """Opens the webcam. Raises RuntimeError if it can't be opened."""
        self._cap = cv2.VideoCapture(self._index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)

        if not self._cap.isOpened():
            raise RuntimeError(
                f"Could not open webcam at index {self._index}. "
                "Check that it's connected and not in use by another app."
            )
        return self

    def read_frame(self):
        """
        Returns a single BGR frame as a numpy array, or None if the read failed.
        Does NOT flip or convert color - that's ImageProcessor's job.
        """
        if self._cap is None:
            raise RuntimeError("Camera not started. Call start() first.")

        success, frame = self._cap.read()
        if not success:
            return None
        return frame

    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
