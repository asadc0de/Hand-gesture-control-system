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


class TestPointerContinuityAndStateTransitions(unittest.TestCase):
    def test_temporary_none_preserves_smoother_history(self):
        """
        When gesture temporarily drops to NONE (raw flicker), smoother history
        is not wiped, so resumption to MOVE glides smoothly without jumping.
        """
        smoother = ExponentialSmoother(smoothing_factor=0.5)
        # 1. Active MOVE at (0.50, 0.50)
        smoother.smooth(0.50, 0.50)

        # 2. Transient NONE for 2 frames: smoother is not reset
        # Hand drifts slightly to (0.52, 0.52) during NONE
        
        # 3. Resumption to MOVE: smoother blends from (0.50, 0.50)
        x, y = smoother.smooth(0.52, 0.52)
        # With alpha=0.5: 0.5*0.50 + 0.5*0.52 = 0.510 (smooth blend, not 0.52 raw jump)
        self.assertAlmostEqual(x, 0.51, delta=1e-5)
        self.assertAlmostEqual(y, 0.51, delta=1e-5)

    def test_discrete_gesture_entry_transition_resets_smoother(self):
        """
        Entering a confirmed discrete gesture resets smoother on the transition edge.
        """
        smoother = ExponentialSmoother(smoothing_factor=0.5)
        smoother.smooth(0.50, 0.50)

        # Discrete gesture entered (transition edge: prev != current)
        smoother.reset()

        # When motion resumes after discrete gesture, first coordinate passes cleanly
        x, y = smoother.smooth(0.80, 0.80)
        self.assertEqual((x, y), (0.80, 0.80))

    def test_hand_loss_resets_smoother(self):
        """
        When right hand tracking is completely lost, smoother is reset.
        """
        smoother = ExponentialSmoother(smoothing_factor=0.5)
        smoother.smooth(0.50, 0.50)
        
        # Hand lost
        smoother.reset()
        self.assertIsNone(smoother._prev_x)
        self.assertIsNone(smoother._prev_y)


if __name__ == "__main__":
    unittest.main()
