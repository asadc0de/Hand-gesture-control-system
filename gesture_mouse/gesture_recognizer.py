"""
GestureRecognizer module.

This is the brain of the system and, deliberately, the one class with zero
dependency on OpenCV, MediaPipe, or PyAutoGUI. It takes plain landmark
tuples in and returns a Gesture enum out. That's what makes it possible to
unit test gesture accuracy with synthetic hand positions, no webcam needed.

Design note on the deadzone: a raw per-frame gesture read is noisy - a
"click" pinch can flicker through a couple of frames that look like a
"scroll" pose while the fingers are moving into position. GESTURE_CONFIRM_FRAMES
requires the SAME gesture to be read for several consecutive frames before
it's accepted, which is exactly what prevents a scroll from being
misfired as a click (or vice versa).

Click / right-click design note:
- CLICK (Left click candidate): Thumb tip to index tip distance under
  CLICK_PINCH_THRESHOLD in config.py.
- RIGHT_CLICK (Right click candidate): Thumb tip to middle tip distance under
  RIGHT_CLICK_PINCH_THRESHOLD in config.py.
- Quick taps (pinch held <= TAP_HOLD_MAX_MS) fire immediate clicks on release.
- Sustained pinch held > TAP_HOLD_MAX_MS promotes to DRAG.
- Two consecutive taps within DOUBLE_CLICK_WINDOW_MS are merged into a double-click
  by the OS event loop.
"""

import math
import time
from enum import Enum, auto

from gesture_mouse import config


class Gesture(Enum):
    NONE = auto()
    MOVE = auto()
    CLICK = auto()
    RIGHT_CLICK = auto()
    SCROLL = auto()
    MINIMIZE = auto()
    MINIMIZE_ALL = auto()
    RESTORE_ALL = auto()
    RESTORE_LAST = auto()
    RESTORE_ACTIVE = auto()
    BACK = auto()
    FORWARD = auto()
    CLOSE = auto()
    TOGGLE_PRESENTATION_MODE = auto()
    TOGGLE_MEDIA_MODE = auto()
    SCREENSHOT = auto()
    LOCK = auto()


def _distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _is_finger_extended(landmarks, tip_idx, pip_idx):
    """A finger is 'extended' if its tip is further from the wrist than its pip joint."""
    wrist = landmarks[config.WRIST]
    return _distance(landmarks[tip_idx], wrist) > _distance(landmarks[pip_idx], wrist)


def _is_thumb_extended(landmarks):
    """
    A thumb is 'extended' if its tip is significantly further from the pinky base than its 
    IP joint is. This correctly identifies an extended thumb while ignoring a 
    thumb that is just resting against the side of the index finger or curled in a fist.
    """
    tip_dist = _distance(landmarks[config.THUMB_TIP], landmarks[config.PINKY_MCP])
    ip_dist = _distance(landmarks[config.THUMB_IP], landmarks[config.PINKY_MCP])
    return tip_dist > ip_dist * 1.2


def _is_thumb_folded_in_palm(landmarks):
    """A thumb is tucked/folded into the palm if its tip is significantly closer to the pinky MCP than its IP joint
    and well within the palm width (tucked across the palm). Natural open hands with relaxed thumbs have tip_dist >= ip_dist * 0.95."""
    palm_width = _distance(landmarks[config.INDEX_MCP], landmarks[config.PINKY_MCP])
    tip_dist = _distance(landmarks[config.THUMB_TIP], landmarks[config.PINKY_MCP])
    ip_dist = _distance(landmarks[config.THUMB_IP], landmarks[config.PINKY_MCP])
    return (tip_dist < ip_dist * 0.75) and (tip_dist < palm_width * 0.85)



def _is_index_only_point(landmarks):
    """Index extended, other fingers folded (ignoring thumb)."""
    index_extended = _is_finger_extended(landmarks, config.INDEX_TIP, config.INDEX_PIP)
    middle_extended = _is_finger_extended(landmarks, config.MIDDLE_TIP, config.MIDDLE_PIP)
    ring_extended = _is_finger_extended(landmarks, config.RING_TIP, config.RING_PIP)
    pinky_extended = _is_finger_extended(landmarks, config.PINKY_TIP, config.PINKY_PIP)
    return index_extended and not middle_extended and not ring_extended and not pinky_extended


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_intersect(p1, p2, p3, p4):
    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)
    return ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))


def _index_fingers_form_x(landmarks_a, landmarks_b):
    """Two hands, index-only pose, index fingers crossing in an X."""
    if not (_is_index_only_point(landmarks_a) and _is_index_only_point(landmarks_b)):
        return False

    a_wrist = landmarks_a[config.WRIST]
    a_tip = landmarks_a[config.INDEX_TIP]
    b_wrist = landmarks_b[config.WRIST]
    b_tip = landmarks_b[config.INDEX_TIP]

    if _distance(a_wrist, b_wrist) < config.LOCK_X_MIN_WRIST_SEPARATION:
        return False

    if _distance(a_tip, b_tip) > config.LOCK_X_TIP_DISTANCE:
        return False

    return _segments_intersect(a_wrist, a_tip, b_wrist, b_tip)


