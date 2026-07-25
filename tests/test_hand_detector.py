import unittest
from unittest.mock import MagicMock
from gesture_mouse.hand_detector import HandDetector

class TestHandDetector(unittest.TestCase):
    def test_extract_all_landmarks_includes_handedness(self):
        # Create a mock MediaPipe results object
        mock_results = MagicMock()
        
        # Mock hand landmarks
        mock_hand1 = MagicMock()
        mock_hand1.landmark = [MagicMock(x=0.1, y=0.1, z=0.1)] * 21
        
        mock_hand2 = MagicMock()
        mock_hand2.landmark = [MagicMock(x=0.2, y=0.2, z=0.2)] * 21
        
        mock_results.multi_hand_landmarks = [mock_hand1, mock_hand2]
        
        # Mock handedness
        mock_handedness1 = MagicMock()
        mock_handedness1.classification = [MagicMock(label="Left")]
        
        mock_handedness2 = MagicMock()
        mock_handedness2.classification = [MagicMock(label="Right")]
        
        mock_results.multi_handedness = [mock_handedness1, mock_handedness2]
        
        extracted = HandDetector.extract_all_landmarks(mock_results)
        
        self.assertEqual(len(extracted), 2)
        
        self.assertEqual(extracted[0]["label"], "Left")
        self.assertEqual(len(extracted[0]["landmarks"]), 21)
        self.assertEqual(extracted[0]["landmarks"][0], (0.1, 0.1, 0.1))
        
        self.assertEqual(extracted[1]["label"], "Right")
        self.assertEqual(len(extracted[1]["landmarks"]), 21)
        self.assertEqual(extracted[1]["landmarks"][0], (0.2, 0.2, 0.2))

if __name__ == "__main__":
    unittest.main()
