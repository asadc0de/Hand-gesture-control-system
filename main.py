"""
Entry point for the Gesture-Based Mouse Control System.

Pipeline (matches the SRS data flow exactly):
User -> Webcam Input -> Hand Detection -> Gesture Recognition -> Mouse Control -> Output Action

Run with:  python main.py
Quit with: press 'q' in the video window, or yank your mouse to a screen
           corner (PyAutoGUI failsafe).
"""

import time

from gesture_mouse.camera import Camera
from gesture_mouse.image_processor import ImageProcessor
from gesture_mouse.hand_detector import HandDetector
from gesture_mouse.gesture_recognizer import GestureRecognizer, Gesture
from gesture_mouse.mouse_control import MouseControlAPI
from gesture_mouse.smoothing import ExponentialSmoother
from gesture_mouse.window_manager import WindowManager
from gesture_mouse import config
import math


GESTURE_LABELS = {
    Gesture.NONE: "",
    Gesture.MOVE: "MOVE",
    Gesture.CLICK: "CLICK",
    Gesture.RIGHT_CLICK: "RIGHT CLICK",
    Gesture.DRAG: "DRAG",
    Gesture.SCROLL_UP: "SCROLL UP",
    Gesture.SCROLL_DOWN: "SCROLL DOWN",
    Gesture.MINIMIZE: "MINIMIZE",
    Gesture.MINIMIZE_ALL: "MINIMIZE ALL",
    Gesture.RESTORE_ALL: "RESTORE ALL",
    Gesture.RESTORE_LAST: "RESTORE LAST",
    Gesture.RESTORE_ACTIVE: "RESTORE ACTIVE",
}


def run():
    detector = HandDetector()
    recognizer = GestureRecognizer()
    mouse = MouseControlAPI()
    smoother = ExponentialSmoother()
    window_manager = WindowManager()

    prev_time = time.time()
    last_screen_pos = None
    prev_confirmed_gesture = Gesture.NONE

    with Camera() as camera:
        print("Gesture mouse control started. Press 'q' in the video window to quit.")
        while True:
            frame = camera.read_frame()
            if frame is None:
                print("Failed to read from camera. Exiting.")
                break

            frame = ImageProcessor.mirror(frame)
            rgb_frame = ImageProcessor.to_rgb(frame)

            results = detector.process(rgb_frame)
            all_landmarks = HandDetector.extract_all_landmarks(results)
            all_raw_hands = HandDetector.get_all_raw_hand_landmarks(results)

            gesture = Gesture.NONE
            landmarks = all_landmarks[0]["landmarks"] if all_landmarks else None

            multi_gesture = recognizer.recognize_multi(all_landmarks)
            
            if multi_gesture in (Gesture.MINIMIZE_ALL, Gesture.RESTORE_ALL, Gesture.RESTORE_LAST):
                gesture = multi_gesture
                if prev_confirmed_gesture != gesture:
                    if gesture == Gesture.MINIMIZE_ALL:
                        window_manager.minimize_all()
                    elif gesture == Gesture.RESTORE_ALL:
                        window_manager.restore_all()
                    elif gesture == Gesture.RESTORE_LAST:
                        window_manager.restore_last()
                # Clear single-hand recognizer state so it doesn't fire when mode ends
                recognizer.reset()
            elif landmarks is not None:
                gesture = recognizer.recognize(landmarks)

            if landmarks is not None:
                anchor_x, anchor_y = GestureRecognizer.get_cursor_anchor(landmarks)
                smooth_x, smooth_y = smoother.smooth(anchor_x, anchor_y)
                screen_x, screen_y = mouse.map_to_screen(smooth_x, smooth_y)

                def move_if_beyond_deadzone():
                    """
                    Skips the actual OS-level cursor move if it barely
                    shifted. This is what kills the residual vibration when
                    your hand is basically still - without it, even a
                    smoothed signal still nudges the cursor a pixel or two
                    every frame, which reads as a shake.
                    """
                    # Prevent pointer movement while transitioning to a fist or open hand
                    if recognizer._candidate_gesture in (Gesture.MINIMIZE, Gesture.MINIMIZE_ALL, Gesture.NONE, Gesture.RESTORE_ACTIVE) or \
                       recognizer._multi_candidate_gesture in (Gesture.MINIMIZE_ALL, Gesture.RESTORE_ALL, Gesture.RESTORE_LAST):
                        return
                        
                    nonlocal last_screen_pos
                    if last_screen_pos is None:
                        mouse.move_cursor(screen_x, screen_y)
                        last_screen_pos = (screen_x, screen_y)
                        return
                    dist = math.hypot(screen_x - last_screen_pos[0],
                                       screen_y - last_screen_pos[1])
                    if dist >= config.MOVE_DEADZONE_PX:
                        mouse.move_cursor(screen_x, screen_y)
                        last_screen_pos = (screen_x, screen_y)

                if gesture == Gesture.MOVE:
                    move_if_beyond_deadzone()
                    if mouse.is_dragging():
                        mouse.end_drag()

                elif gesture == Gesture.CLICK:
                    mouse.click()

                elif gesture == Gesture.RIGHT_CLICK:
                    mouse.right_click()

                elif gesture == Gesture.DRAG:
                    move_if_beyond_deadzone()
                    mouse.start_drag()

                elif gesture == Gesture.SCROLL_UP:
                    mouse.scroll("up")

                elif gesture == Gesture.SCROLL_DOWN:
                    mouse.scroll("down")

                elif gesture == Gesture.MINIMIZE:
                    # One-shot: only fire the instant we transition INTO a
                    # confirmed fist, not on every frame the fist is held.
                    # Without this, holding the fist for even half a second
                    # would spam the minimize hotkey repeatedly.
                    if prev_confirmed_gesture != Gesture.MINIMIZE:
                        window_manager.minimize_active()
                        
                elif gesture == Gesture.RESTORE_ACTIVE:
                    if prev_confirmed_gesture != Gesture.RESTORE_ACTIVE:
                        window_manager.restore_last_single()

            if all_raw_hands:
                for raw_hand in all_raw_hands:
                    ImageProcessor.draw_landmarks(
                        frame, raw_hand, detector.mp_hands, detector.mp_drawing
                    )

            if landmarks is None:
                recognizer.reset()
                smoother.reset()
                last_screen_pos = None
                if mouse.is_dragging():
                    mouse.end_drag()

            prev_confirmed_gesture = gesture

            now = time.time()
            fps = 1 / (now - prev_time) if now != prev_time else 0
            prev_time = now

            ImageProcessor.draw_gesture_label(frame, GESTURE_LABELS.get(gesture, ""))
            ImageProcessor.draw_fps(frame, fps)
            ImageProcessor.show("Gesture Mouse Control", frame)

            if ImageProcessor.wait_key(1) == ord('q'):
                break

    detector.close()
    ImageProcessor.destroy_all_windows()


if __name__ == "__main__":
    run()
