"""
GestureRecognizer module.

This is the brain of the system and, deliberately, the one class with zero
dependency on OpenCV, MediaPipe, or PyAutoGUI. It takes plain landmark
tuples in and returns a Gesture enum out. That's what makes it possible to
unit test gesture accuracy with synthetic hand positions, no webcam needed.

Design note on the deadzone: a raw per-frame gesture read is noisy - a
"click" pinch can flicker through a couple of frames that look like a
"scroll" pose while the fingers are moving into position. GESTURE_CONFIRM
requires the SAME gesture to be read for several consecutive frames before
it's accepted, which is exactly what prevents a scroll from being
misfired as a click (or vice versa).
"""

import math
from enum import Enum, auto

from gesture_mouse import config


class Gesture(Enum):
    NONE = auto()
    MOVE = auto()
    CLICK = auto()
    RIGHT_CLICK = auto()
    DRAG = auto()
    SCROLL_UP = auto()
    SCROLL_DOWN = auto()
    MINIMIZE = auto()
    MINIMIZE_ALL = auto()


def _distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _is_finger_extended(landmarks, tip_idx, pip_idx):
    """A finger is 'extended' if its tip is above (smaller y) its pip joint."""
    return landmarks[tip_idx][1] < landmarks[pip_idx][1]


class GestureRecognizer:
    def __init__(self,
                 pinch_threshold: float = config.PINCH_THRESHOLD,
                 right_click_threshold: float = config.RIGHT_CLICK_THRESHOLD,
                 confirm_frames: int = config.GESTURE_CONFIRM_FRAMES,
                 drag_hold_frames: int = config.DRAG_HOLD_FRAMES):
        self.pinch_threshold = pinch_threshold
        self.right_click_threshold = right_click_threshold
        self.confirm_frames = confirm_frames
        self.drag_hold_frames = drag_hold_frames

        # deadzone state
        self._candidate_gesture = Gesture.NONE
        self._candidate_streak = 0
        self._confirmed_gesture = Gesture.NONE

        # pinch-hold state (for click vs drag distinction)
        self._pinch_streak = 0

        # scroll state
        self._prev_index_y = None

    def reset(self):
        self._candidate_gesture = Gesture.NONE
        self._candidate_streak = 0
        self._confirmed_gesture = Gesture.NONE
        self._pinch_streak = 0
        self._prev_index_y = None

    def _raw_gesture(self, landmarks) -> Gesture:
        """One-frame classification, before the deadzone smooths it out."""
        thumb_tip = landmarks[config.THUMB_TIP]
        index_tip = landmarks[config.INDEX_TIP]
        middle_tip = landmarks[config.MIDDLE_TIP]
        pinky_tip = landmarks[config.PINKY_TIP]

        pinch_dist = _distance(thumb_tip, index_tip)
        right_click_dist = _distance(thumb_tip, pinky_tip)

        index_extended = _is_finger_extended(landmarks, config.INDEX_TIP, config.INDEX_PIP)
        middle_extended = _is_finger_extended(landmarks, config.MIDDLE_TIP, config.MIDDLE_PIP)
        ring_extended = _is_finger_extended(landmarks, config.RING_TIP, config.RING_PIP)
        pinky_extended = _is_finger_extended(landmarks, config.PINKY_TIP, config.PINKY_PIP)

        # Right click: thumb and pinky pinched together.
        if right_click_dist < self.right_click_threshold:
            return Gesture.RIGHT_CLICK

        # Click/drag: thumb and index pinched together.
        if pinch_dist < self.pinch_threshold:
            return Gesture.CLICK

        # Fist / minimize: all four fingers folded AND the thumb isn't
        # specifically pinched to the index tip (that combination is CLICK,
        # already handled above). A natural fist has the thumb resting over
        # the folded fingers rather than tucked precisely against the index
        # tip, so checking this after the click/right-click checks is what
        # keeps the two from colliding.
        if not index_extended and not middle_extended and not ring_extended and not pinky_extended:
            return Gesture.MINIMIZE

        # Scroll: index + middle extended, ring folded (a "peace sign" without pinky).
        if index_extended and middle_extended and not ring_extended:
            if self._prev_index_y is None:
                return Gesture.NONE  # need a previous frame to know direction
            delta = index_tip[1] - self._prev_index_y
            if abs(delta) < 0.004:  # tiny movements are just hand tremor, ignore
                return Gesture.NONE
            return Gesture.SCROLL_UP if delta < 0 else Gesture.SCROLL_DOWN

        # Default: open hand / pointing -> move the cursor.
        if index_extended:
            return Gesture.MOVE

        return Gesture.NONE

    def recognize(self, landmarks) -> Gesture:
        """
        Main entry point. Feed it one frame's landmarks, get back the
        deadzone-confirmed gesture for that frame.
        """
        if landmarks is None:
            self.reset()
            return Gesture.NONE

        raw = self._raw_gesture(landmarks)

        # track pinch-hold duration to distinguish a quick click from a drag
        if raw == Gesture.CLICK:
            self._pinch_streak += 1
            if self._pinch_streak >= self.drag_hold_frames:
                raw = Gesture.DRAG
        else:
            self._pinch_streak = 0

        # deadzone / confirmation logic
        if raw == self._candidate_gesture:
            self._candidate_streak += 1
        else:
            self._candidate_gesture = raw
            self._candidate_streak = 1

        if self._candidate_streak >= self.confirm_frames:
            self._confirmed_gesture = raw

        # update scroll reference position every frame regardless of gesture
        self._prev_index_y = landmarks[config.INDEX_TIP][1]

        return self._confirmed_gesture

    @staticmethod
    def get_cursor_anchor(landmarks):
        """The landmark used to drive cursor position: the index fingertip."""
        return landmarks[config.INDEX_TIP][0], landmarks[config.INDEX_TIP][1]
