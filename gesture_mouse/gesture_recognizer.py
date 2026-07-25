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
    SCROLL = auto()
    MINIMIZE = auto()
    MINIMIZE_ALL = auto()
    RESTORE_ALL = auto()
    RESTORE_LAST = auto()
    RESTORE_ACTIVE = auto()


def _distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _is_finger_extended(landmarks, tip_idx, pip_idx):
    """A finger is 'extended' if its tip is above (smaller y) its pip joint."""
    return landmarks[tip_idx][1] < landmarks[pip_idx][1]


def _is_thumb_extended(landmarks):
    """
    A thumb is 'extended' (like in a finger gun or flat palm) if its tip is
    further from the pinky base than its own base joint is. When tucked into
    a fist, the tip moves across the palm, becoming closer to the pinky base.
    """
    tip_dist = _distance(landmarks[config.THUMB_TIP], landmarks[config.PINKY_MCP])
    base_dist = _distance(landmarks[config.THUMB_MCP], landmarks[config.PINKY_MCP])
    return tip_dist > base_dist


class GestureRecognizer:
    def __init__(self,
                 confirm_frames: int = config.GESTURE_CONFIRM_FRAMES,
                 drag_hold_frames: int = config.DRAG_HOLD_FRAMES):
        self.confirm_frames = confirm_frames
        self.drag_hold_frames = drag_hold_frames

        # deadzone state
        self._candidate_gesture = Gesture.NONE
        self._candidate_streak = 0
        self._confirmed_gesture = Gesture.NONE

        # pinch-hold state (for click vs drag distinction)
        self._pinch_streak = 0

        # multi-hand / window management state
        self._in_window_management_mode = False
        self._multi_candidate_gesture = Gesture.NONE
        self._multi_candidate_streak = 0
        self._multi_confirmed_gesture = Gesture.NONE

    def reset(self):
        self._candidate_gesture = Gesture.NONE
        self._candidate_streak = 0
        self._confirmed_gesture = Gesture.NONE
        self._pinch_streak = 0
        self._in_window_management_mode = False
        self._multi_candidate_gesture = Gesture.NONE
        self._multi_candidate_streak = 0
        self._multi_confirmed_gesture = Gesture.NONE

    def _raw_gesture(self, landmarks) -> Gesture:
        """One-frame classification, before the deadzone smooths it out."""
        thumb_tip = landmarks[config.THUMB_TIP]
        index_tip = landmarks[config.INDEX_TIP]
        middle_tip = landmarks[config.MIDDLE_TIP]
        pinky_tip = landmarks[config.PINKY_TIP]

        index_extended = _is_finger_extended(landmarks, config.INDEX_TIP, config.INDEX_PIP)
        middle_extended = _is_finger_extended(landmarks, config.MIDDLE_TIP, config.MIDDLE_PIP)
        ring_extended = _is_finger_extended(landmarks, config.RING_TIP, config.RING_PIP)
        pinky_extended = _is_finger_extended(landmarks, config.PINKY_TIP, config.PINKY_PIP)
        thumb_extended = _is_thumb_extended(landmarks)

        # Left click / Drag: index and thumb UP ("L" shape / finger gun), others folded.
        if index_extended and thumb_extended and not middle_extended and not ring_extended and not pinky_extended:
            return Gesture.CLICK

        # Right click: index and pinky UP, others folded.
        if index_extended and pinky_extended and not thumb_extended and not middle_extended and not ring_extended:
            return Gesture.RIGHT_CLICK

        # Fist / minimize: all five fingers folded.
        if not index_extended and not middle_extended and not ring_extended and not pinky_extended and not thumb_extended:
            return Gesture.MINIMIZE

        # Scroll: index + middle extended, ring folded (a "peace sign" without pinky).
        if index_extended and middle_extended and not ring_extended:
            return Gesture.SCROLL

        # Restore Active: all 5 fingers fully extended (flat palm)
        if index_extended and middle_extended and ring_extended and pinky_extended and thumb_extended:
            return Gesture.RESTORE_ACTIVE

        # Default: pointing (index extended, middle folded, thumb folded) -> move the cursor.
        if index_extended and not middle_extended and not thumb_extended:
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
            
            # Clear window management mode if a regular gesture is confirmed
            if self._confirmed_gesture in (Gesture.MOVE, Gesture.CLICK, Gesture.DRAG, 
                                           Gesture.RIGHT_CLICK, Gesture.SCROLL):
                self._in_window_management_mode = False

        return self._confirmed_gesture

    def recognize_multi(self, hands_data) -> Gesture:
        """
        Evaluates two-hand gestures. Returns the confirmed multi-hand gesture,
        or Gesture.NONE if no multi-hand gesture applies.
        """
        if not hands_data:
            self._multi_candidate_gesture = Gesture.NONE
            self._multi_candidate_streak = 0
            self._multi_confirmed_gesture = Gesture.NONE
            return Gesture.NONE

        raw_gestures = [self._raw_gesture(h["landmarks"]) for h in hands_data]
        is_fist = [r == Gesture.MINIMIZE for r in raw_gestures]
        
        raw_multi = Gesture.NONE
        
        if len(hands_data) >= 2:
            if is_fist[0] and is_fist[1]:
                raw_multi = Gesture.MINIMIZE_ALL
            elif not is_fist[0] and not is_fist[1]:
                if self._in_window_management_mode:
                    raw_multi = Gesture.RESTORE_ALL
            else:
                if self._in_window_management_mode:
                    raw_multi = Gesture.RESTORE_LAST
        elif len(hands_data) == 1:
            if is_fist[0]:
                if self._in_window_management_mode:
                    raw_multi = Gesture.RESTORE_LAST
                    
        if raw_multi == self._multi_candidate_gesture:
            self._multi_candidate_streak += 1
        else:
            self._multi_candidate_gesture = raw_multi
            self._multi_candidate_streak = 1
            
        if self._multi_candidate_streak >= self.confirm_frames:
            self._multi_confirmed_gesture = raw_multi
            
            if self._multi_confirmed_gesture == Gesture.MINIMIZE_ALL:
                self._in_window_management_mode = True
            elif self._multi_confirmed_gesture == Gesture.RESTORE_ALL:
                self._in_window_management_mode = False
                
        return self._multi_confirmed_gesture

    @staticmethod
    def get_cursor_anchor(landmarks):
        """The landmark used to drive cursor position: the index fingertip."""
        return landmarks[config.INDEX_TIP][0], landmarks[config.INDEX_TIP][1]
