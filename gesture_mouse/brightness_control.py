import math
import numpy as np
import cv2
import screen_brightness_control as sbc
from gesture_mouse import config

class BrightnessController:
    def __init__(self):
        self.min_bright = 0.0
        self.max_bright = 100.0
        
        self.bright_bar = 400
        self.bright_per = 0
        self.current_length = 0
        
        try:
            current_bright = sbc.get_brightness()[0]
            self.bright_per = np.interp(current_bright, [self.min_bright, self.max_bright], [0, 100])
            self.bright_bar = np.interp(current_bright, [self.min_bright, self.max_bright], [150, 400])
        except Exception as e:
            print(f"Warning: Failed to get initial brightness: {e}")

    def process_hand(self, landmarks, frame):
        """
        Process hand landmarks to control brightness.
        Draws visual feedback directly onto the frame.
        """
        thumb = landmarks[config.THUMB_TIP]
        index = landmarks[config.INDEX_TIP]
        
        w, h = config.FRAME_WIDTH, config.FRAME_HEIGHT
        x1, y1 = int(thumb[0] * w), int(thumb[1] * h)
        x2, y2 = int(index[0] * w), int(index[1] * h)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        
        # Draw circles and line for visual feedback (Yellow for brightness)
        cv2.circle(frame, (x1, y1), 15, (0, 255, 255), cv2.FILLED)
        cv2.circle(frame, (x2, y2), 15, (0, 255, 255), cv2.FILLED)
        cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 255), 3)
        cv2.circle(frame, (cx, cy), 15, (0, 255, 255), cv2.FILLED)
        
        length = math.hypot(x2 - x1, y2 - y1)
        self.current_length = length
        
        # Map distance to brightness parameters
        bright_level = np.interp(length, [50, 300], [self.min_bright, self.max_bright])
        self.bright_bar = np.interp(length, [50, 300], [150, 400])
        self.bright_per = np.interp(length, [50, 300], [0, 100])
        
        try:
            sbc.set_brightness(int(bright_level))
        except Exception as e:
            pass
                
        if length < 50:
            cv2.circle(frame, (cx, cy), 15, (0, 255, 0), cv2.FILLED)
            
    def draw_overlay(self, frame):
        """Draws the brightness bar and percentage on the frame."""
        cv2.rectangle(frame, (150, 400), (400, 435), (0, 255, 255), 3)
        cv2.rectangle(frame, (150, 400), (int(self.bright_bar), 435), (0, 255, 255), cv2.FILLED)
        cv2.putText(frame, f"{int(self.bright_per)} %", (420, 425), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 255), 3)
