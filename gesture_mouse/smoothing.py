"""
Smoothing module.
A tiny exponential moving average filter. Raw MediaPipe landmark coordinates
jitter frame to frame even when your hand is dead still, which makes the
cursor shake. This filter is what turns a shaky cursor into a smooth one -
it's a small addition but it's the single biggest visible quality upgrade
you can make to the demo.
"""

from gesture_mouse import config


class ExponentialSmoother:
    def __init__(self, smoothing_factor: float = config.SMOOTHING_FACTOR):
        if not 0 <= smoothing_factor < 1:
            raise ValueError("smoothing_factor must be in [0, 1)")
        self.alpha = smoothing_factor
        self._prev_x = None
        self._prev_y = None

    def smooth(self, x: float, y: float):
        """Returns a smoothed (x, y). First call just passes the value through."""
        if self._prev_x is None:
            self._prev_x, self._prev_y = x, y
            return x, y

        smoothed_x = self.alpha * self._prev_x + (1 - self.alpha) * x
        smoothed_y = self.alpha * self._prev_y + (1 - self.alpha) * y

        self._prev_x, self._prev_y = smoothed_x, smoothed_y
        return smoothed_x, smoothed_y

    def reset(self):
        self._prev_x = None
        self._prev_y = None
