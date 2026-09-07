"""
Unit tests for Pinch-to-Zoom logic in Presentation Mode.
"""

import unittest
from unittest.mock import MagicMock
import math

from gesture_mouse import config
from gesture_mouse.gesture_recognizer import GestureRecognizer


def make_zoom_hand(thumb_tip, index_tip, index_pip=(0.5, 0.65, 0.0),
                   middle_folded=True, ring_folded=True, pinky_folded=True):
    lm = [(0.5, 0.9, 0.0)] * 21
    lm[config.WRIST] = (0.5, 0.9, 0.0)
    lm[config.THUMB_TIP] = thumb_tip
    lm[config.INDEX_TIP] = index_tip
    lm[config.INDEX_PIP] = index_pip
    
    # Middle
    lm[config.MIDDLE_PIP] = (0.5, 0.65, 0.0)
    lm[config.MIDDLE_TIP] = (0.5, 0.70, 0.0) if middle_folded else (0.5, 0.35, 0.0)
    
    # Ring
    lm[config.RING_PIP] = (0.6, 0.65, 0.0)
    lm[config.RING_TIP] = (0.6, 0.70, 0.0) if ring_folded else (0.6, 0.35, 0.0)
    
    # Pinky
    lm[config.PINKY_PIP] = (0.7, 0.65, 0.0)
    lm[config.PINKY_TIP] = (0.7, 0.70, 0.0) if pinky_folded else (0.7, 0.35, 0.0)
    
    return lm


class TestPinchToZoom(unittest.TestCase):
    def test_zoom_in_when_fingers_spread(self):
        """
        Spreading thumb and index apart (distance increases >= ZOOM_SENSITIVITY) -> Zoom IN (+120).
        """
        mouse = MagicMock()
        zoom_dist = None

        # Frame 1: Pinch start at dist = 0.05
        hand_start = make_zoom_hand(thumb_tip=(0.5, 0.5), index_tip=(0.55, 0.5))
        thumb = hand_start[config.THUMB_TIP]
        index = hand_start[config.INDEX_TIP]
        dist = math.hypot(thumb[0] - index[0], thumb[1] - index[1])
        zoom_dist = dist  # 0.05

        # Frame 2: Fingers spread to dist = 0.11 (+0.06 >= 0.05)
        hand_spread = make_zoom_hand(thumb_tip=(0.5, 0.5), index_tip=(0.61, 0.5))
        thumb = hand_spread[config.THUMB_TIP]
        index = hand_spread[config.INDEX_TIP]
        dist = math.hypot(thumb[0] - index[0], thumb[1] - index[1])
        delta = dist - zoom_dist

        if abs(delta) >= config.ZOOM_SENSITIVITY:
            steps = int(abs(delta) / config.ZOOM_SENSITIVITY)
            zoom_amount = 120 * steps if delta > 0 else -120 * steps
            mouse.zoom(zoom_amount)
            zoom_dist += steps * config.ZOOM_SENSITIVITY

        mouse.zoom.assert_called_once_with(120)
        self.assertAlmostEqual(zoom_dist, 0.10, places=4)

    def test_zoom_out_when_fingers_pinch_in(self):
        """
        Pinching thumb and index closer (distance decreases >= ZOOM_SENSITIVITY) -> Zoom OUT (-120).
        """
        mouse = MagicMock()
        zoom_dist = None

        # Frame 1: Open "L" start at dist = 0.15
        hand_start = make_zoom_hand(thumb_tip=(0.5, 0.5), index_tip=(0.65, 0.5))
        thumb = hand_start[config.THUMB_TIP]
        index = hand_start[config.INDEX_TIP]
        dist = math.hypot(thumb[0] - index[0], thumb[1] - index[1])
        zoom_dist = dist  # 0.15

        # Frame 2: Fingers close to dist = 0.09 (-0.06 <= -0.05)
        hand_close = make_zoom_hand(thumb_tip=(0.5, 0.5), index_tip=(0.59, 0.5))
        thumb = hand_close[config.THUMB_TIP]
        index = hand_close[config.INDEX_TIP]
        dist = math.hypot(thumb[0] - index[0], thumb[1] - index[1])
        delta = dist - zoom_dist

        if abs(delta) >= config.ZOOM_SENSITIVITY:
            steps = int(abs(delta) / config.ZOOM_SENSITIVITY)
            zoom_amount = 120 * steps if delta > 0 else -120 * steps
            mouse.zoom(zoom_amount)
            zoom_dist -= steps * config.ZOOM_SENSITIVITY

        mouse.zoom.assert_called_once_with(-120)
        self.assertAlmostEqual(zoom_dist, 0.10, places=4)

    def test_zoom_deactivates_when_other_fingers_unfold(self):
        """
        When middle finger extends (e.g. peace sign or flat palm), zoom baseline is reset.
        """
        hand_unfolded = make_zoom_hand(thumb_tip=(0.5, 0.5), index_tip=(0.60, 0.5), middle_folded=False)
        middle_ext = GestureRecognizer.is_finger_extended(hand_unfolded, config.MIDDLE_TIP, config.MIDDLE_PIP)
        ring_ext = GestureRecognizer.is_finger_extended(hand_unfolded, config.RING_TIP, config.RING_PIP)
        pinky_ext = GestureRecognizer.is_finger_extended(hand_unfolded, config.PINKY_TIP, config.PINKY_PIP)

        is_zoom_pose = not middle_ext and not ring_ext and not pinky_ext
        self.assertFalse(is_zoom_pose)


if __name__ == "__main__":
    unittest.main()
