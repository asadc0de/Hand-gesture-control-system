"""
Central configuration for the gesture mouse system.
Keeping every tunable value here means you only touch one file
when your webcam, lighting, or screen setup changes.
"""

# ---- MediaPipe hand landmark indices (fixed by the MediaPipe Hands model) ----
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20

# ---- Camera settings ----
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# ---- Detection settings ----
MAX_NUM_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7

# ---- Gesture thresholds (normalized 0-1 coordinates, tuned for a 640x480 frame) ----
PINCH_THRESHOLD = 0.045          # thumb tip to index tip distance -> left click
RIGHT_CLICK_THRESHOLD = 0.045    # thumb tip to pinky tip distance -> right click
DRAG_HOLD_FRAMES = 5             # frames a pinch must persist before it counts as a drag-start
GESTURE_CONFIRM_FRAMES = 4       # frames a gesture must be stable before it's accepted (deadzone)

# ---- Cursor smoothing ----
SMOOTHING_FACTOR = 0.5          # 0 = no smoothing (raw/jittery), 1 = frozen cursor
CURSOR_DEAD_ZONE_PX = 3
                                  # Higher = steadier cursor when your hand is still,
                                  # but slightly more lag when you move fast.

# ---- Cursor sensitivity (mouse-like acceleration) ----
# Amplifies hand movement around the center of the usable region so a small
# hand movement covers a large chunk of the screen, like a real mouse.
# 1.0 = no amplification (1:1 mapping). Try 1.5-2.5; higher = more sensitive.
CURSOR_SENSITIVITY = 2.0

# Ignore cursor moves smaller than this many screen pixels. This is what
# actually kills the residual vibration when your hand is basically still -
# without it, even a well-smoothed signal still nudges the cursor by a pixel
# or two every frame, which reads as a shake.
MOVE_DEADZONE_PX = 4

# Never let the mapped cursor position land exactly on a screen corner.
# PyAutoGUI's failsafe kills the script the instant the cursor hits (0,0)
# or the opposite corner, assuming something's gone wrong. Since our own
# mapping can legitimately reach the true corner when your hand nears the
# edge of the frame, this buffer keeps us a few pixels short of it.
SCREEN_EDGE_BUFFER_PX = 8

# ---- Scroll ----
SCROLL_SENSITIVITY = 40          # pixels of vertical hand movement per scroll "tick"
SCROLL_AMOUNT = 40               # pyautogui scroll units per tick

# ---- Frame margin ----
# Landmarks near the very edge of the frame are unreliable; we map only the
# central region of the camera view to the full screen so users don't have
# to stretch their hand to the frame boundary to reach screen corners.
FRAME_MARGIN = 0.15
