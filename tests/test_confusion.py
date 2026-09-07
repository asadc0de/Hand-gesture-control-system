"""
Confusion Matrix & Cross-Talk Prevention Tests.

Verifies:
1. GestureRecognizer spatial classification: MOVE vs SCROLL zero confusion (30/30 each).
2. LeftHandController action dispatch: LEFT_CLICK vs RIGHT_CLICK vs AMBIGUOUS_PINCH zero confusion (30/30 each).
"""

import unittest
from unittest.mock import MagicMock, patch
import time

from gesture_mouse.gesture_recognizer import GestureRecognizer, Gesture
from gesture_mouse.left_hand_controller import LeftHandController
from gesture_mouse import config


def make_landmarks(index_ext=False, middle_ext=False, ring_ext=False, pinky_ext=False, thumb_ext=False):
    lm = [(0.5, 0.9, 0.0)] * 21
    
    lm[config.WRIST] = (0.5, 0.9, 0.0)
    lm[config.THUMB_MCP] = (0.2, 0.70, 0.0)
    lm[config.INDEX_MCP] = (0.4, 0.60, 0.0)
    lm[config.MIDDLE_MCP] = (0.5, 0.60, 0.0)
    lm[config.RING_MCP] = (0.6, 0.60, 0.0)
    lm[config.PINKY_MCP] = (0.8, 0.60, 0.0)

    # PIP joints
    lm[config.INDEX_PIP] = (0.4, 0.65, 0.0)
    lm[config.MIDDLE_PIP] = (0.5, 0.65, 0.0)
    lm[config.RING_PIP] = (0.6, 0.65, 0.0)
    lm[config.PINKY_PIP] = (0.8, 0.65, 0.0)

    # tips
    lm[config.INDEX_TIP] = (0.42, 0.35, 0.0) if index_ext else (0.42, 0.70, 0.0)
    lm[config.MIDDLE_TIP] = (0.52, 0.35, 0.0) if middle_ext else (0.52, 0.70, 0.0)
    lm[config.RING_TIP] = (0.62, 0.35, 0.0) if ring_ext else (0.62, 0.70, 0.0)
    lm[config.PINKY_TIP] = (0.82, 0.35, 0.0) if pinky_ext else (0.82, 0.70, 0.0)
    
    lm[config.THUMB_IP] = (0.4, 0.68, 0.0)
    if thumb_ext:
        lm[config.THUMB_TIP] = (0.1, 0.40, 0.0)
    else:
        lm[config.THUMB_TIP] = (0.6, 0.65, 0.0)
        
    return lm


def make_left_hand(thumb_tip, middle_tip, ring_tip, index_tip=(0.4, 0.3, 0.0), wrist=(0.5, 0.9, 0.0)):
    lm = [(0.5, 0.9, 0.0)] * 21
    lm[config.WRIST] = wrist
    lm[config.THUMB_TIP] = thumb_tip
    lm[config.INDEX_TIP] = index_tip
    lm[config.INDEX_PIP] = (0.4, 0.55, 0.0)
    lm[config.MIDDLE_TIP] = middle_tip
    lm[config.MIDDLE_PIP] = (0.5, 0.65, 0.0)
    lm[config.MIDDLE_MCP] = (0.5, 0.75, 0.0)
    lm[config.RING_TIP] = ring_tip
    lm[config.RING_PIP] = (0.6, 0.65, 0.0)
    return lm


