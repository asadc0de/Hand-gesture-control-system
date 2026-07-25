import unittest
from unittest.mock import patch, MagicMock
from gesture_mouse.window_manager import WindowManager

class TestWindowManager(unittest.TestCase):
    def setUp(self):
        self.wm = WindowManager()

    def _create_mock_window(self, title, visible=True, is_minimized=False):
        mock_win = MagicMock()
        mock_win.title = title
        mock_win.visible = visible
        mock_win.isMinimized = is_minimized
        return mock_win

    @patch("gesture_mouse.window_manager.gw.getAllWindows")
    def test_minimize_all_pushes_batch_and_minimizes_correct_windows(self, mock_get_all):
        # Create some mock windows
        win1 = self._create_mock_window("Win1")
        win2 = self._create_mock_window("Win2", visible=False) # Invisible, shouldn't minimize
        win3 = self._create_mock_window("Win3")
        win4 = self._create_mock_window("Win4", is_minimized=True) # Already minimized, skip
        win5 = self._create_mock_window("") # No title, skip
        
        mock_get_all.return_value = [win1, win2, win3, win4, win5]
        
        self.wm.minimize_all()
        
        # Only win1 and win3 should have been minimized
        win1.minimize.assert_called_once()
        win3.minimize.assert_called_once()
        win2.minimize.assert_not_called()
        win4.minimize.assert_not_called()
        win5.minimize.assert_not_called()
        
        # The stack should contain one batch with [win1, win3]
        self.assertEqual(len(self.wm._minimized_batches), 1)
        self.assertEqual(self.wm._minimized_batches[0], [win1, win3])

    def test_restore_all_pops_entire_latest_batch(self):
        win1 = self._create_mock_window("Win1")
        win2 = self._create_mock_window("Win2")
        win3 = self._create_mock_window("Win3")
        
        # Manually push two batches
        self.wm._minimized_batches.append([win1])
        self.wm._minimized_batches.append([win2, win3])
        
        self.wm.restore_all()
        
        # Should have restored win2 and win3 (in reverse order, but we just check calls here)
        win2.restore.assert_called_once()
        win3.restore.assert_called_once()
        win1.restore.assert_not_called()
        
        # One batch should be left
        self.assertEqual(len(self.wm._minimized_batches), 1)
        self.assertEqual(self.wm._minimized_batches[0], [win1])

    def test_restore_last_pops_only_one_window(self):
        win1 = self._create_mock_window("Win1")
        win2 = self._create_mock_window("Win2")
        win3 = self._create_mock_window("Win3")
        
        self.wm._minimized_batches.append([win1])
        self.wm._minimized_batches.append([win2, win3])
        
        self.wm.restore_last()
        
        # Should restore win3 (the last one in the latest batch)
        win3.restore.assert_called_once()
        win2.restore.assert_not_called()
        win1.restore.assert_not_called()
        
        # The latest batch should still exist, containing only win2
        self.assertEqual(len(self.wm._minimized_batches), 2)
        self.assertEqual(self.wm._minimized_batches[1], [win2])
        
        # Call it again
        self.wm.restore_last()
        win2.restore.assert_called_once()
        
        # Now the batch is empty and should be removed
        self.assertEqual(len(self.wm._minimized_batches), 1)
        self.assertEqual(self.wm._minimized_batches[0], [win1])

if __name__ == "__main__":
    unittest.main()
