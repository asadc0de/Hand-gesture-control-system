"""
HandTracker
-----------
Thin, decoupled wrapper around MediaPipe's HandLandmarker (Tasks API).

Older MediaPipe tutorials use `mp.solutions.hands.Hands(...)` - that legacy
"solutions" API has been removed from recent MediaPipe pip packages, so this
uses the modern Tasks API instead (`mediapipe.tasks.python.vision`), which is
what current MediaPipe versions ship regardless of platform.

Its only job is: turn a BGR camera frame into a list of index-fingertip
positions (normalized 0..1 coordinates). Nothing in here knows about pygame,
fruit, or scoring - keeps the class reusable in the FYP project too.
"""

import os
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python import BaseOptions

from . import constants as C

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
_MODEL_PATH = os.path.join(_MODEL_DIR, "hand_landmarker.task")

# Landmark index 8 is the index fingertip in MediaPipe's 21-point hand model.
INDEX_FINGER_TIP = 8


def _ensure_model_downloaded():
    if os.path.exists(_MODEL_PATH) and os.path.getsize(_MODEL_PATH) > 0:
        return _MODEL_PATH
    os.makedirs(_MODEL_DIR, exist_ok=True)
    print("Downloading hand landmark model (first run only)...")
    try:
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    except Exception as exc:
        raise RuntimeError(
            "Could not download the MediaPipe hand landmark model.\n"
            f"Tried: {_MODEL_URL}\n"
            f"Reason: {exc}\n"
            "Fix: download that file manually and place it at "
            f"{_MODEL_PATH}"
        ) from exc
    print(f"Model saved to {_MODEL_PATH}")
    return _MODEL_PATH


class HandTracker:
    def __init__(self,
                 max_hands: int = C.MAX_HANDS,
                 detection_conf: float = C.DETECTION_CONFIDENCE,
                 tracking_conf: float = C.TRACKING_CONFIDENCE):
        model_path = _ensure_model_downloaded()
        options = mp_vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )
        self.landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self._start_time = time.time()
        self._last_timestamp_ms = -1

    def process(self, bgr_frame):
        """
        Returns a list of (x_norm, y_norm) tuples, one per detected hand's
        index fingertip, in normalized [0,1] coordinates. Empty list if no
        hand is detected.
        """
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        timestamp_ms = int((time.time() - self._start_time) * 1000)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        tips = []
        if result.hand_landmarks:
            for hand_landmarks in result.hand_landmarks:
                lm = hand_landmarks[INDEX_FINGER_TIP]
                tips.append((lm.x, lm.y))
        return tips

    def close(self):
        self.landmarker.close()
