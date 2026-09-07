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

    def test_map_to_screen_clamps_beyond_margin(self):
        # Anything past the margin should clamp to screen boundaries
        x, y = self.mouse.map_to_screen(0.0, 0.0)
        self.assertEqual(x, 0.0)
        self.assertEqual(y, 0.0)

        x, y = self.mouse.map_to_screen(1.0, 1.0)
        self.assertEqual(x, 1920.0)
        self.assertEqual(y, 1080.0)

    def test_map_to_screen_reaches_exact_edges_at_frame_margin(self):
        # Active range is [0.15, 0.85] for FRAME_MARGIN = 0.15
        margin = config.FRAME_MARGIN
        x_min, y_min = self.mouse.map_to_screen(margin, margin)
        self.assertAlmostEqual(x_min, 0.0, delta=1e-5)
        self.assertAlmostEqual(y_min, 0.0, delta=1e-5)

        x_max, y_max = self.mouse.map_to_screen(1.0 - margin, 1.0 - margin)
        self.assertAlmostEqual(x_max, 1920.0, delta=1e-5)
        self.assertAlmostEqual(y_max, 1080.0, delta=1e-5)

    def test_map_to_screen_linear_interpolation(self):
        # 0.50 normalized maps to exact center (50%)
        x_mid, y_mid = self.mouse.map_to_screen(0.5, 0.5)
        self.assertAlmostEqual(x_mid, 960.0, delta=1e-5)
        self.assertAlmostEqual(y_mid, 540.0, delta=1e-5)

        # 0.80 normalized on Y maps to (0.80 - 0.15) / 0.70 = 0.65 / 0.70 * 1080 = 1002.86 px
        _, y_80 = self.mouse.map_to_screen(0.5, 0.80)
        expected_y = ((0.80 - 0.15) / 0.70) * 1080.0
        self.assertAlmostEqual(y_80, expected_y, delta=1e-4)

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
    def test_scroll_calls_pyautogui_with_amount(self, mock_scroll):
        self.mouse.scroll(150)
        mock_scroll.assert_called_once_with(150)

    @patch("gesture_mouse.mouse_control.pyautogui.keyUp")
    @patch("gesture_mouse.mouse_control.pyautogui.scroll")
    @patch("gesture_mouse.mouse_control.pyautogui.keyDown")
    def test_zoom_calls_pyautogui_with_ctrl_and_scroll(self, mock_key_down, mock_scroll, mock_key_up):
        self.mouse.zoom(120)
        mock_key_down.assert_called_once_with('ctrl')
        mock_scroll.assert_called_once_with(120)
        mock_key_up.assert_called_once_with('ctrl')

    @patch("gesture_mouse.mouse_control.ctypes.windll.user32.LockWorkStation")
    def test_lock_screen_uses_windows_api_when_available(self, mock_lock):
        self.mouse.lock_screen()
        mock_lock.assert_called_once()

    @patch("gesture_mouse.mouse_control.pyautogui.hotkey")
    @patch("gesture_mouse.mouse_control.ctypes.windll.user32.LockWorkStation", return_value=0)
    def test_lock_screen_falls_back_to_hotkey_when_windows_api_unavailable(self, mock_lock, mock_hotkey):
        self.mouse.lock_screen()
        mock_lock.assert_called_once()
        mock_hotkey.assert_called_once_with('win', 'l')

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

    # ---- Tests for Cursor Freeze Window (Steady Clicks) ----

    @patch("gesture_mouse.mouse_control.pyautogui.moveTo")
    def test_cursor_position_does_not_change_during_freeze_window(self, mock_move):
        """(a) Cursor position does not change during the freeze window even if coordinates shift."""
        self.mouse.lock_cursor(duration_ms=200)
        self.assertTrue(self.mouse.is_cursor_locked())

        self.mouse.move_cursor(100, 200)
        self.mouse.move_cursor(300, 400)
        mock_move.assert_not_called()

    @patch("gesture_mouse.mouse_control.pyautogui.moveTo")
    def test_cursor_resumes_updating_after_freeze_window_expires(self, mock_move):
        """(b) Cursor resumes updating immediately after the freeze window expires."""
        current_time = 1000.0
        with patch("gesture_mouse.mouse_control.time.time", side_effect=lambda: current_time):
            self.mouse.lock_cursor(duration_ms=200)
            self.assertTrue(self.mouse.is_cursor_locked())

            # Attempt move during lock window
            self.mouse.move_cursor(100, 200)
            mock_move.assert_not_called()

            # Advance time past freeze window (200ms -> 0.2s)
            current_time = 1000.25
            self.assertFalse(self.mouse.is_cursor_locked())

            # Move cursor after expiration
            self.mouse.move_cursor(500, 600)
            mock_move.assert_called_once_with(500, 600)

    @patch("gesture_mouse.mouse_control.pyautogui.click")
    def test_click_fires_correctly_during_freeze_window(self, mock_click):
        """(c) The click itself still fires correctly and isn't blocked or delayed by the freeze logic."""
        self.mouse.lock_cursor(duration_ms=200)
        self.assertTrue(self.mouse.is_cursor_locked())

        self.mouse.click()
        mock_click.assert_called_once()

    @patch("gesture_mouse.mouse_control.pyautogui.moveTo")
    def test_cursor_freeze_disabled_bypasses_feature(self, mock_move):
        """(d) CURSOR_FREEZE_ENABLED=False fully bypasses this feature with zero behavior change."""
        with patch.object(config, "CURSOR_FREEZE_ENABLED", False):
            self.mouse.lock_cursor(duration_ms=200)
            self.assertFalse(self.mouse.is_cursor_locked())

            self.mouse.move_cursor(150, 250)
            mock_move.assert_called_once_with(150, 250)


if __name__ == "__main__":
    unittest.main()