class TestConfusionMatrix(unittest.TestCase):
    def test_gesture_recognizer_confusion_matrix(self):
        """
        Tests right-hand spatial pose classification: MOVE vs SCROLL.
        """
        recognizer = GestureRecognizer(confirm_frames=3)
        simulated_fps = 30
        frame_time = 1.0 / simulated_fps
        
        results = {
            "EXPECTED_MOVE": {"MOVE": 0, "SCROLL": 0, "OTHER": 0},
            "EXPECTED_SCROLL": {"MOVE": 0, "SCROLL": 0, "OTHER": 0}
        }
        
        # 1. Test MOVE (Index extended for 5 frames)
        for _ in range(30):
            recognizer.reset()
            current_t = 0.0
            fired = Gesture.NONE
            with patch('time.time') as mock_time:
                for _ in range(5):
                    mock_time.return_value = current_t
                    g = recognizer.recognize(make_landmarks(index_ext=True))
                    if g in (Gesture.MOVE, Gesture.SCROLL):
                        fired = g
                    current_t += frame_time
                    
            name = fired.name if fired != Gesture.NONE else "OTHER"
            results["EXPECTED_MOVE"][name] += 1

        # 2. Test SCROLL (Index + Middle extended for 5 frames)
        for _ in range(30):
            recognizer.reset()
            current_t = 0.0
            fired = Gesture.NONE
            with patch('time.time') as mock_time:
                for _ in range(5):
                    mock_time.return_value = current_t
                    g = recognizer.recognize(make_landmarks(index_ext=True, middle_ext=True))
                    if g in (Gesture.MOVE, Gesture.SCROLL):
                        fired = g
                    current_t += frame_time
                    
            name = fired.name if fired != Gesture.NONE else "OTHER"
            results["EXPECTED_SCROLL"][name] += 1
                
        print("\n=== RIGHT-HAND SPATIAL CONFUSION MATRIX ===")
        print(f"EXPECTED MOVE   -> {results['EXPECTED_MOVE']}")
        print(f"EXPECTED SCROLL -> {results['EXPECTED_SCROLL']}")
        print("===========================================\n")
        
        self.assertEqual(results["EXPECTED_MOVE"]["MOVE"], 30)
        self.assertEqual(results["EXPECTED_MOVE"]["SCROLL"], 0)
        self.assertEqual(results["EXPECTED_SCROLL"]["SCROLL"], 30)
        self.assertEqual(results["EXPECTED_SCROLL"]["MOVE"], 0)

    def test_left_hand_controller_confusion_matrix(self):
        """
        Tests left-hand action dispatch: LEFT_CLICK (Thumb+Middle) vs RIGHT_CLICK (Thumb+Ring) vs AMBIGUOUS_PINCH.
        """
        results = {
            "INPUT: THUMB+MIDDLE (Expect Left Click)": {"LEFT_CLICK": 0, "RIGHT_CLICK": 0, "OTHER": 0},
            "INPUT: THUMB+RING (Expect Right Click)": {"LEFT_CLICK": 0, "RIGHT_CLICK": 0, "OTHER": 0},
            "INPUT: SIMULTANEOUS BOTH (Disambiguated -> Left Click)": {"LEFT_CLICK": 0, "RIGHT_CLICK": 0, "OTHER": 0}
        }

        # 1. Test LEFT_CLICK (Thumb + Middle pinch tap)
        pinch_left = make_left_hand(
            thumb_tip=(0.50, 0.60, 0.0),
            middle_tip=(0.50, 0.61, 0.0),
            ring_tip=(0.70, 0.40, 0.0)
        )
        open_hand = make_left_hand(
            thumb_tip=(0.20, 0.60, 0.0),
            middle_tip=(0.50, 0.30, 0.0),
            ring_tip=(0.70, 0.30, 0.0)
        )

        for _ in range(30):
            controller = LeftHandController()
            mouse = MagicMock()
            controller.process_hand(pinch_left, False, False, mouse)
            controller.process_hand(open_hand, False, False, mouse)

            if mouse.click.call_count == 1 and mouse.right_click.call_count == 0:
                results["INPUT: THUMB+MIDDLE (Expect Left Click)"]["LEFT_CLICK"] += 1
            elif mouse.right_click.call_count == 1:
                results["INPUT: THUMB+MIDDLE (Expect Left Click)"]["RIGHT_CLICK"] += 1
            else:
                results["INPUT: THUMB+MIDDLE (Expect Left Click)"]["OTHER"] += 1

        # 2. Test RIGHT_CLICK (Thumb + Ring pinch tap)
        pinch_right = make_left_hand(
            thumb_tip=(0.60, 0.60, 0.0),
            middle_tip=(0.40, 0.30, 0.0),
            ring_tip=(0.60, 0.61, 0.0)
        )

        for _ in range(30):
            controller = LeftHandController()
            mouse = MagicMock()
            controller.process_hand(pinch_right, False, False, mouse)
            controller.process_hand(open_hand, False, False, mouse)

            if mouse.right_click.call_count == 1 and mouse.click.call_count == 0:
                results["INPUT: THUMB+RING (Expect Right Click)"]["RIGHT_CLICK"] += 1
            elif mouse.click.call_count == 1:
                results["INPUT: THUMB+RING (Expect Right Click)"]["LEFT_CLICK"] += 1
            else:
                results["INPUT: THUMB+RING (Expect Right Click)"]["OTHER"] += 1

        # 3. Test AMBIGUOUS_PINCH (Thumb touches BOTH middle and ring simultaneously)
        pinch_ambiguous = make_left_hand(
            thumb_tip=(0.50, 0.60, 0.0),
            middle_tip=(0.50, 0.60, 0.0),
            ring_tip=(0.50, 0.60, 0.0)
        )

        for _ in range(30):
            controller = LeftHandController()
            mouse = MagicMock()
            controller.process_hand(pinch_ambiguous, False, False, mouse)
            controller.process_hand(open_hand, False, False, mouse)

            if mouse.click.call_count == 1 and mouse.right_click.call_count == 0:
                results["INPUT: SIMULTANEOUS BOTH (Disambiguated -> Left Click)"]["LEFT_CLICK"] += 1
            elif mouse.right_click.call_count == 1:
                results["INPUT: SIMULTANEOUS BOTH (Disambiguated -> Left Click)"]["RIGHT_CLICK"] += 1
            else:
                results["INPUT: SIMULTANEOUS BOTH (Disambiguated -> Left Click)"]["OTHER"] += 1

        print("\n=== LEFT-HAND ACTION DISPATCH & DISAMBIGUATION MATRIX ===")
        for key, val in results.items():
            print(f"{key:<55} -> {val}")
        print("=========================================================\n")

        self.assertEqual(results["INPUT: THUMB+MIDDLE (Expect Left Click)"]["LEFT_CLICK"], 30)
        self.assertEqual(results["INPUT: THUMB+MIDDLE (Expect Left Click)"]["RIGHT_CLICK"], 0)
        self.assertEqual(results["INPUT: THUMB+RING (Expect Right Click)"]["RIGHT_CLICK"], 30)
        self.assertEqual(results["INPUT: THUMB+RING (Expect Right Click)"]["LEFT_CLICK"], 0)
        self.assertEqual(results["INPUT: SIMULTANEOUS BOTH (Disambiguated -> Left Click)"]["LEFT_CLICK"], 30)
        self.assertEqual(results["INPUT: SIMULTANEOUS BOTH (Disambiguated -> Left Click)"]["RIGHT_CLICK"], 0)


if __name__ == '__main__':
    unittest.main()
