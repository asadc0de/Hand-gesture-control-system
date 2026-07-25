"""
MouseControlAPI module.
The only class that touches PyAutoGUI / the operating system's mouse. Every
other class stays blissfully unaware that a real mouse exists, which is
what makes it possible to unit test them with a fake/mock version of this
class instead of actually moving your cursor during tests.
"""

import platform
import pyautogui
import ctypes
from gesture_mouse import config

# Safety: moving the mouse to a screen corner aborts the script. Useful
# during development, harmless in normal use.
pyautogui.FAILSAFE = True
# Removes PyAutoGUI's default 0.1s pause after every call - we handle our
# own frame-rate pacing in the main loop instead.
pyautogui.PAUSE = 0


class MouseControlAPI:
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self._dragging = False

    def map_to_screen(self, norm_x: float, norm_y: float):
        """
        Maps a normalized (0-1) hand coordinate to actual screen pixels.

        Two things happen here, in order:
        1. Margin crop: only the central region of the camera frame (see
           config.FRAME_MARGIN) maps to the screen, so reaching screen edges
           doesn't require stretching your hand to the very edge of the
           webcam view.
        2. Sensitivity gain: movement is amplified around the center point
           (config.CURSOR_SENSITIVITY), the same way a real mouse has
           acceleration - a small hand movement near center still moves the
           cursor a little, but the same movement further from center covers
           a lot more screen. This is what makes it feel like a mouse
           instead of a 1:1 tracing pad.
        """
        margin = config.FRAME_MARGIN
        usable_range = 1 - 2 * margin

        clamped_x = min(max(norm_x - margin, 0), usable_range) / usable_range
        clamped_y = min(max(norm_y - margin, 0), usable_range) / usable_range

        gain = config.CURSOR_SENSITIVITY
        gained_x = min(max(0.5 + (clamped_x - 0.5) * gain, 0), 1)
        gained_y = min(max(0.5 + (clamped_y - 0.5) * gain, 0), 1)

        screen_x = gained_x * self.screen_width
        screen_y = gained_y * self.screen_height

        buffer = config.SCREEN_EDGE_BUFFER_PX
        screen_x = min(max(screen_x, buffer), self.screen_width - buffer)
        screen_y = min(max(screen_y, buffer), self.screen_height - buffer)

        return screen_x, screen_y

    def move_cursor(self, screen_x: float, screen_y: float):
        try:
            pyautogui.moveTo(screen_x, screen_y)
        except pyautogui.FailSafeException:
            # Should be rare now that map_to_screen keeps us off the exact
            # corner pixel, but if it ever happens, warn instead of crashing
            # the whole demo.
            print("Warning: cursor got too close to a screen corner, move skipped.")

    def click(self):
        pyautogui.click()

    def right_click(self):
        pyautogui.rightClick()

    def scroll(self, direction: str):
        """direction: 'up' or 'down'."""
        amount = config.SCROLL_AMOUNT if direction == "up" else -config.SCROLL_AMOUNT
        pyautogui.scroll(amount)

    def start_drag(self):
        if not self._dragging:
            pyautogui.mouseDown()
            self._dragging = True

    def end_drag(self):
        if self._dragging:
            pyautogui.mouseUp()
            self._dragging = False

    def is_dragging(self) -> bool:
        return self._dragging



