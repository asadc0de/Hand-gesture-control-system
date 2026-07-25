"""
WindowManager module.

Handles cross-platform window management (minimize, restore).
We use pygetwindow because it's cross-platform and simpler to use
for this specific use case than raw Win32 APIs (pywin32), keeping
the code clean while satisfying the requirements.
"""

import pygetwindow as gw
import ctypes

class WindowManager:
    def __init__(self):
        # A stack of lists. Each list represents a batch of windows
        # minimized during a single minimize_all() call.
        self._minimized_batches = []
        
        # A stack of window handles for single-window minimize actions
        self._single_minimized_stack = []

    def minimize_all(self):
        """
        Enumerates all currently visible, non-minimized windows,
        minimizes each one, and pushes their handles onto an internal stack
        in the order they were minimized.
        """
        windows = gw.getAllWindows()
        minimized_this_batch = []
        
        for win in windows:
            # We only want to minimize visible windows that aren't already minimized
            if win.visible and not win.isMinimized:
                # Some system windows don't have titles, skipping them avoids issues
                if win.title:
                    win.minimize()
                    minimized_this_batch.append(win)
                    
        if minimized_this_batch:
            self._minimized_batches.append(minimized_this_batch)

    def restore_all(self):
        """
        Pops every handle pushed by the most recent minimize_all() call 
        and restores each one.
        """
        if not self._minimized_batches:
            return
            
        latest_batch = self._minimized_batches.pop()
        # Restore in reverse order of how they were minimized to preserve z-order
        for win in reversed(latest_batch):
            win.restore()

    def restore_last(self):
        """
        Pops only the single most recently minimized handle from the stack 
        and restores just that one window, leaving the rest minimized.
        """
        if not self._minimized_batches:
            return
            
        latest_batch = self._minimized_batches[-1]
        
        if latest_batch:
            last_win = latest_batch.pop()
            last_win.restore()
            
            
        # If the batch is now empty, remove it from the stack
        if not latest_batch:
            self._minimized_batches.pop()

    def minimize_active(self):
        """
        Minimizes the currently active (foreground) window using Win32 API,
        and pushes its handle to the single-window stack so it can be restored later.
        """
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd:
            # SW_MINIMIZE = 6
            ctypes.windll.user32.ShowWindow(hwnd, 6)
            self._single_minimized_stack.append(hwnd)

    def restore_last_single(self):
        """
        Pops the last window handle minimized via minimize_active() and restores it.
        """
        if not self._single_minimized_stack:
            return
            
        hwnd = self._single_minimized_stack.pop()
        # SW_RESTORE = 9
        ctypes.windll.user32.ShowWindow(hwnd, 9)
