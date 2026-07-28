import unittest
import time
from unittest.mock import patch
from gesture_mouse.gesture_recognizer import GestureRecognizer, Gesture
from gesture_mouse import config

def make_landmarks(index_ext=False, middle_ext=False, ring_ext=False, pinky_ext=False, thumb_ext=False):
    # Base dummy landmarks
    lm = [(0.0, 0.0)] * 21
    
    # helper to set extended
    def set_ext(tip_idx, pip_idx, ext):
        if ext:
            lm[tip_idx] = (0.5, 0.1)
            lm[pip_idx] = (0.5, 0.5)
        else:
            lm[tip_idx] = (0.5, 0.5)
            lm[pip_idx] = (0.5, 0.1)

    set_ext(config.INDEX_TIP, config.INDEX_PIP, index_ext)
    set_ext(config.MIDDLE_TIP, config.MIDDLE_PIP, middle_ext)
    set_ext(config.RING_TIP, config.RING_PIP, ring_ext)
    set_ext(config.PINKY_TIP, config.PINKY_PIP, pinky_ext)
    
    # Thumb
    lm[config.PINKY_MCP] = (0.8, 0.8)
    lm[config.THUMB_MCP] = (0.2, 0.8)
    if thumb_ext:
        lm[config.THUMB_TIP] = (0.0, 0.2) # Further than base from pinky
    else:
        lm[config.THUMB_TIP] = (0.7, 0.7) # Closer
        
    return lm

class TestConfusionMatrix(unittest.TestCase):
    def test_confusion_matrix(self):
        recognizer = GestureRecognizer(confirm_frames=3)
        # Using a mock for time to precisely control the simulated frames
        
        simulated_fps = 30
        frame_time = 1.0 / simulated_fps
        
        results = {
            "EXPECTED_CLICK": {"CLICK": 0, "DOUBLE_CLICK": 0, "DRAG": 0, "SCROLL": 0, "OTHER": 0},
            "EXPECTED_DOUBLE_CLICK": {"CLICK": 0, "DOUBLE_CLICK": 0, "DRAG": 0, "SCROLL": 0, "OTHER": 0},
            "EXPECTED_SCROLL": {"CLICK": 0, "DOUBLE_CLICK": 0, "DRAG": 0, "SCROLL": 0, "OTHER": 0}
        }
        
        # 1. Test CLICK (Index extended < 0.4s, then folded)
        # 0.4s = 12 frames. Let's extend for 8 frames, then fold.
        for _ in range(30):
            recognizer.reset()
            current_t = 0.0
            fired = Gesture.NONE
            with patch('time.time') as mock_time:
                # Extend for 8 frames (0.26s)
                for _ in range(8):
                    mock_time.return_value = current_t
                    g = recognizer.recognize(make_landmarks(index_ext=True))
                    if g in (Gesture.CLICK, Gesture.DOUBLE_CLICK, Gesture.DRAG, Gesture.SCROLL):
                        fired = g
                    current_t += frame_time
                
                # Fold for 5 frames
                for _ in range(5):
                    mock_time.return_value = current_t
                    g = recognizer.recognize(make_landmarks(index_ext=False))
                    if g in (Gesture.CLICK, Gesture.DOUBLE_CLICK, Gesture.DRAG, Gesture.SCROLL):
                        fired = g
                    current_t += frame_time
                    
            name = fired.name if fired != Gesture.NONE else "OTHER"
            if name in results["EXPECTED_CLICK"]:
                results["EXPECTED_CLICK"][name] += 1
            else:
                results["EXPECTED_CLICK"]["OTHER"] += 1

        # 2. Test DOUBLE CLICK (Extend -> Fold -> Extend within 0.6s)
        for _ in range(30):
            recognizer.reset()
            current_t = 0.0
            fired = Gesture.NONE
            with patch('time.time') as mock_time:
                # Extend for 5 frames
                for _ in range(5):
                    mock_time.return_value = current_t
                    g = recognizer.recognize(make_landmarks(index_ext=True))
                    current_t += frame_time
                # Fold for 5 frames
                for _ in range(5):
                    mock_time.return_value = current_t
                    g = recognizer.recognize(make_landmarks(index_ext=False))
                    current_t += frame_time
                # Extend for 5 frames
                for _ in range(5):
                    mock_time.return_value = current_t
                    g = recognizer.recognize(make_landmarks(index_ext=True))
                    if g in (Gesture.CLICK, Gesture.DOUBLE_CLICK, Gesture.DRAG, Gesture.SCROLL):
                        fired = g
                    current_t += frame_time
                    
            name = fired.name if fired != Gesture.NONE else "OTHER"
            if name in results["EXPECTED_DOUBLE_CLICK"]:
                results["EXPECTED_DOUBLE_CLICK"][name] += 1
            else:
                results["EXPECTED_DOUBLE_CLICK"]["OTHER"] += 1

        # 3. Test SCROLL (Index + Middle extended for 15 frames)
        for _ in range(30):
            recognizer.reset()
            current_t = 0.0
            fired = Gesture.NONE
            with patch('time.time') as mock_time:
                for _ in range(15):
                    mock_time.return_value = current_t
                    g = recognizer.recognize(make_landmarks(index_ext=True, middle_ext=True))
                    if g in (Gesture.CLICK, Gesture.DOUBLE_CLICK, Gesture.DRAG, Gesture.SCROLL):
                        fired = g
                    current_t += frame_time
                    
            name = fired.name if fired != Gesture.NONE else "OTHER"
            if name in results["EXPECTED_SCROLL"]:
                results["EXPECTED_SCROLL"][name] += 1
            else:
                results["EXPECTED_SCROLL"]["OTHER"] += 1
                
        print("\n=== CONFUSION MATRIX ===")
        print(f"EXPECTED CLICK        -> {results['EXPECTED_CLICK']}")
        print(f"EXPECTED DOUBLE_CLICK -> {results['EXPECTED_DOUBLE_CLICK']}")
        print(f"EXPECTED SCROLL       -> {results['EXPECTED_SCROLL']}")
        print("========================\n")
        
        self.assertEqual(results["EXPECTED_CLICK"]["CLICK"], 30)
        self.assertEqual(results["EXPECTED_DOUBLE_CLICK"]["DOUBLE_CLICK"], 30)
        self.assertEqual(results["EXPECTED_SCROLL"]["SCROLL"], 30)
        self.assertEqual(results["EXPECTED_CLICK"]["DOUBLE_CLICK"], 0)
        self.assertEqual(results["EXPECTED_DOUBLE_CLICK"]["CLICK"], 0)

if __name__ == '__main__':
    unittest.main()
