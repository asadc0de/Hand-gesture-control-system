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

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


class MouseControlAPI:
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self._dragging = False
        # last SMOOTHED position, used as the baseline for exponential
        # smoothing every frame. None until the first frame arrives.
        self._smoothed_x = None
        self._smoothed_y = None

    def map_to_screen(self, norm_x: float, norm_y: float):
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

    def _smooth(self, target_x: float, target_y: float):
        """
        Exponential moving average. SMOOTHING_FACTOR close to 1 = snappy
        and jittery, close to 0 = smooth but laggy. 0.4-0.6 is usually the
        sweet spot for hand tracking. Add SMOOTHING_FACTOR to config.py if
        it's not there yet.
        """
        if self._smoothed_x is None:
            self._smoothed_x, self._smoothed_y = target_x, target_y
            return target_x, target_y

        factor = config.SMOOTHING_FACTOR
        self._smoothed_x += (target_x - self._smoothed_x) * factor
        self._smoothed_y += (target_y - self._smoothed_y) * factor
        return self._smoothed_x, self._smoothed_y

    def move_cursor(self, screen_x: float, screen_y: float):
        # dead zone: ignore movement smaller than a few pixels so a
        # perfectly still hand doesn't create phantom drift
        if self._smoothed_x is not None:
            dx = screen_x - self._smoothed_x
            dy = screen_y - self._smoothed_y
            if (dx ** 2 + dy ** 2) ** 0.5 < config.CURSOR_DEAD_ZONE_PX:
                return

        smooth_x, smooth_y = self._smooth(screen_x, screen_y)

        try:
            pyautogui.moveTo(smooth_x, smooth_y)
        except pyautogui.FailSafeException:
            print("Warning: cursor got too close to a screen corner, move skipped.")

    def click(self):
        pyautogui.click()

    def right_click(self):
        pyautogui.rightClick()

    def back(self):
        pyautogui.hotkey('browserback')

    def forward(self):
        pyautogui.hotkey('browserforward')

    def scroll(self, amount: int):
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