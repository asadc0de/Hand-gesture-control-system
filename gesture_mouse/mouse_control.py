"""
MouseControlAPI module.
The only class that touches PyAutoGUI / the operating system's mouse. Every
other class stays blissfully unaware that a real mouse exists, which is
what makes it possible to unit test them with a fake/mock version of this
class instead of actually moving your cursor during tests.
"""

import ctypes
import sys
import pyautogui
import time
from gesture_mouse import config

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


class MouseControlAPI:
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self._dragging = False
        self._cursor_locked_until = 0.0

    def lock_cursor(self, duration_ms: float = None):
        """Activates cursor lock for duration_ms (defaults to config.CURSOR_FREEZE_DURATION_MS)."""
        if not getattr(config, "CURSOR_FREEZE_ENABLED", True):
            return
        if duration_ms is None:
            duration_ms = getattr(config, "CURSOR_FREEZE_DURATION_MS", 200)
        self._cursor_locked_until = time.time() + (duration_ms / 1000.0)

    def is_cursor_locked(self) -> bool:
        """Returns True if the cursor freeze window is currently active."""
        if not getattr(config, "CURSOR_FREEZE_ENABLED", True):
            return False
        return time.time() < self._cursor_locked_until

    def unlock_cursor(self):
        """Explicitly releases the cursor lock."""
        self._cursor_locked_until = 0.0

    def map_to_screen(self, norm_x: float, norm_y: float):
        """
        Maps normalized coordinates [0.0, 1.0] to full screen pixel dimensions.
        Active range is [FRAME_MARGIN, 1.0 - FRAME_MARGIN].
        Coordinates outside the active range are clamped smoothly.
        """
        margin = getattr(config, "FRAME_MARGIN", 0.15)
        span = 1.0 - 2.0 * margin
        if span <= 0:
            return 0.0, 0.0

        clamped_x = max(margin, min(1.0 - margin, float(norm_x)))
        clamped_y = max(margin, min(1.0 - margin, float(norm_y)))

        sx = (clamped_x - margin) * self.screen_width / span
        sy = (clamped_y - margin) * self.screen_height / span

        sx = max(0.0, min(float(self.screen_width), sx))
        sy = max(0.0, min(float(self.screen_height), sy))

        return sx, sy

    def move_cursor(self, screen_x: float, screen_y: float):
        if not self.is_cursor_locked():
            pyautogui.moveTo(int(screen_x), int(screen_y))

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

    def lock_screen(self):
        if sys.platform.startswith("win"):
            try:
                user32 = ctypes.windll.user32
                if hasattr(user32, "LockWorkStation"):
                    result = user32.LockWorkStation()
                    if result:
                        return
            except (AttributeError, OSError):
                pass

        pyautogui.hotkey('win', 'l')

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