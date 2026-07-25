import math
import numpy as np
import cv2
from ctypes import cast, POINTER

try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False

from gesture_mouse import config


class VolumeController:
    def __init__(self):
        self.volume = None
        self.min_vol = -65.0
        self.max_vol = 0.0
        
        self.vol_bar = 400
        self.vol_per = 0
        self.current_length = 0
        
        if PYCAW_AVAILABLE:
            try:
                import comtypes
                comtypes.CoInitialize()
                devices = AudioUtilities.GetSpeakers()
                if hasattr(devices, "EndpointVolume"):
                    self.volume = devices.EndpointVolume
                else:
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    self.volume = cast(interface, POINTER(IAudioEndpointVolume))
                volRange = self.volume.GetVolumeRange()
                self.min_vol = volRange[0]
                self.max_vol = volRange[1]
                # Init display values based on current volume
                current_vol = self.volume.GetMasterVolumeLevel()
                self.vol_per = np.interp(current_vol, [self.min_vol, self.max_vol], [0, 100])
                self.vol_bar = np.interp(current_vol, [self.min_vol, self.max_vol], [400, 150])
            except Exception as e:
                print(f"Warning: Failed to initialize Pycaw audio interface: {e}")
                self.volume = None
        else:
            print("Warning: pycaw or comtypes not installed. Volume control disabled.")

    def process_hand(self, landmarks, frame):
        """
        Process hand landmarks to control volume.
        Draws visual feedback directly onto the frame.
        """
        thumb = landmarks[config.THUMB_TIP]
        index = landmarks[config.INDEX_TIP]
        
        w, h = config.FRAME_WIDTH, config.FRAME_HEIGHT
        x1, y1 = int(thumb[0] * w), int(thumb[1] * h)
        x2, y2 = int(index[0] * w), int(index[1] * h)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        
        # Draw circles and line for visual feedback
        cv2.circle(frame, (x1, y1), 15, (255, 0, 255), cv2.FILLED)
        cv2.circle(frame, (x2, y2), 15, (255, 0, 255), cv2.FILLED)
        cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)
        cv2.circle(frame, (cx, cy), 15, (255, 0, 255), cv2.FILLED)
        
        length = math.hypot(x2 - x1, y2 - y1)
        self.current_length = length
        
        # Map distance to volume parameters
        # distance ranges roughly 50 to 300 pixels
        vol_level = np.interp(length, [50, 300], [self.min_vol, self.max_vol])
        self.vol_bar = np.interp(length, [50, 300], [400, 150])
        self.vol_per = np.interp(length, [50, 300], [0, 100])
        
        if self.volume:
            try:
                # np.interp returns np.float64, which ctypes might reject. Explicitly cast to Python float.
                self.volume.SetMasterVolumeLevel(float(vol_level), None)
            except Exception as e:
                print(f"Volume error: {e}")
                
        if length < 50:
            cv2.circle(frame, (cx, cy), 15, (0, 255, 0), cv2.FILLED)
            
    def draw_overlay(self, frame):
        """Draws the volume bar and percentage on the frame."""
        cv2.rectangle(frame, (50, 150), (85, 400), (255, 0, 0), 3)
        cv2.rectangle(frame, (50, int(self.vol_bar)), (85, 400), (255, 0, 0), cv2.FILLED)
        cv2.putText(frame, f"{int(self.vol_per)} %", (40, 450), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 0), 3)
