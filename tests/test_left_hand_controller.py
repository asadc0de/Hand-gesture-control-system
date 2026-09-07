"""
Unit tests for LeftHandController with Thumb+Middle Left Click and Thumb+Ring Right Click.
"""

import unittest
from unittest.mock import MagicMock
import time

from gesture_mouse import config
from gesture_mouse.left_hand_controller import LeftHandController


def make_hand(wrist=(0.5, 0.9, 0.0), thumb_tip=(0.5, 0.7, 0.0),
              index_tip=(0.5, 0.5, 0.0), index_pip=(0.5, 0.65, 0.0),
              middle_tip=(0.6, 0.5, 0.0), middle_pip=(0.6, 0.65, 0.0),
              ring_tip=(0.7, 0.5, 0.0), ring_pip=(0.7, 0.65, 0.0),
              middle_mcp=(0.6, 0.75, 0.0)):
    lm = [(0.5, 0.9, 0.0)] * 21
    lm[config.WRIST] = wrist
    lm[config.THUMB_TIP] = thumb_tip
    lm[config.INDEX_TIP] = index_tip
    lm[config.INDEX_PIP] = index_pip
    lm[config.MIDDLE_TIP] = middle_tip
    lm[config.MIDDLE_PIP] = middle_pip
    lm[config.RING_TIP] = ring_tip
    lm[config.RING_PIP] = ring_pip
    lm[config.MIDDLE_MCP] = middle_mcp
    return lm


