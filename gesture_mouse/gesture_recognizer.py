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

Click / right-click design note (fixed version): both are detected by
actual pinch distance (thumb tip to index tip for CLICK, thumb tip to
pinky tip for RIGHT_CLICK) against PINCH_THRESHOLD / RIGHT_CLICK_THRESHOLD
in config.py. Earlier versions defined those thresholds but never used
them, relying instead on brittle static hand shapes. Distance-based
detection is what those config values were built for, so that's what
drives it now. CLICK and RIGHT_CLICK are one-shot: once confirmed, they
fire exactly once per pinch, not once per frame the pinch is held. A
second CLICK within DOUBLE_CLICK_WINDOW seconds of the last one is
promoted to DOUBLE_CLICK. Holding a pinch past DRAG_HOLD_FRAMES promotes
it to DRAG instead of firing a click at all.
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
    DRAG = auto()
    SCROLL = auto()
    MINIMIZE = auto()
    MINIMIZE_ALL = auto()
    RESTORE_ALL = auto()
    RESTORE_LAST = auto()
    RESTORE_ACTIVE = auto()
    BACK = auto()
    FORWARD = auto()
    DOUBLE_CLICK = auto()
    CLOSE = auto()
    TOGGLE_PRESENTATION_MODE = auto()
    SCREENSHOT = auto()


def _distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _is_finger_extended(landmarks, tip_idx, pip_idx):
    """A finger is 'extended' if its tip is further from the wrist than its pip joint."""
    wrist = landmarks[config.WRIST]
    return _distance(landmarks[tip_idx], wrist) > _distance(landmarks[pip_idx], wrist)


