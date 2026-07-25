"""
Unit tests for MouseControlAPI.

PyAutoGUI needs a real display to actually move a cursor, which this
sandbox doesn't have. So every OS-level call is mocked - these tests check
that MouseControlAPI calls PyAutoGUI correctly and does its coordinate math
right, without ever touching a real mouse. That's the same technique
you'll want if you ever run this in CI.
"""

import unittest
from unittest.mock import patch, MagicMock

with patch("pyautogui.size", return_value=(1920, 1080)):
    from gesture_mouse.mouse_control import MouseControlAPI
from gesture_mouse import config


class TestMouseControlAPI(unittest.TestCase):
    def setUp(self):
        with patch("pyautogui.size", return_value=(1920, 1080)):
            self.mouse = MouseControlAPI()

    def test_map_to_screen_center(self):
        x, y = self.mouse.map_to_screen(0.5, 0.5)
        self.assertAlmostEqual(x, 960, delta=1)
        self.assertAlmostEqual(y, 540, delta=1)

    def test_sensitivity_gain_amplifies_movement_away_from_center(self):
        # A small offset from center should map to a noticeably larger
        # fraction of the screen than a plain 1:1 mapping would give,
        # because CURSOR_SENSITIVITY > 1 amplifies deviation from center.
        x, _ = self.mouse.map_to_screen(0.6, 0.5)  # slightly right of center

        margin = config.FRAME_MARGIN
        usable_range = 1 - 2 * margin
        one_to_one_x = ((0.6 - margin) / usable_range) * 1920

        # With gain > 1, the amplified result should land further from
        # center than the plain 1:1 mapping would.
        self.assertGreater(abs(x - 960), abs(one_to_one_x - 960))

    def test_map_to_screen_clamps_beyond_margin(self):
        # Anything past the margin should clamp near the screen edge, but
        # never the exact corner pixel (that would trip PyAutoGUI's failsafe).
        buffer = config.SCREEN_EDGE_BUFFER_PX
        x, y = self.mouse.map_to_screen(0.0, 0.0)
        self.assertEqual(x, buffer)
        self.assertEqual(y, buffer)

        x, y = self.mouse.map_to_screen(1.0, 1.0)
        self.assertEqual(x, 1920 - buffer)
        self.assertEqual(y, 1080 - buffer)

    @patch("gesture_mouse.mouse_control.pyautogui.moveTo")
    def test_move_cursor_calls_pyautogui(self, mock_move):
        self.mouse.move_cursor(100, 200)
        mock_move.assert_called_once_with(100, 200)

    @patch("gesture_mouse.mouse_control.pyautogui.click")
    def test_click_calls_pyautogui(self, mock_click):
        self.mouse.click()
        mock_click.assert_called_once()

    @patch("gesture_mouse.mouse_control.pyautogui.rightClick")
    def test_right_click_calls_pyautogui(self, mock_right_click):
        self.mouse.right_click()
        mock_right_click.assert_called_once()

    @patch("gesture_mouse.mouse_control.pyautogui.scroll")
    def test_scroll_up_uses_positive_amount(self, mock_scroll):
        self.mouse.scroll("up")
        mock_scroll.assert_called_once_with(config.SCROLL_AMOUNT)

    @patch("gesture_mouse.mouse_control.pyautogui.scroll")
    def test_scroll_down_uses_negative_amount(self, mock_scroll):
        self.mouse.scroll("down")
        mock_scroll.assert_called_once_with(-config.SCROLL_AMOUNT)

    @patch("gesture_mouse.mouse_control.pyautogui.mouseUp")
    @patch("gesture_mouse.mouse_control.pyautogui.mouseDown")
    def test_drag_start_and_end_toggles_state(self, mock_down, mock_up):
        self.assertFalse(self.mouse.is_dragging())

        self.mouse.start_drag()
        mock_down.assert_called_once()
        self.assertTrue(self.mouse.is_dragging())

        # calling start_drag again while already dragging shouldn't fire mouseDown twice
        self.mouse.start_drag()
        mock_down.assert_called_once()

        self.mouse.end_drag()
        mock_up.assert_called_once()
        self.assertFalse(self.mouse.is_dragging())

    @patch("gesture_mouse.mouse_control.ctypes")
    @patch("gesture_mouse.mouse_control.platform.system", return_value="Windows")
    def test_minimize_uses_windows_api(self, mock_system, mock_ctypes):
        mock_hwnd = MagicMock()
        mock_ctypes.windll.user32.GetForegroundWindow.return_value = mock_hwnd
        self.mouse.minimize_active_window()
        mock_ctypes.windll.user32.GetForegroundWindow.assert_called_once()
        mock_ctypes.windll.user32.ShowWindow.assert_called_once_with(mock_hwnd, 6)


if __name__ == "__main__":
    unittest.main()


