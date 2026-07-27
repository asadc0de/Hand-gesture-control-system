"""
Central config for Ninja Fruit - Hand Edition.
Keep every tunable number here so balancing the game doesn't mean hunting
through five files.
"""

# ---- Screen / timing ----
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# ---- Physics ----
# Fruit rises straight up at a near-constant speed and never falls back -
# this is an endless "infinite ascension" mode, not an arc-and-fall one.
FRUIT_RISE_SPEED_MIN = 260     # px / s, upward (applied as negative vy)
FRUIT_RISE_SPEED_MAX = 420
FRUIT_DRIFT_X = 40             # small side-to-side wobble speed
HALF_GRAVITY = 900.0           # gravity used only by the cosmetic cut halves

# ---- Spawning ----
SPAWN_INTERVAL_START = 0.85   # seconds between spawns at game start
SPAWN_INTERVAL_MIN = 0.32     # hardest difficulty spawn rate
DIFFICULTY_RAMP_TIME = 60.0   # seconds to reach max difficulty
MULTI_SPAWN_CHANCE = 0.22     # chance to launch 2-3 fruit at once

# ---- Fruit ----
FRUIT_RADIUS_MIN = 34
FRUIT_RADIUS_MAX = 52
FRUIT_TYPES = ["apple", "orange", "watermelon", "banana", "plum"]

FRUIT_COLORS = {
    "apple":      {"body": (222, 45, 45),   "shade": (150, 20, 20),   "flesh": (250, 236, 210)},
    "orange":     {"body": (255, 140, 20),  "shade": (200, 95, 10),   "flesh": (255, 200, 120)},
    "watermelon": {"body": (60, 170, 80),   "shade": (30, 110, 50),   "flesh": (235, 60, 90)},
    "banana":     {"body": (245, 210, 40),  "shade": (200, 165, 20),  "flesh": (250, 245, 210)},
    "plum":       {"body": (120, 60, 150),  "shade": (75, 30, 100),   "flesh": (230, 200, 235)},
}

# ---- Slice slash effect ----
SLASH_LIFE = 0.16
SLASH_COLOR = (255, 255, 255)

# ---- Trail ----
TRAIL_MAX_POINTS = 14
TRAIL_POINT_LIFETIME = 0.18   # seconds a trail point stays visible

# ---- Colors ----
COLOR_BG_TOP = (18, 22, 46)
COLOR_BG_BOTTOM = (8, 10, 22)
COLOR_HUD_TEXT = (255, 255, 255)
COLOR_COMBO = (255, 215, 0)
COLOR_DANGER = (255, 60, 60)

# ---- Hand tracking ----
MAX_HANDS = 2
DETECTION_CONFIDENCE = 0.6
TRACKING_CONFIDENCE = 0.6
CAM_INDEX = 0
MIRROR_CAMERA = True
