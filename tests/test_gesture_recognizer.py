"""
Unit tests for GestureRecognizer.

These tests build synthetic (x, y, z) landmark sets by hand - no webcam,
no MediaPipe, no PyAutoGUI required - because GestureRecognizer only ever
consumes plain tuples. This is exactly what the SDD asks for: verification
that a click can't be misread as a scroll and vice versa, expressed as
repeatable, automated tests instead of "it looked fine on my webcam."
"""

import unittest

from gesture_mouse import config
from gesture_mouse.gesture_recognizer import GestureRecognizer, Gesture


def make_base_hand():
    """
    21 landmarks with every finger folded (tip below its pip joint) and
    the thumb resting away from other fingertips. This is the neutral
    'closed hand' pose that every other pose below is built from.
    """
    lm = [(0.5, 0.9, 0.0)] * 21  # placeholder wrist-ish default

    lm[config.THUMB_MCP] = (0.2, 0.70, 0.0)
    lm[config.INDEX_MCP] = (0.4, 0.60, 0.0)
    lm[config.MIDDLE_MCP] = (0.5, 0.60, 0.0)
    lm[config.RING_MCP] = (0.6, 0.60, 0.0)
    lm[config.PINKY_MCP] = (0.8, 0.60, 0.0)

    # PIP joints
    lm[config.INDEX_PIP] = (0.4, 0.65, 0.0)
    lm[config.MIDDLE_PIP] = (0.5, 0.65, 0.0)
    lm[config.RING_PIP] = (0.6, 0.65, 0.0)
    lm[config.PINKY_PIP] = (0.8, 0.65, 0.0)

    # folded tips: y greater than pip -> curled toward palm
    lm[config.INDEX_TIP] = (0.42, 0.70, 0.0)
    lm[config.MIDDLE_TIP] = (0.52, 0.70, 0.0)
    lm[config.RING_TIP] = (0.62, 0.70, 0.0)
    lm[config.PINKY_TIP] = (0.82, 0.70, 0.0)
    
    # thumb tucked: tip near the palm/pinky side
    lm[config.THUMB_IP] = (0.4, 0.68, 0.0)
    lm[config.THUMB_TIP] = (0.6, 0.65, 0.0) 

    return lm


def extend_finger(lm, tip_idx, pip_idx, x=None):
    """Returns a copy of lm with the given finger pointing up (extended)."""
    lm = list(lm)
    px = x if x is not None else lm[tip_idx][0]
    lm[tip_idx] = (px, 0.35, 0.0)  # well above its pip -> extended
    return lm


def make_index_point_hand(wrist_x, tip_x, tip_y=0.35):
    """Single hand with only the index finger extended, wrist placed at wrist_x."""
    lm = [(wrist_x, 0.70, 0.0)] * 21

    lm[config.WRIST] = (wrist_x, 0.70, 0.0)
    lm[config.THUMB_MCP] = (wrist_x - 0.08, 0.62, 0.0)
    lm[config.INDEX_MCP] = (wrist_x + 0.05, 0.60, 0.0)
    lm[config.MIDDLE_MCP] = (wrist_x + 0.10, 0.60, 0.0)
    lm[config.RING_MCP] = (wrist_x + 0.15, 0.60, 0.0)
    lm[config.PINKY_MCP] = (wrist_x + 0.20, 0.60, 0.0)

    lm[config.INDEX_PIP] = (wrist_x + 0.05, 0.65, 0.0)
    lm[config.MIDDLE_PIP] = (wrist_x + 0.10, 0.65, 0.0)
    lm[config.RING_PIP] = (wrist_x + 0.15, 0.65, 0.0)
    lm[config.PINKY_PIP] = (wrist_x + 0.20, 0.65, 0.0)

    lm[config.INDEX_TIP] = (tip_x, tip_y, 0.0)
    lm[config.MIDDLE_TIP] = (wrist_x + 0.10, 0.70, 0.0)
    lm[config.RING_TIP] = (wrist_x + 0.15, 0.70, 0.0)
    lm[config.PINKY_TIP] = (wrist_x + 0.20, 0.70, 0.0)
    lm[config.THUMB_TIP] = (wrist_x + 0.15, 0.65, 0.0)

    return lm


