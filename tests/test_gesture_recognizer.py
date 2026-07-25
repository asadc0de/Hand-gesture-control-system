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

    # MCP joints (knuckles), roughly level
    for mcp in (config.THUMB_MCP, config.INDEX_MCP, config.MIDDLE_MCP,
                config.RING_MCP, config.PINKY_MCP):
        lm[mcp] = (0.5, 0.60, 0.0)

    # PIP joints
    for pip in (config.INDEX_PIP, config.MIDDLE_PIP, config.RING_PIP, config.PINKY_PIP):
        lm[pip] = (0.5, 0.65, 0.0)

    # folded tips: y greater than pip -> curled toward palm
    lm[config.INDEX_TIP] = (0.52, 0.70, 0.0)
    lm[config.MIDDLE_TIP] = (0.54, 0.70, 0.0)
    lm[config.RING_TIP] = (0.56, 0.70, 0.0)
    lm[config.PINKY_TIP] = (0.58, 0.70, 0.0)
    lm[config.THUMB_TIP] = (0.35, 0.62, 0.0)  # thumb tucked, far from other tips

    return lm


def extend_finger(lm, tip_idx, pip_idx, x=None):
    """Returns a copy of lm with the given finger pointing up (extended)."""
    lm = list(lm)
    px = x if x is not None else lm[tip_idx][0]
    lm[tip_idx] = (px, 0.35, 0.0)  # well above its pip -> extended
    return lm


