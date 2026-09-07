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


if __name__ == "__main__":
    unittest.main(verbosity=2)