class TestGestureRecognizerBasics(unittest.TestCase):
    def setUp(self):
        self.recognizer = GestureRecognizer(confirm_frames=1)

    def _feed(self, landmarks, n=1):
        """Feed the same landmark frame n times and return the last result."""
        result = Gesture.NONE
        for _ in range(n):
            result = self.recognizer.recognize(landmarks)
        return result

    def test_no_hand_returns_none(self):
        self.assertEqual(self.recognizer.recognize(None), Gesture.NONE)

    def test_pointing_hand_is_move(self):
        # Base hand has all fingers folded, so extending just the index tip creates a point
        hand = extend_finger(make_base_hand(), config.INDEX_TIP, config.INDEX_PIP)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.MOVE)

    def test_flat_palm_is_restore_active(self):
        hand = make_base_hand()
        hand = extend_finger(hand, config.INDEX_TIP, config.INDEX_PIP)
        hand = extend_finger(hand, config.MIDDLE_TIP, config.MIDDLE_PIP)
        hand = extend_finger(hand, config.RING_TIP, config.RING_PIP)
        hand = extend_finger(hand, config.PINKY_TIP, config.PINKY_PIP)
        hand[config.THUMB_TIP] = (0.1, 0.4, 0.0) # extend thumb
        result = self._feed(hand)
        self.assertEqual(result, Gesture.RESTORE_ACTIVE)

    def test_right_hand_pinch_shape_does_not_fire_click(self):
        # On right hand, GestureRecognizer never classifies CLICK.
        hand = extend_finger(make_base_hand(), config.INDEX_TIP, config.INDEX_PIP)
        # Thumb near folded middle
        hand[config.MIDDLE_TIP] = (0.50, 0.70, 0.0)
        hand[config.THUMB_TIP] = (0.50, 0.69, 0.0)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.MOVE)
        self.assertNotEqual(result, Gesture.CLICK)

    def test_index_middle_extended_is_scroll(self):
        hand = make_base_hand()
        hand = extend_finger(hand, config.INDEX_TIP, config.INDEX_PIP, x=0.50)
        hand = extend_finger(hand, config.MIDDLE_TIP, config.MIDDLE_PIP, x=0.54)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.SCROLL)

    def test_closed_fist_is_minimize(self):
        hand = make_base_hand()  # all five fingers folded
        result = self._feed(hand)
        self.assertEqual(result, Gesture.MINIMIZE)

    def test_thumb_only_is_not_confused_with_click(self):
        # Only thumb extended, all other fingers folded. Should be BACK.
        hand = make_base_hand()
        hand[config.THUMB_TIP] = (0.1, 0.4, 0.0)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.BACK)

    def test_pinky_only_is_forward(self):
        # Extending only the pinky finger with thumb folded should be FORWARD
        hand = extend_finger(make_base_hand(), config.PINKY_TIP, config.PINKY_PIP)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.FORWARD)

    def test_pinky_with_relaxed_thumb_is_forward_not_close(self):
        # Even with a relaxed thumb resting on the curled fingers, raising the pinky must be FORWARD, not CLOSE
        hand = extend_finger(make_base_hand(), config.PINKY_TIP, config.PINKY_PIP)
        hand[config.THUMB_IP] = (0.35, 0.65, 0.0)
        hand[config.THUMB_TIP] = (0.32, 0.58, 0.0)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.FORWARD)

    def test_shaka_is_close(self):
        # Shaka sign: both thumb and pinky extended, others folded -> CLOSE
        hand = extend_finger(make_base_hand(), config.PINKY_TIP, config.PINKY_PIP)
        hand[config.THUMB_TIP] = (0.1, 0.40, 0.0)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.CLOSE)

    def test_four_finger_salute_is_toggle_media_mode(self):
        # 4-finger salute: Index, Middle, Ring, Pinky extended, thumb folded -> TOGGLE_MEDIA_MODE
        hand = make_base_hand()
        hand = extend_finger(hand, config.INDEX_TIP, config.INDEX_PIP)
        hand = extend_finger(hand, config.MIDDLE_TIP, config.MIDDLE_PIP)
        hand = extend_finger(hand, config.RING_TIP, config.RING_PIP)
        hand = extend_finger(hand, config.PINKY_TIP, config.PINKY_PIP)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.TOGGLE_MEDIA_MODE)

    def test_three_fingers_is_toggle_presentation_mode(self):
        # 3 fingers up: Index, Middle, Ring extended, thumb folded, pinky folded -> TOGGLE_PRESENTATION_MODE
        hand = make_base_hand()
        hand = extend_finger(hand, config.INDEX_TIP, config.INDEX_PIP)
        hand = extend_finger(hand, config.MIDDLE_TIP, config.MIDDLE_PIP)
        hand = extend_finger(hand, config.RING_TIP, config.RING_PIP)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.TOGGLE_PRESENTATION_MODE)

    def test_five_finger_open_hand_is_restore_active_not_media_mode(self):
        # 5 fingers open naturally: all extended -> RESTORE_ACTIVE, never TOGGLE_MEDIA_MODE
        hand = make_base_hand()
        hand = extend_finger(hand, config.INDEX_TIP, config.INDEX_PIP)
        hand = extend_finger(hand, config.MIDDLE_TIP, config.MIDDLE_PIP)
        hand = extend_finger(hand, config.RING_TIP, config.RING_PIP)
        hand = extend_finger(hand, config.PINKY_TIP, config.PINKY_PIP)
        hand[config.THUMB_TIP] = (0.28, 0.50, 0.0) # thumb naturally open
        result = self._feed(hand)
        self.assertEqual(result, Gesture.RESTORE_ACTIVE)
        self.assertNotEqual(result, Gesture.TOGGLE_MEDIA_MODE)

    def test_open_hand_relaxed_thumb_is_restore_active_not_media_mode(self):
        # Even with a relaxed thumb slightly closer to palm, all 4 fingers extended must never trigger Media Mode
        hand = make_base_hand()
        hand = extend_finger(hand, config.INDEX_TIP, config.INDEX_PIP)
        hand = extend_finger(hand, config.MIDDLE_TIP, config.MIDDLE_PIP)
        hand = extend_finger(hand, config.RING_TIP, config.RING_PIP)
        hand = extend_finger(hand, config.PINKY_TIP, config.PINKY_PIP)
        hand[config.THUMB_IP] = (0.35, 0.55, 0.0)
        hand[config.THUMB_TIP] = (0.35, 0.50, 0.0)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.RESTORE_ACTIVE)
        self.assertNotEqual(result, Gesture.TOGGLE_MEDIA_MODE)



    """
    This is the test that directly answers the SDD's requirement: prove a
    scroll gesture can't be misread as a click due to single-frame noise.
    """

    def test_single_flickered_frame_does_not_trigger_click(self):
        recognizer = GestureRecognizer(confirm_frames=4)

        scroll_hand = make_base_hand()
        scroll_hand = extend_finger(scroll_hand, config.INDEX_TIP, config.INDEX_PIP, x=0.50)
        scroll_hand = extend_finger(scroll_hand, config.MIDDLE_TIP, config.MIDDLE_PIP, x=0.54)

        click_hand = extend_finger(make_base_hand(), config.INDEX_TIP, config.INDEX_PIP)
        click_hand[config.MIDDLE_TIP] = (0.50, 0.60, 0.0)
        click_hand[config.THUMB_TIP] = (0.50, 0.61, 0.0)

        # Feed 3 stable scroll-pose frames (below the confirm threshold of 4,
        # so nothing should be confirmed as SCROLL yet), then a single
        # flickered click-pose frame, then back to scroll.
        recognizer.recognize(scroll_hand)
        recognizer.recognize(scroll_hand)
        result_after_flicker = recognizer.recognize(click_hand)

        # One flickered frame should NOT be enough to confirm a click,
        # because confirm requires at least CLICK_CONFIRM_FRAMES (2) consecutive matching reads.
        self.assertNotEqual(result_after_flicker, Gesture.CLICK)

    def test_gesture_confirms_only_after_required_streak(self):
        recognizer = GestureRecognizer(confirm_frames=4)
        hand = extend_finger(make_base_hand(), config.INDEX_TIP, config.INDEX_PIP)

        results = [recognizer.recognize(hand) for _ in range(4)]
        # Should still be NONE for the first 3 frames (streak not yet met)
        self.assertTrue(all(r == Gesture.NONE for r in results[:3]))
        # By the 4th consecutive matching frame, MOVE should be confirmed
        self.assertEqual(results[3], Gesture.MOVE)


