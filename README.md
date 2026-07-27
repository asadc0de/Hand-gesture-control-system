# Gesture-Based Mouse Control System

Control your mouse with hand gestures using your webcam. Built with Python,
OpenCV, MediaPipe, and PyAutoGUI, following the class architecture from the
SDD: `Camera`, `ImageProcessor`, `HandDetector`, `GestureRecognizer`, and
`MouseControlAPI`.

## Gestures

### Single-Hand Gestures
| Gesture | Action |
|---|---|
| Point with index finger ("Pointing") | Move cursor |
| Index and thumb extended ("L" shape / Finger gun) | Left click |
| Index, middle, and thumb extended | Double click |
| Index and pinky extended ("Rock sign") | Right click |
| Index and thumb extended, held for few frames | Click and drag |
| Index and middle extended, others folded ("Peace sign") | Scroll |
| All five fingers folded (Fist) | Minimize active window |
| All five fingers extended (Flat palm) | Restore active window |
| Thumb and pinky extended ("Shaka" sign) | Close window |
| Only thumb extended (Thumbs up) | Navigate back |
| Only pinky extended | Navigate forward |
| **Left hand:** distance between thumb and index | Volume control |

### Multi-Hand Gestures (Window Management)
*Note: These gestures activate/operate in window management mode.*
| Gesture | Action |
|---|---|
| Two hands, both forming a Fist | Minimize all windows |
| Two hands, both open (Not fists) | Restore all windows (after Minimize All) |
| One hand fist, one hand open | Restore last minimized window (after Minimize All) |

## Setup

```bash
pip install -r requirements.txt
python main.py
```

Press `q` in the video window to quit. Yanking the mouse to any screen
corner triggers PyAutoGUI's failsafe and stops the program immediately -
keep that in mind if the cursor starts moving somewhere you don't want it.

## Project structure

```
gesture_mouse/
    config.py            all tunable thresholds and landmark indices
    camera.py             Camera - wraps cv2.VideoCapture
    image_processor.py    ImageProcessor - preprocessing + overlay drawing
    hand_detector.py       HandDetector - wraps MediaPipe Hands
    gesture_recognizer.py GestureRecognizer - pure gesture classification logic
    mouse_control.py       MouseControlAPI - wraps PyAutoGUI
    smoothing.py           ExponentialSmoother - cursor jitter reduction
main.py                    ties the pipeline together
tests/
    test_gesture_recognizer.py   gesture accuracy + deadzone tests
    test_smoothing.py            smoothing filter tests
    test_mouse_control.py        mouse API tests (PyAutoGUI mocked)
```

## Why it's built this way

**Decoupling.** `GestureRecognizer` never imports MediaPipe or OpenCV - it
only takes plain `(x, y, z)` tuples. That's what makes it possible to unit
test gesture accuracy without a webcam. `MouseControlAPI` is the only class
that touches PyAutoGUI, so its tests mock every OS-level call instead of
actually moving your cursor during `pytest`.

**The deadzone.** A raw per-frame gesture read is noisy - fingers moving
into a scroll pose can flicker through a frame or two that look like a
click. `GESTURE_CONFIRM_FRAMES` in `config.py` requires a gesture to repeat
for several consecutive frames before it's accepted. This is the single
biggest thing standing between "cool demo" and "keeps misfiring during your
defense."

**Smoothing.** Raw landmark coordinates jitter even when your hand is
still. `ExponentialSmoother` averages the current and previous position, so
the cursor moves smoothly instead of shaking.

## Running the tests

```bash
python -m unittest discover -s tests -v
```

All 21 tests pass without a webcam or display - `test_mouse_control.py`
mocks every PyAutoGUI call, and `test_gesture_recognizer.py` builds
synthetic hand landmark data by hand to check that scroll poses can't be
misread as clicks and vice versa.

## Tuning for your setup

If gestures feel unreliable on your machine, these are the first knobs to
turn in `gesture_mouse/config.py`:

- `PINCH_THRESHOLD` / `RIGHT_CLICK_THRESHOLD` - raise if clicks aren't
  triggering, lower if they're triggering by accident.
- `GESTURE_CONFIRM_FRAMES` - raise if gestures misfire, but too high makes
  the system feel laggy.
- `SMOOTHING_FACTOR` - raise for a smoother but slower-feeling cursor.
- `FRAME_MARGIN` - increase if you have to stretch your hand painfully far
  to reach screen corners.

## Known limitations (be upfront about these in your defense)

- Cursor movement is driven by a single primary hand (matches the SRS). A second
  hand is only used for two-handed gestures like minimizing all windows.
- Accuracy depends on lighting, exactly as the SRS's non-functional
  requirements section states.
- No voice or keyboard fallback - also an explicit SRS constraint, not an
  oversight.
- The minimize gesture completely minimizes the active window on Windows
  using native API calls. On macOS it uses Cmd+M. On Linux there's no universal
  shortcut across window managers, so it prints a warning instead of guessing wrong.
- Fist detection and click detection both involve curled fingers, so they're
  distinguished by thumb position: a genuine fist keeps the thumb away from
  the index tip, while click requires them pinched together. In rare hand
  shapes these can still overlap - if that happens for you, it's a config
  tuning problem, not something wrong with the underlying approach.