class TestGestureRecognizerBasics(unittest.TestCase):
    def setUp(self):
        self.recognizer = GestureRecognizer(confirm_frames=1, drag_hold_frames=3)

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
        result = self._feed(hand)
        self.assertEqual(result, Gesture.RESTORE_ACTIVE)

    def test_thumb_index_pinch_is_click(self):
        hand = make_base_hand()
        # move thumb tip right next to index tip
        hand[config.THUMB_TIP] = (
            hand[config.INDEX_TIP][0] + 0.01,
            hand[config.INDEX_TIP][1] + 0.01,
            0.0,
        )
        result = self._feed(hand)
        self.assertEqual(result, Gesture.CLICK)

    def test_thumb_pinky_pinch_is_right_click(self):
        hand = make_base_hand()
        hand[config.THUMB_TIP] = (
            hand[config.PINKY_TIP][0] + 0.01,
            hand[config.PINKY_TIP][1] + 0.01,
            0.0,
        )
        result = self._feed(hand)
        self.assertEqual(result, Gesture.RIGHT_CLICK)

    def test_index_middle_extended_enables_scroll_mode(self):
        hand = make_base_hand()
        hand = extend_finger(hand, config.INDEX_TIP, config.INDEX_PIP, x=0.50)
        hand = extend_finger(hand, config.MIDDLE_TIP, config.MIDDLE_PIP, x=0.54)

        # first frame just establishes the reference position (no prior y yet)
        self.recognizer.recognize(hand)

        # second frame: move the hand up -> should register as SCROLL_UP
        hand_moved_up = list(hand)
        hand_moved_up[config.INDEX_TIP] = (0.50, 0.30, 0.0)  # y decreased = moved up
        result = self.recognizer.recognize(hand_moved_up)
        self.assertEqual(result, Gesture.SCROLL_UP)

    def test_sustained_pinch_becomes_drag_not_repeated_clicks(self):
        hand = make_base_hand()
        hand[config.THUMB_TIP] = (
            hand[config.INDEX_TIP][0] + 0.01,
            hand[config.INDEX_TIP][1] + 0.01,
            0.0,
        )
        recognizer = GestureRecognizer(confirm_frames=1, drag_hold_frames=3)
        results = [recognizer.recognize(hand) for _ in range(5)]
        # first couple of frames read as CLICK, then it should escalate to DRAG
        self.assertEqual(results[0], Gesture.CLICK)
        self.assertEqual(results[-1], Gesture.DRAG)

    def test_closed_fist_is_minimize(self):
        hand = make_base_hand()  # already has all four fingers folded
        # thumb tucked away from other fingertips, NOT pinched to index
        hand[config.THUMB_TIP] = (0.30, 0.55, 0.0)
        result = self._feed(hand)
        self.assertEqual(result, Gesture.MINIMIZE)

    def test_fist_is_not_confused_with_click(self):
        # Same folded fingers as a fist, but thumb IS pinched to index tip -
        # this must stay CLICK, not get swallowed by the fist check.
        hand = make_base_hand()
        hand[config.THUMB_TIP] = (
            hand[config.INDEX_TIP][0] + 0.01,
            hand[config.INDEX_TIP][1] + 0.01,
            0.0,
        )
        result = self._feed(hand)
        self.assertEqual(result, Gesture.CLICK)


    """
    This is the test that directly answers the SDD's requirement: prove a
    scroll gesture can't be misread as a click due to single-frame noise.
    """

    def test_single_flickered_frame_does_not_trigger_click(self):
        recognizer = GestureRecognizer(confirm_frames=4, drag_hold_frames=10)

        scroll_hand = make_base_hand()
        scroll_hand = extend_finger(scroll_hand, config.INDEX_TIP, config.INDEX_PIP, x=0.50)
        scroll_hand = extend_finger(scroll_hand, config.MIDDLE_TIP, config.MIDDLE_PIP, x=0.54)

        click_hand = make_base_hand()
        click_hand[config.THUMB_TIP] = (
            click_hand[config.INDEX_TIP][0] + 0.01,
            click_hand[config.INDEX_TIP][1] + 0.01,
            0.0,
        )

        # Feed 3 stable scroll-pose frames (below the confirm threshold of 4,
        # so nothing should be confirmed as SCROLL yet), then a single
        # flickered click-pose frame, then back to scroll.
        recognizer.recognize(scroll_hand)
        recognizer.recognize(scroll_hand)
        result_after_flicker = recognizer.recognize(click_hand)

        # One flickered frame should NOT be enough to confirm a click,
        # because confirm_frames=4 requires 4 consecutive matching reads.
        self.assertNotEqual(result_after_flicker, Gesture.CLICK)

    def test_gesture_confirms_only_after_required_streak(self):
        recognizer = GestureRecognizer(confirm_frames=4, drag_hold_frames=10)
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
        self.recognizer = GestureRecognizer(confirm_frames=1, drag_hold_frames=3)

    def _feed_multi(self, hands_data, n=1):
        result = Gesture.NONE
        for _ in range(n):
            result = self.recognizer.recognize_multi(hands_data)
        return result

    def test_both_fists_is_minimize_all(self):
        hand1 = make_base_hand()
        hand1[config.THUMB_TIP] = (0.30, 0.55, 0.0)
        hand2 = make_base_hand()
        hand2[config.THUMB_TIP] = (0.30, 0.55, 0.0)

        hands_data = [
            {"label": "Left", "landmarks": hand1},
            {"label": "Right", "landmarks": hand2},
        ]
        
        result = self._feed_multi(hands_data)
        self.assertEqual(result, Gesture.MINIMIZE_ALL)
        self.assertTrue(self.recognizer._in_window_management_mode)

    def test_restore_last_when_one_hand_fisted_in_mode(self):
        # First trigger minimize all to enter mode
        self.test_both_fists_is_minimize_all()
        
        hand1 = make_base_hand()
        hand1[config.THUMB_TIP] = (0.30, 0.55, 0.0)
        
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
        recognizer = GestureRecognizer(confirm_frames=4, drag_hold_frames=10)

        # Setup hands for none/move
        open_hand = extend_finger(make_base_hand(), config.INDEX_TIP, config.INDEX_PIP)
        hands_open = [
            {"label": "Left", "landmarks": open_hand},
            {"label": "Right", "landmarks": open_hand},
        ]

        # Setup hands for minimize all
        fist = make_base_hand()
        fist[config.THUMB_TIP] = (0.30, 0.55, 0.0)
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