class GestureRecognizer:
    def __init__(self,
                 confirm_frames: int = config.GESTURE_CONFIRM_FRAMES,
                 tap_hold_max_ms: float = config.TAP_HOLD_MAX_MS):
        self.confirm_frames = confirm_frames
        self.tap_hold_max_ms = tap_hold_max_ms

        # deadzone state
        self._candidate_gesture = Gesture.NONE
        self._candidate_streak = 0
        self._confirmed_gesture = Gesture.NONE

        # one-shot / double-click state for RIGHT_CLICK
        self._last_click_time = 0.0

        # multi-hand / window management state
        self._in_window_management_mode = False
        self._multi_candidate_gesture = Gesture.NONE
        self._multi_candidate_streak = 0
        self._multi_confirmed_gesture = Gesture.NONE

    def reset(self):
        self.reset_single()
        self._in_window_management_mode = False
        self._multi_candidate_gesture = Gesture.NONE
        self._multi_candidate_streak = 0
        self._multi_confirmed_gesture = Gesture.NONE

    def reset_single(self):
        self._candidate_gesture = Gesture.NONE
        self._candidate_streak = 0
        self._confirmed_gesture = Gesture.NONE
        self._last_click_time = 0.0

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

        # Fist / minimize: all five fingers folded.
        if not index_extended and not middle_extended and not ring_extended and not pinky_extended and not thumb_extended:
            return Gesture.MINIMIZE

        # All 4 main fingers extended:
        # - If thumb is actively tucked/folded into the palm: 4-Finger Salute (Media Mode)
        # - Otherwise: Natural 5-finger open hand (Flat Palm / Restore Window)
        if index_extended and middle_extended and ring_extended and pinky_extended:
            if _is_thumb_folded_in_palm(landmarks):
                return Gesture.TOGGLE_MEDIA_MODE
            return Gesture.RESTORE_ACTIVE

        # Scroll: index + middle extended, others folded (a "peace sign").
        if index_extended and middle_extended and not thumb_extended and not ring_extended and not pinky_extended:
            return Gesture.SCROLL

        # Back: only thumb extended (thumbs up)
        if thumb_extended and not index_extended and not middle_extended and not ring_extended and not pinky_extended:
            return Gesture.BACK

        # Pinky extended with index, middle, ring folded:
        # Distinguish between CLOSE (Shaka: Thumb and Pinky widely extended) and FORWARD (Only pinky extended)
        if pinky_extended and not index_extended and not middle_extended and not ring_extended:
            palm_width = _distance(landmarks[config.INDEX_MCP], landmarks[config.PINKY_MCP])
            thumb_index_dist = _distance(landmarks[config.THUMB_TIP], landmarks[config.INDEX_MCP])
            # A true Shaka sign requires the thumb to be extended and widely abducted away from the palm/index
            if thumb_extended and (thumb_index_dist > palm_width * 0.6):
                return Gesture.CLOSE
            return Gesture.FORWARD

        # MOVE (Index only shape): index extended, middle/ring/pinky folded. Thumb is ignored.
        if index_extended and not middle_extended and not ring_extended and not pinky_extended:
            return Gesture.MOVE

        # Toggle Presentation Mode: Index, Middle, Ring extended, thumb folded (3 fingers). 
        # Checked after Media Mode. We ignore the pinky because it naturally extends with the ring finger for some people.
        if index_extended and middle_extended and ring_extended and not thumb_extended:
            return Gesture.TOGGLE_PRESENTATION_MODE

        # Screenshot: Index, Pinky, Thumb extended (Spiderman / I love you sign)
        if index_extended and pinky_extended and thumb_extended and not middle_extended and not ring_extended:
            return Gesture.SCREENSHOT

        return Gesture.NONE

    def recognize(self, right_landmarks, left_landmarks=None) -> Gesture:
        """
        Main entry point. Feed it the landmarks, get back the
        deadzone-confirmed gesture for that frame.
        """
        if right_landmarks is None:
            self.reset()
            return Gesture.NONE

        raw = self._raw_gesture(right_landmarks)

        # deadzone / confirmation logic
        if raw == self._candidate_gesture:
            self._candidate_streak += 1
        else:
            self._candidate_gesture = raw
            self._candidate_streak = 1

        prev_confirmed = self._confirmed_gesture

        if self._candidate_streak >= self.confirm_frames:
            self._confirmed_gesture = raw

            # Clear window management mode if a regular gesture is confirmed
            if self._confirmed_gesture in (Gesture.SCROLL,
                                           Gesture.TOGGLE_PRESENTATION_MODE,
                                           Gesture.TOGGLE_MEDIA_MODE,
                                           Gesture.SCREENSHOT):
                self._in_window_management_mode = False

        confirmed = self._confirmed_gesture

        return confirmed

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
            if _index_fingers_form_x(hands_data[0]["landmarks"], hands_data[1]["landmarks"]):
                raw_multi = Gesture.LOCK
            elif is_fist[0] and is_fist[1]:
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
            elif self._multi_confirmed_gesture in (Gesture.RESTORE_ALL, Gesture.LOCK):
                self._in_window_management_mode = False

        return self._multi_confirmed_gesture

    @staticmethod
    def get_cursor_anchor(landmarks):
        """The landmark used to drive cursor position: the index fingertip."""
        return landmarks[config.INDEX_TIP][0], landmarks[config.INDEX_TIP][1]

    @staticmethod
    def is_finger_extended(landmarks, tip_idx, pip_idx):
        """A finger is 'extended' if its tip is further from the wrist than its pip joint."""
        return _is_finger_extended(landmarks, tip_idx, pip_idx)