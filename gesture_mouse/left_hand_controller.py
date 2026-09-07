"""
LeftHandController module.

Handles all left-hand interaction:
- Left click (quick thumb+middle tap <= TAP_HOLD_MAX_MS -> immediate click() on release)
- Left drag (sustained thumb+middle pinch > TAP_HOLD_MAX_MS -> start_drag(), end_drag() on release)
- Right click (quick thumb+ring tap -> immediate right_click() on release)
- Media mode volume/brightness adjustments (thumb+index pinch when media mode active)
- Presentation mode pass-through
"""

import math
import time

from gesture_mouse import config


class LeftHandController:
    def __init__(self, max_missing_frames: int = 2):
        self.left_middle_pinched = False
        self.left_middle_pinch_start = 0.0
        self.left_is_dragging = False
        
        self.left_ring_pinched = False
        self.left_ring_pinch_start = 0.0

        self.missing_frames = 0
        self.max_missing_frames = max_missing_frames

    def reset(self, mouse=None):
        if self.left_is_dragging and mouse is not None:
            mouse.end_drag()
        self.left_is_dragging = False
        self.left_middle_pinched = False
        self.left_ring_pinched = False
        self.missing_frames = 0

    def process_hand(self, landmarks, media_mode, presentation_mode, mouse,
                     volume_controller=None, brightness_controller=None, frame=None):
        """
        Process a single frame of left-hand landmarks.
        """
        if landmarks is None:
            self.missing_frames += 1
            if self.missing_frames >= self.max_missing_frames:
                self.reset(mouse)
            return

        self.missing_frames = 0

        wrist = landmarks[config.WRIST]
        middle_mcp = landmarks[config.MIDDLE_MCP]
        
        dy = abs(wrist[1] - middle_mcp[1])
        dx = abs(wrist[0] - middle_mcp[0])
        
        # If media mode active, route to volume / brightness (thumb + index gesture)
        if media_mode:
            if volume_controller is not None and brightness_controller is not None:
                if dy > dx:
                    volume_controller.process_hand(landmarks, frame)
                    if frame is not None:
                        volume_controller.draw_overlay(frame)
                else:
                    brightness_controller.process_hand(landmarks, frame)
                    if frame is not None:
                        brightness_controller.draw_overlay(frame)
            return

        # In presentation mode, clicking is disabled
        if presentation_mode:
            return

        l_thumb = landmarks[config.THUMB_TIP]
        l_middle = landmarks[config.MIDDLE_TIP]
        l_ring = landmarks[config.RING_TIP]
        
        l_mid_dist = math.hypot(l_thumb[0] - l_middle[0], l_thumb[1] - l_middle[1])
        l_ring_dist = math.hypot(l_thumb[0] - l_ring[0], l_thumb[1] - l_ring[1])

        # Mutually exclusive pinch detection when idle
        if not self.left_middle_pinched and not self.left_ring_pinched:
            # Right click candidate: Thumb + Ring pinch (requires thumb not pinching middle)
            if l_ring_dist < config.RIGHT_CLICK_PINCH_THRESHOLD and l_mid_dist >= config.CLICK_PINCH_THRESHOLD:
                self.left_ring_pinched = True
                self.left_ring_pinch_start = time.time()
                if mouse is not None:
                    mouse.lock_cursor()
            # Left click / Drag candidate: Thumb + Middle pinch
            elif l_mid_dist < config.CLICK_PINCH_THRESHOLD:
                self.left_middle_pinched = True
                self.left_middle_pinch_start = time.time()
                if mouse is not None:
                    mouse.lock_cursor()

        # Active Left Click / Drag tracking
        if self.left_middle_pinched:
            release_threshold = getattr(config, "CLICK_PINCH_RELEASE_THRESHOLD", 0.075)
            if l_mid_dist < release_threshold:
                hold_ms = (time.time() - self.left_middle_pinch_start) * 1000.0
                if hold_ms >= config.TAP_HOLD_MAX_MS and not self.left_is_dragging:
                    if mouse is not None:
                        mouse.start_drag()
                    self.left_is_dragging = True
            else:
                if self.left_is_dragging:
                    if mouse is not None:
                        mouse.end_drag()
                    self.left_is_dragging = False
                else:
                    # Quick tap completed: immediate click on release
                    if mouse is not None:
                        mouse.click()
                self.left_middle_pinched = False

        # Active Right Click tracking (tap only)
        elif self.left_ring_pinched:
            if l_ring_dist >= config.RIGHT_CLICK_PINCH_THRESHOLD:
                # Quick tap completed: immediate right-click on release
                if mouse is not None:
                    mouse.right_click()
                self.left_ring_pinched = False
