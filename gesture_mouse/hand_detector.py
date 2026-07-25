"""
HandDetector module.
Wraps MediaPipe Hands. This is the only class in the project that imports
mediapipe directly - everything downstream (GestureRecognizer, main.py)
works with plain (x, y, z) tuples, not MediaPipe's internal objects. That
decoupling is what lets us unit test the gesture logic without a real camera
or the mediapipe dependency installed.
"""

import mediapipe as mp
from gesture_mouse import config


class HandDetector:
    def __init__(self,
                 max_num_hands: int = config.MAX_NUM_HANDS,
                 min_detection_confidence: float = config.MIN_DETECTION_CONFIDENCE,
                 min_tracking_confidence: float = config.MIN_TRACKING_CONFIDENCE):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self._hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, rgb_frame):
        """
        Runs detection on an RGB frame.
        Returns the raw MediaPipe results object (used only for drawing).
        """
        return self._hands.process(rgb_frame)

    @staticmethod
    def extract_landmarks(results):
        """
        Converts MediaPipe's results into a plain list of 21 (x, y, z) tuples
        for the first detected hand, normalized to [0, 1]. Returns None if
        no hand was detected.
        """
        if not results.multi_hand_landmarks:
            return None

        hand = results.multi_hand_landmarks[0]
        return [(lm.x, lm.y, lm.z) for lm in hand.landmark]

    @staticmethod
    def extract_all_landmarks(results):
        """
        Converts MediaPipe's results into a list of dicts for all detected hands,
        each containing 'label' ("Left" or "Right") and 'landmarks' (list of 21 tuples).
        Returns an empty list if no hand was detected.
        """
        if not results.multi_hand_landmarks or not results.multi_handedness:
            return []

        hands_data = []
        for hand, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handedness.classification[0].label
            landmarks = [(lm.x, lm.y, lm.z) for lm in hand.landmark]
            hands_data.append({"label": label, "landmarks": landmarks})
            
        return hands_data

    @staticmethod
    def get_raw_hand_landmarks(results):
        """Returns the raw MediaPipe landmark object for drawing, or None."""
        if not results.multi_hand_landmarks:
            return None
        return results.multi_hand_landmarks[0]

    @staticmethod
    def get_all_raw_hand_landmarks(results):
        """Returns the raw MediaPipe landmark objects for drawing, or empty list."""
        if not results.multi_hand_landmarks:
            return []
        return results.multi_hand_landmarks

    def close(self):
        self._hands.close()
