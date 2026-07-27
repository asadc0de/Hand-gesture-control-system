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
import time
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
        margin = 60
        
        x = max(margin, min(640 - margin, int(norm_x * 640)))
        y = max(margin, min(480 - margin, int(norm_y * 480)))
        
        sx = (x - margin) * self.screen_width / (640 - 2 * margin)
        sy = (y - margin) * self.screen_height / (480 - 2 * margin)
        
        return sx, sy

    def _smooth(self, target_x: float, target_y: float):
        if self._smoothed_x is None:
            self._smoothed_x, self._smoothed_y = target_x, target_y
            return target_x, target_y

        alpha = 0.25
        self._smoothed_x = alpha * target_x + (1 - alpha) * self._smoothed_x
        self._smoothed_y = alpha * target_y + (1 - alpha) * self._smoothed_y
        return self._smoothed_x, self._smoothed_y

    def move_cursor(self, screen_x: float, screen_y: float):
        smooth_x, smooth_y = self._smooth(screen_x, screen_y)

        try:
            pyautogui.moveTo(smooth_x, smooth_y, _pause=False)
        except pyautogui.FailSafeException:
            print("Warning: cursor got too close to a screen corner, move skipped.")

    def click(self):
        pyautogui.click()

    def right_click(self):
        pyautogui.rightClick()

    def back(self):
        pyautogui.keyDown('alt')
        pyautogui.press('left')
        pyautogui.keyUp('alt')

    def forward(self):
        pyautogui.keyDown('alt')
        pyautogui.press('right')
        pyautogui.keyUp('alt')

    def double_click(self):
        pyautogui.doubleClick()

    def close_window(self):
        pyautogui.keyDown('alt')
        pyautogui.press('f4')
        pyautogui.keyUp('alt')

    def take_screenshot(self):
        filename = f"screenshot_{int(time.time())}.png"
        pyautogui.screenshot(filename)
        print(f"Screenshot saved to {filename}")

    def scroll(self, amount: int):
        pyautogui.scroll(amount)

    def next_slide(self):
        pyautogui.press('right')

    def prev_slide(self):
        pyautogui.press('left')

    def zoom(self, amount: int):
        pyautogui.keyDown('ctrl')
        pyautogui.scroll(amount)
        pyautogui.keyUp('ctrl')

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