class TestLeftHandController(unittest.TestCase):
    def setUp(self):
        self.controller = LeftHandController()
        self.mouse = MagicMock()

    def test_left_click_thumb_middle_tap(self):
        """
        Left Click: Thumb + Middle finger pinch (quick tap).
        """
        pinch_hand = make_hand(
            thumb_tip=(0.50, 0.60, 0.0),
            middle_tip=(0.50, 0.61, 0.0),    # mid_dist = 0.010 < CLICK_PINCH_THRESHOLD (0.055)
            ring_tip=(0.70, 0.40, 0.0)       # ring far away
        )
        open_hand = make_hand(
            thumb_tip=(0.20, 0.60, 0.0),
            middle_tip=(0.50, 0.30, 0.0),
            ring_tip=(0.70, 0.30, 0.0)
        )

        # Frame 1: Pinch down
        self.controller.process_hand(pinch_hand, False, False, self.mouse)
        self.assertTrue(self.controller.left_middle_pinched)
        self.assertFalse(self.controller.left_ring_pinched)
        self.mouse.lock_cursor.assert_called_once()
        self.mouse.click.assert_not_called()

        # Frame 2: Release
        self.controller.process_hand(open_hand, False, False, self.mouse)
        self.assertFalse(self.controller.left_middle_pinched)
        self.mouse.click.assert_called_once()
        self.mouse.right_click.assert_not_called()

    def test_right_click_thumb_ring_tap(self):
        """
        Right Click: Thumb + Ring finger pinch (quick tap).
        """
        pinch_hand = make_hand(
            thumb_tip=(0.60, 0.60, 0.0),
            middle_tip=(0.40, 0.30, 0.0),    # middle far away
            ring_tip=(0.60, 0.61, 0.0)       # ring_dist = 0.010 < RIGHT_CLICK_PINCH_THRESHOLD (0.060)
        )
        open_hand = make_hand(
            thumb_tip=(0.20, 0.60, 0.0),
            middle_tip=(0.40, 0.30, 0.0),
            ring_tip=(0.70, 0.30, 0.0)
        )

        # Frame 1: Pinch down
        self.controller.process_hand(pinch_hand, False, False, self.mouse)
        self.assertFalse(self.controller.left_middle_pinched)
        self.assertTrue(self.controller.left_ring_pinched)
        self.mouse.lock_cursor.assert_called_once()
        self.mouse.right_click.assert_not_called()

        # Frame 2: Release
        self.controller.process_hand(open_hand, False, False, self.mouse)
        self.assertFalse(self.controller.left_ring_pinched)
        self.mouse.right_click.assert_called_once()
        self.mouse.click.assert_not_called()

    def test_ambiguous_simultaneous_pinch_fires_only_left_click(self):
        """
        Ambiguous case: Thumb touches BOTH middle and ring fingertips simultaneously.
        Exclusivity ensures ONLY left click is initiated, NEVER right click.
        """
        simultaneous_hand = make_hand(
            thumb_tip=(0.50, 0.60, 0.0),
            middle_tip=(0.50, 0.60, 0.0),    # mid_dist = 0.000 < 0.055
            ring_tip=(0.50, 0.60, 0.0)       # ring_dist = 0.000 < 0.060
        )
        open_hand = make_hand(
            thumb_tip=(0.20, 0.60, 0.0),
            middle_tip=(0.50, 0.30, 0.0),
            ring_tip=(0.70, 0.30, 0.0)
        )

        # Frame 1: Pinch down
        self.controller.process_hand(simultaneous_hand, False, False, self.mouse)
        self.assertTrue(self.controller.left_middle_pinched)
        self.assertFalse(self.controller.left_ring_pinched)
        self.mouse.lock_cursor.assert_called_once()

        # Frame 2: Release
        self.controller.process_hand(open_hand, False, False, self.mouse)
        self.assertFalse(self.controller.left_middle_pinched)
        self.mouse.click.assert_called_once()
        self.mouse.right_click.assert_not_called()

    def test_two_taps_fire_two_clicks_for_native_double_click(self):
        """
        Two rapid Thumb + Middle taps invoke mouse.click() exactly twice.
        """
        pinch_hand = make_hand(
            thumb_tip=(0.50, 0.60, 0.0),
            middle_tip=(0.50, 0.61, 0.0),
            ring_tip=(0.70, 0.30, 0.0)
        )
        open_hand = make_hand(
            thumb_tip=(0.20, 0.60, 0.0),
            middle_tip=(0.50, 0.30, 0.0),
            ring_tip=(0.70, 0.30, 0.0)
        )

        # Tap 1
        self.controller.process_hand(pinch_hand, False, False, self.mouse)
        self.controller.process_hand(open_hand, False, False, self.mouse)
        self.assertEqual(self.mouse.click.call_count, 1)

        # Tap 2
        self.controller.process_hand(pinch_hand, False, False, self.mouse)
        self.controller.process_hand(open_hand, False, False, self.mouse)
        self.assertEqual(self.mouse.click.call_count, 2)
        self.mouse.right_click.assert_not_called()

    def test_sustained_pinch_promotes_to_drag(self):
        """
        Thumb + Middle held > TAP_HOLD_MAX_MS (250ms) enters drag and ends on release.
        """
        pinch_hand = make_hand(
            thumb_tip=(0.50, 0.60, 0.0),
            middle_tip=(0.50, 0.61, 0.0),
            ring_tip=(0.70, 0.30, 0.0)
        )
        open_hand = make_hand(
            thumb_tip=(0.20, 0.60, 0.0),
            middle_tip=(0.50, 0.30, 0.0),
            ring_tip=(0.70, 0.30, 0.0)
        )

        # Pinch down
        self.controller.process_hand(pinch_hand, False, False, self.mouse)
        self.assertTrue(self.controller.left_middle_pinched)
        self.assertFalse(self.controller.left_is_dragging)

        # Hold > TAP_HOLD_MAX_MS
        self.controller.left_middle_pinch_start = time.time() - 0.300
        self.controller.process_hand(pinch_hand, False, False, self.mouse)
        
        self.assertTrue(self.controller.left_is_dragging)
        self.mouse.start_drag.assert_called_once()
        self.mouse.click.assert_not_called()

        # Release
        self.controller.process_hand(open_hand, False, False, self.mouse)
        self.assertFalse(self.controller.left_is_dragging)
        self.assertFalse(self.controller.left_middle_pinched)
        self.mouse.end_drag.assert_called_once()
        self.mouse.click.assert_not_called()

    def test_sustained_pinch_with_one_frame_distance_jitter(self):
        """
        Test A: Sustained pinch with one-frame distance jitter (< release threshold)
        -> no false click
        -> drag still starts after 250ms
        """
        pinch_entry = make_hand(thumb_tip=(0.50, 0.60, 0.0), middle_tip=(0.50, 0.61, 0.0))  # dist = 0.010 < 0.055
        pinch_jitter = make_hand(thumb_tip=(0.50, 0.60, 0.0), middle_tip=(0.50, 0.665, 0.0)) # dist = 0.065 (0.055 < 0.065 < 0.075)
        
        t0 = 1000.0
        # Frame 1: Pinch start (t = 0ms)
        with unittest.mock.patch('time.time', return_value=t0):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        self.assertTrue(self.controller.left_middle_pinched)
        self.assertFalse(self.controller.left_is_dragging)

        # Frame 2: Jitter frame at t = 130ms
        with unittest.mock.patch('time.time', return_value=t0 + 0.130):
            self.controller.process_hand(pinch_jitter, False, False, self.mouse)
        self.assertTrue(self.controller.left_middle_pinched)
        self.assertFalse(self.controller.left_is_dragging)
        self.mouse.click.assert_not_called()

        # Frame 3: Hold crossed 250ms at t = 260ms
        with unittest.mock.patch('time.time', return_value=t0 + 0.260):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        self.assertTrue(self.controller.left_is_dragging)
        self.mouse.start_drag.assert_called_once()
        self.mouse.click.assert_not_called()

    def test_active_drag_with_one_frame_distance_spike(self):
        """
        Test B: Active drag with one-frame distance spike (< release threshold)
        -> drag remains active
        -> no end_drag()
        """
        pinch_entry = make_hand(thumb_tip=(0.50, 0.60, 0.0), middle_tip=(0.50, 0.61, 0.0))
        pinch_jitter = make_hand(thumb_tip=(0.50, 0.60, 0.0), middle_tip=(0.50, 0.665, 0.0)) # dist = 0.065

        t0 = 1000.0
        with unittest.mock.patch('time.time', return_value=t0):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        with unittest.mock.patch('time.time', return_value=t0 + 0.300):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        self.assertTrue(self.controller.left_is_dragging)

        # Distance spike during active drag
        with unittest.mock.patch('time.time', return_value=t0 + 0.330):
            self.controller.process_hand(pinch_jitter, False, False, self.mouse)
        self.assertTrue(self.controller.left_is_dragging)
        self.mouse.end_drag.assert_not_called()

    def test_genuine_sustained_release(self):
        """
        Test C & H: Genuine sustained release (dist >= release threshold)
        -> exactly one end_drag()
        """
        pinch_entry = make_hand(thumb_tip=(0.50, 0.60, 0.0), middle_tip=(0.50, 0.61, 0.0))
        open_hand = make_hand(thumb_tip=(0.20, 0.60, 0.0), middle_tip=(0.50, 0.30, 0.0)) # dist = 0.424 >= 0.075

        t0 = 1000.0
        with unittest.mock.patch('time.time', return_value=t0):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        with unittest.mock.patch('time.time', return_value=t0 + 0.300):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        self.assertTrue(self.controller.left_is_dragging)

        # Release
        with unittest.mock.patch('time.time', return_value=t0 + 0.330):
            self.controller.process_hand(open_hand, False, False, self.mouse)
        self.assertFalse(self.controller.left_is_dragging)
        self.assertFalse(self.controller.left_middle_pinched)
        self.assertEqual(self.mouse.end_drag.call_count, 1)

    def test_quick_pinch_fires_one_click_and_no_start_drag(self):
        """
        Test D: Quick pinch (< 250ms)
        -> exactly one click
        -> no start_drag()
        """
        pinch_entry = make_hand(thumb_tip=(0.50, 0.60, 0.0), middle_tip=(0.50, 0.61, 0.0))
        open_hand = make_hand(thumb_tip=(0.20, 0.60, 0.0), middle_tip=(0.50, 0.30, 0.0))

        t0 = 1000.0
        # Pinch at t = 0ms
        with unittest.mock.patch('time.time', return_value=t0):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        # Release at t = 100ms
        with unittest.mock.patch('time.time', return_value=t0 + 0.100):
            self.controller.process_hand(open_hand, False, False, self.mouse)

        self.assertEqual(self.mouse.click.call_count, 1)
        self.mouse.start_drag.assert_not_called()
        self.mouse.end_drag.assert_not_called()

    def test_one_frame_tracking_loss_during_drag(self):
        """
        Test E: One-frame left-hand tracking loss during drag
        -> drag remains active
        """
        pinch_entry = make_hand(thumb_tip=(0.50, 0.60, 0.0), middle_tip=(0.50, 0.61, 0.0))

        t0 = 1000.0
        with unittest.mock.patch('time.time', return_value=t0):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        with unittest.mock.patch('time.time', return_value=t0 + 0.300):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        self.assertTrue(self.controller.left_is_dragging)

        # 1-frame tracking dropout (landmarks is None)
        self.controller.process_hand(None, False, False, self.mouse)
        self.assertTrue(self.controller.left_is_dragging)
        self.mouse.end_drag.assert_not_called()

        # Resumed tracking on next frame
        with unittest.mock.patch('time.time', return_value=t0 + 0.360):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        self.assertTrue(self.controller.left_is_dragging)
        self.mouse.end_drag.assert_not_called()

    def test_two_consecutive_frames_tracking_loss_safely_ends_drag(self):
        """
        Test F: Two+ consecutive frames of left-hand loss
        -> active drag safely ends/resets
        """
        pinch_entry = make_hand(thumb_tip=(0.50, 0.60, 0.0), middle_tip=(0.50, 0.61, 0.0))

        t0 = 1000.0
        with unittest.mock.patch('time.time', return_value=t0):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        with unittest.mock.patch('time.time', return_value=t0 + 0.300):
            self.controller.process_hand(pinch_entry, False, False, self.mouse)
        self.assertTrue(self.controller.left_is_dragging)

        # Frame 1 missing
        self.controller.process_hand(None, False, False, self.mouse)
        self.assertTrue(self.controller.left_is_dragging)

        # Frame 2 missing -> triggers reset
        self.controller.process_hand(None, False, False, self.mouse)
        self.assertFalse(self.controller.left_is_dragging)
        self.assertFalse(self.controller.left_middle_pinched)
        self.mouse.end_drag.assert_called_once()

    def test_start_drag_called_exactly_once_during_sustained_hold(self):
        """
        Test G: start_drag() is called exactly once during sustained hold
        """
        pinch_entry = make_hand(thumb_tip=(0.50, 0.60, 0.0), middle_tip=(0.50, 0.61, 0.0))

        t0 = 1000.0
        for i in range(15):
            with unittest.mock.patch('time.time', return_value=t0 + i * 0.033):
                self.controller.process_hand(pinch_entry, False, False, self.mouse)

        self.assertEqual(self.mouse.start_drag.call_count, 1)
        self.assertTrue(self.controller.left_is_dragging)


if __name__ == "__main__":
    unittest.main(verbosity=2)