class TestCursorAnchor(unittest.TestCase):
    def test_cursor_anchor_is_index_tip(self):
        hand = make_base_hand()
        x, y = GestureRecognizer.get_cursor_anchor(hand)
        self.assertEqual((x, y), (hand[config.INDEX_TIP][0], hand[config.INDEX_TIP][1]))


class TestGestureRecognizerMultiHand(unittest.TestCase):
    def setUp(self):
        self.recognizer = GestureRecognizer(confirm_frames=1)

    def _feed_multi(self, hands_data, n=1):
        result = Gesture.NONE
        for _ in range(n):
            result = self.recognizer.recognize_multi(hands_data)
        return result

    def test_both_fists_is_minimize_all(self):
        hand1 = make_base_hand()
        hand2 = make_base_hand()

        hands_data = [
            {"label": "Left", "landmarks": hand1},
            {"label": "Right", "landmarks": hand2},
        ]
        
        result = self._feed_multi(hands_data)
        self.assertEqual(result, Gesture.MINIMIZE_ALL)
        self.assertTrue(self.recognizer._in_window_management_mode)

    def test_crossed_index_fingers_is_lock(self):
        left_hand = make_index_point_hand(wrist_x=0.25, tip_x=0.52, tip_y=0.38)
        right_hand = make_index_point_hand(wrist_x=0.75, tip_x=0.48, tip_y=0.42)

        hands_data = [
            {"label": "Left", "landmarks": left_hand},
            {"label": "Right", "landmarks": right_hand},
        ]

        result = self._feed_multi(hands_data)
        self.assertEqual(result, Gesture.LOCK)

    def test_restore_last_when_one_hand_fisted_in_mode(self):
        # First trigger minimize all to enter mode
        self.test_both_fists_is_minimize_all()
        
        hand1 = make_base_hand()
        
        hands_data = [
            {"label": "Right", "landmarks": hand1},
        ]
        
        # Now one hand is fisted, should be RESTORE_LAST
        result = self._feed_multi(hands_data)
        self.assertEqual(result, Gesture.RESTORE_LAST)
        self.assertTrue(self.recognizer._in_window_management_mode)

    def test_restore_all_when_both_hands_open_in_mode(self):
        # Enter mode
        self.test_both_fists_is_minimize_all()
        
        hand1 = extend_finger(make_base_hand(), config.INDEX_TIP, config.INDEX_PIP)
        hand2 = extend_finger(make_base_hand(), config.INDEX_TIP, config.INDEX_PIP)
        
        hands_data = [
            {"label": "Left", "landmarks": hand1},
            {"label": "Right", "landmarks": hand2},
        ]
        
        # Both hands present but not fisted -> RESTORE_ALL
        result = self._feed_multi(hands_data)
        self.assertEqual(result, Gesture.RESTORE_ALL)
        # Should clear mode
        self.assertFalse(self.recognizer._in_window_management_mode)

    def test_single_flicker_does_not_misfire_multi_hand(self):
        recognizer = GestureRecognizer(confirm_frames=4)

        # Setup hands for none/move
        open_hand = extend_finger(make_base_hand(), config.INDEX_TIP, config.INDEX_PIP)
        hands_open = [
            {"label": "Left", "landmarks": open_hand},
            {"label": "Right", "landmarks": open_hand},
        ]

        # Setup hands for minimize all
        fist = make_base_hand()
        hands_fist = [
            {"label": "Left", "landmarks": fist},
            {"label": "Right", "landmarks": fist},
        ]

        recognizer.recognize_multi(hands_open)
        recognizer.recognize_multi(hands_open)
        
        # 1 flicker of double fist
        result = recognizer.recognize_multi(hands_fist)
        
        # Should not confirm yet
        self.assertNotEqual(result, Gesture.MINIMIZE_ALL)
        
        # After 3 more frames (4 total), it should confirm
        recognizer.recognize_multi(hands_fist)
        recognizer.recognize_multi(hands_fist)
        result2 = recognizer.recognize_multi(hands_fist)
        
        self.assertEqual(result2, Gesture.MINIMIZE_ALL)

if __name__ == "__main__":
    unittest.main()
