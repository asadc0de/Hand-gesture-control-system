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
CAMERA_INDEX = 1  # 0 = Laptop Webcam, 1 = Phone / External Camera
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# ---- Detection settings ----
MAX_NUM_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7

# ---- Gesture thresholds (normalized 0-1 coordinates, tuned for a 640x480 frame) ----
CLICK_PINCH_THRESHOLD = 0.055        # thumb tip to middle tip distance -> left click entry
CLICK_PINCH_RELEASE_THRESHOLD = 0.075# thumb tip to middle tip distance -> left click/drag release hysteresis
RIGHT_CLICK_PINCH_THRESHOLD = 0.060  # thumb tip to ring tip distance -> right click
TAP_HOLD_MAX_MS = 250                # max ms a pinch can be held to register as a tap click (longer hold becomes DRAG)
DOUBLE_CLICK_WINDOW_MS = 300         # ms window between two consecutive taps; kept comfortably below
                                     # standard OS double-click thresholds (~500ms on Windows) so the OS
                                     # event loop naturally merges two rapid click() calls into a double-click.
CLICK_CONFIRM_FRAMES = 2             # frames to confirm click pinch (responsive for quick tap)
GESTURE_CONFIRM_FRAMES = 4           # frames a gesture must be stable before it's accepted (deadzone)

# ---- Cursor smoothing ----
SMOOTHING_FACTOR = 0.5          # 0 = no smoothing (raw/jittery), 1 = frozen cursor
CURSOR_DEAD_ZONE_PX = 3
                                  # Higher = steadier cursor when your hand is still,
                                  # but slightly more lag when you move fast.

# ---- Steady Clicks / Cursor Freeze ----
CURSOR_FREEZE_DURATION_MS = 200  # ms to lock cursor movement upon click detection
CURSOR_FREEZE_ENABLED = True     # toggle cursor freeze for A/B testing

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
SCROLL_SENSITIVITY = 30          # pixels of vertical hand movement per scroll "tick"
SCROLL_AMOUNT = 120              # pyautogui scroll units per tick

# ---- Lock (two-hand X gesture) ----
# Both hands point with index only; fingertips must meet near the cross point.
LOCK_X_TIP_DISTANCE = 0.14          # max normalized distance between the two index tips
LOCK_X_MIN_WRIST_SEPARATION = 0.12  # wrists must be apart so it is clearly two hands

# ---- Presentation Mode ----
SWIPE_SENSITIVITY = 50           # pixels of horizontal movement to trigger a swipe
ZOOM_SENSITIVITY = 0.05          # change in normalized distance to trigger a zoom step

# ---- Frame margin ----
# Landmarks near the very edge of the frame are unreliable; we map only the
# central region of the camera view to the full screen so users don't have
# to stretch their hand to the frame boundary to reach screen corners.
FRAME_MARGIN = 0.15
