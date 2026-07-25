import unittest
from gesture_mouse.smoothing import ExponentialSmoother


class TestExponentialSmoother(unittest.TestCase):
    def test_first_call_passes_through_unchanged(self):
        s = ExponentialSmoother(smoothing_factor=0.5)
        x, y = s.smooth(0.5, 0.5)
        self.assertEqual((x, y), (0.5, 0.5))

    def test_smoothing_dampens_a_sudden_jump(self):
        s = ExponentialSmoother(smoothing_factor=0.8)
        s.smooth(0.5, 0.5)
        x, y = s.smooth(0.9, 0.9)  # sudden jitter/jump
        # With alpha=0.8 the output should stay much closer to the previous
        # value (0.5) than to the new raw value (0.9).
        self.assertLess(x, 0.65)
        self.assertGreater(x, 0.5)

    def test_reset_clears_history(self):
        s = ExponentialSmoother()
        s.smooth(0.5, 0.5)
        s.reset()
        x, y = s.smooth(0.9, 0.9)
        self.assertEqual((x, y), (0.9, 0.9))

    def test_rejects_invalid_alpha(self):
        with self.assertRaises(ValueError):
            ExponentialSmoother(smoothing_factor=1.5)


if __name__ == "__main__":
    unittest.main()