def _is_thumb_extended(landmarks):
    """
    A thumb is 'extended' if its tip is further from the pinky base than its 
    IP joint is. This correctly identifies an extended thumb while ignoring a 
    thumb that is just resting against the side of the index finger.
    """
    tip_dist = _distance(landmarks[config.THUMB_TIP], landmarks[config.PINKY_MCP])
    ip_dist = _distance(landmarks[config.THUMB_IP], landmarks[config.PINKY_MCP])
    return tip_dist > ip_dist


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

        # one-shot / double-click state for RIGHT_CLICK
        self._last_click_time = 0.0

        # Temporal state for index finger (Phase 1 Fix)
        self._index_history = []
        self._current_index_state = False
        self._drag_active = False

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
        self._index_history = []
        self._current_index_state = False
        self._drag_active = False

    def _raw_gesture(self, landmarks) -> Gesture:
        """One-frame classification, before the deadzone smooths it out."""
        thumb_tip = landmarks[config.THUMB_TIP]
        index_tip = landmarks[config.INDEX_TIP]
        pinky_tip = landmarks[config.PINKY_TIP]

        index_extended = _is_finger_extended(landmarks, config.INDEX_TIP, config.INDEX_PIP)
        middle_extended = _is_finger_extended(landmarks, config.MIDDLE_TIP, config.MIDDLE_PIP)
        ring_extended = _is_finger_extended(landmarks, config.RING_TIP, config.RING_PIP)
        pinky_extended = _is_finger_extended(landmarks, config.PINKY_TIP, config.PINKY_PIP)
        thumb_extended = _is_thumb_extended(landmarks)

        # Right Click (Rock sign): Index and pinky extended, others folded
        if index_extended and pinky_extended and not middle_extended and not ring_extended and not thumb_extended:
            return Gesture.RIGHT_CLICK

        # Close Window: Thumb and Pinky extended (Shaka sign)
        if thumb_extended and pinky_extended and not index_extended and not middle_extended and not ring_extended:
            return Gesture.CLOSE

        # Fist / minimize: all five fingers folded.
        if not index_extended and not middle_extended and not ring_extended and not pinky_extended and not thumb_extended:
            return Gesture.MINIMIZE

        # Scroll: index + middle extended, others folded (a "peace sign").
        if index_extended and middle_extended and not thumb_extended and not ring_extended and not pinky_extended:
            return Gesture.SCROLL

        # Restore Active: all 5 fingers fully extended (flat palm)
        if index_extended and middle_extended and ring_extended and pinky_extended and thumb_extended:
            return Gesture.RESTORE_ACTIVE

        # Back: only thumb extended (thumbs up)
        if thumb_extended and not index_extended and not middle_extended and not ring_extended and not pinky_extended:
            return Gesture.BACK

        # Forward: only pinky extended
        if pinky_extended and not index_extended and not middle_extended and not ring_extended and not thumb_extended:
            return Gesture.FORWARD

        # MOVE (Index only shape): index extended, middle/ring/pinky folded. Thumb is ignored.
        if index_extended and not middle_extended and not ring_extended and not pinky_extended:
            return Gesture.MOVE

        # Toggle Presentation Mode: Index, Middle, Ring extended, thumb folded. 
        # We ignore the pinky because it's anatomically difficult to keep it fully folded while extending the ring finger.
        if index_extended and middle_extended and ring_extended and not thumb_extended:
            return Gesture.TOGGLE_PRESENTATION_MODE

        # Screenshot: Index, Pinky, Thumb extended (Spiderman / I love you sign)
        if index_extended and pinky_extended and thumb_extended and not middle_extended and not ring_extended:
            return Gesture.SCREENSHOT

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
            if self._confirmed_gesture in (Gesture.MOVE, Gesture.CLICK, Gesture.DRAG,
                                           Gesture.RIGHT_CLICK, Gesture.SCROLL,
                                           Gesture.TOGGLE_PRESENTATION_MODE,
                                           Gesture.SCREENSHOT):
                self._in_window_management_mode = False

        confirmed = self._confirmed_gesture

        # Phase 1 Temporal Logic for CLICK, DOUBLE_CLICK, DRAG
        current_time = time.time()
        self._index_history = [h for h in self._index_history if current_time - h[1] < 1.0]

        is_index_only = (confirmed == Gesture.MOVE)

        if is_index_only and not self._current_index_state:
            # Transition to EXTEND
            self._current_index_state = True
            self._index_history.append(("EXTEND", current_time))
            self._drag_active = False
            
            # Check DOUBLE_CLICK
            if len(self._index_history) >= 3:
                e1, e2, e3 = self._index_history[-3:]
                if e1[0] == "EXTEND" and e2[0] == "FOLD" and e3[0] == "EXTEND":
                    if e3[1] - e1[1] <= config.DOUBLE_CLICK_WINDOW:
                        self._index_history = [] # Consume events
                        return Gesture.DOUBLE_CLICK

        elif not is_index_only and self._current_index_state:
            # Transition to FOLD or OTHER
            self._current_index_state = False
            if confirmed in (Gesture.MINIMIZE, Gesture.NONE):
                self._index_history.append(("FOLD", current_time))
                if not self._drag_active and len(self._index_history) >= 2:
                    e1, e2 = self._index_history[-2:]
                    if e1[0] == "EXTEND" and e2[0] == "FOLD":
                        if e2[1] - e1[1] <= config.CLICK_FOLD_WINDOW:
                            return Gesture.CLICK
            else:
                # Transitioned to SCROLL or something else, abort click tracking
                self._index_history = []

        # Check DRAG
        if is_index_only:
            if len(self._index_history) > 0 and self._index_history[-1][0] == "EXTEND":
                if current_time - self._index_history[-1][1] > config.DRAG_HOLD_SECONDS:
                    self._drag_active = True
                    return Gesture.DRAG
            return Gesture.MOVE

        # --- One-shot firing for RIGHT_CLICK ---
        if confirmed == Gesture.RIGHT_CLICK:
            if prev_confirmed != Gesture.RIGHT_CLICK:
                return Gesture.RIGHT_CLICK
            return Gesture.NONE

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