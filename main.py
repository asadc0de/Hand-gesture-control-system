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
from gesture_mouse.volume_control import VolumeController
from gesture_mouse.brightness_control import BrightnessController
from gesture_mouse.left_hand_controller import LeftHandController
from gesture_mouse import config
import math


GESTURE_LABELS = {
    Gesture.NONE: "",
    Gesture.MOVE: "MOVE POINTER",
    Gesture.CLICK: "LEFT CLICK",
    Gesture.RIGHT_CLICK: "RIGHT CLICK",
    Gesture.SCROLL: "SCROLL",
    Gesture.MINIMIZE: "MINIMIZE",
    Gesture.MINIMIZE_ALL: "MINIMIZE ALL",
    Gesture.RESTORE_ALL: "RESTORE ALL",
    Gesture.RESTORE_LAST: "RESTORE LAST",
    Gesture.RESTORE_ACTIVE: "RESTORE ACTIVE",
    Gesture.BACK: "BACK",
    Gesture.FORWARD: "FORWARD",
    Gesture.CLOSE: "CLOSE WINDOW",
    Gesture.TOGGLE_PRESENTATION_MODE: "TOGGLE PRESENTATION MODE",
    Gesture.TOGGLE_MEDIA_MODE: "TOGGLE MEDIA MODE",
    Gesture.SCREENSHOT: "SCREENSHOT",
    Gesture.LOCK: "LOCK SCREEN",
}


def run():
    detector = HandDetector()
    recognizer = GestureRecognizer()
    mouse = MouseControlAPI()
    smoother = ExponentialSmoother()
    window_manager = WindowManager()
    volume_controller = VolumeController()
    brightness_controller = BrightnessController()
    left_hand_controller = LeftHandController()

    prev_time = time.time()
    last_screen_pos = None
    last_scroll_y = None
    scroll_accumulator = 0.0
    
    # Presentation mode state
    presentation_mode = False
    presentation_swipe_x = None
    presentation_zoom_dist = None
    
    # Media mode state
    media_mode = False
    
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
            right_hand_landmarks = None
            left_hand_landmarks = None
            
            for hl in all_landmarks:
                if hl["label"] == "Right":
                    right_hand_landmarks = hl["landmarks"]
                elif hl["label"] == "Left":
                    left_hand_landmarks = hl["landmarks"]

            left_hand_controller.process_hand(
                left_hand_landmarks,
                media_mode=media_mode,
                presentation_mode=presentation_mode,
                mouse=mouse,
                volume_controller=volume_controller,
                brightness_controller=brightness_controller,
                frame=frame
            )

            landmarks = right_hand_landmarks

            multi_gesture = recognizer.recognize_multi(all_landmarks)
            
            if multi_gesture in (Gesture.MINIMIZE_ALL, Gesture.RESTORE_ALL, Gesture.RESTORE_LAST, Gesture.LOCK):
                gesture = multi_gesture
                if prev_confirmed_gesture != gesture:
                    smoother.reset()
                    last_screen_pos = None
                    if gesture == Gesture.MINIMIZE_ALL:
                        window_manager.minimize_all()
                    elif gesture == Gesture.RESTORE_ALL:
                        window_manager.restore_all()
                    elif gesture == Gesture.RESTORE_LAST:
                        window_manager.restore_last()
                    elif gesture == Gesture.LOCK:
                        mouse.lock_screen()
                # Clear single-hand recognizer state so it doesn't fire when mode ends
                recognizer.reset_single()
            elif landmarks is not None:
                gesture = recognizer.recognize(landmarks, left_hand_landmarks)

            if landmarks is not None:
                anchor_x, anchor_y = GestureRecognizer.get_cursor_anchor(landmarks)
                screen_x, screen_y = mouse.map_to_screen(anchor_x, anchor_y)

                if gesture == Gesture.TOGGLE_PRESENTATION_MODE:
                    if prev_confirmed_gesture != Gesture.TOGGLE_PRESENTATION_MODE:
                        smoother.reset()
                        last_screen_pos = None
                        presentation_mode = not presentation_mode
                        # Media mode and presentation mode should probably not be active simultaneously to avoid confusion
                        if presentation_mode:
                            media_mode = False
                        print(f"Presentation Mode: {'ON' if presentation_mode else 'OFF'}")

                elif gesture == Gesture.TOGGLE_MEDIA_MODE:
                    if prev_confirmed_gesture != Gesture.TOGGLE_MEDIA_MODE:
                        smoother.reset()
                        last_screen_pos = None
                        media_mode = not media_mode
                        if media_mode:
                            presentation_mode = False
                        print(f"Media Mode: {'ON' if media_mode else 'OFF'}")

                elif presentation_mode:
                    # In presentation mode, we hijack RESTORE_ACTIVE (Flat Palm) for Swiping
                    if gesture == Gesture.RESTORE_ACTIVE:
                        if presentation_swipe_x is None:
                            presentation_swipe_x = screen_x
                        else:
                            delta_x = screen_x - presentation_swipe_x
                            if abs(delta_x) > config.SWIPE_SENSITIVITY:
                                if delta_x > 0:
                                    print("SWIPE RIGHT detected! (Next Slide)")
                                    mouse.next_slide()
                                else:
                                    print("SWIPE LEFT detected! (Prev Slide)")
                                    mouse.prev_slide()
                                # Reset swipe baseline so we don't trigger multiple times instantly
                                presentation_swipe_x = screen_x
                    else:
                        presentation_swipe_x = None
                    
                    # Pinch to Zoom: Active when middle, ring, pinky are folded
                    middle_extended = GestureRecognizer.is_finger_extended(landmarks, config.MIDDLE_TIP, config.MIDDLE_PIP)
                    ring_extended = GestureRecognizer.is_finger_extended(landmarks, config.RING_TIP, config.RING_PIP)
                    pinky_extended = GestureRecognizer.is_finger_extended(landmarks, config.PINKY_TIP, config.PINKY_PIP)

                    if not middle_extended and not ring_extended and not pinky_extended:
                        thumb = landmarks[config.THUMB_TIP]
                        index = landmarks[config.INDEX_TIP]
                        dist = math.hypot(thumb[0] - index[0], thumb[1] - index[1])
                        if presentation_zoom_dist is None:
                            presentation_zoom_dist = dist
                        else:
                            delta_dist = dist - presentation_zoom_dist
                            if abs(delta_dist) >= config.ZOOM_SENSITIVITY:
                                steps = int(abs(delta_dist) / config.ZOOM_SENSITIVITY)
                                zoom_amount = 120 * steps if delta_dist > 0 else -120 * steps
                                mouse.zoom(zoom_amount)
                                if delta_dist > 0:
                                    presentation_zoom_dist += steps * config.ZOOM_SENSITIVITY
                                else:
                                    presentation_zoom_dist -= steps * config.ZOOM_SENSITIVITY
                    else:
                        presentation_zoom_dist = None

                # Normal operation when not in presentation mode
                elif gesture == Gesture.SCROLL:
                    if prev_confirmed_gesture != Gesture.SCROLL:
                        smoother.reset()
                        last_screen_pos = None

                    if last_scroll_y is None:
                        last_scroll_y = screen_y
                    else:
                        delta_y = screen_y - last_scroll_y
                        last_scroll_y = screen_y
                        
                        # hand moves up -> delta_y is negative -> we want positive scroll (up)
                        # We use config.SCROLL_SENSITIVITY as a divisor for delta_y
                        # e.g., if hand moves 40 pixels, scroll by SCROLL_AMOUNT
                        scroll_multiplier = config.SCROLL_AMOUNT / max(1.0, config.SCROLL_SENSITIVITY)
                        scroll_accumulator += -delta_y * scroll_multiplier
                        
                        # Apply scroll when accumulator reaches at least one notch (e.g., 10)
                        if abs(scroll_accumulator) >= 10:
                            mouse.scroll(int(scroll_accumulator))
                            scroll_accumulator = 0.0

                elif gesture == Gesture.MINIMIZE:
                    # One-shot: only fire the instant we transition INTO a confirmed fist
                    if prev_confirmed_gesture != Gesture.MINIMIZE:
                        smoother.reset()
                        last_screen_pos = None
                        window_manager.minimize_active()
                        
                elif gesture == Gesture.RESTORE_ACTIVE:
                    if prev_confirmed_gesture != Gesture.RESTORE_ACTIVE:
                        smoother.reset()
                        last_screen_pos = None
                        window_manager.restore_last_single()

                elif gesture == Gesture.BACK:
                    if prev_confirmed_gesture != Gesture.BACK:
                        smoother.reset()
                        last_screen_pos = None
                        mouse.back()

                elif gesture == Gesture.FORWARD:
                    if prev_confirmed_gesture != Gesture.FORWARD:
                        smoother.reset()
                        last_screen_pos = None
                        mouse.forward()

                elif gesture == Gesture.CLOSE:
                    if prev_confirmed_gesture != Gesture.CLOSE:
                        smoother.reset()
                        last_screen_pos = None
                        mouse.close_window()

                elif gesture == Gesture.SCREENSHOT:
                    if prev_confirmed_gesture != Gesture.SCREENSHOT:
                        smoother.reset()
                        last_screen_pos = None
                        mouse.take_screenshot()

                elif gesture == Gesture.MOVE:
                    smoothed_x, smoothed_y = smoother.smooth(anchor_x, anchor_y)
                    screen_x, screen_y = mouse.map_to_screen(smoothed_x, smoothed_y)

                    if not mouse.is_cursor_locked():
                        if last_screen_pos is None or math.hypot(
                            screen_x - last_screen_pos[0], screen_y - last_screen_pos[1]
                        ) >= config.MOVE_DEADZONE_PX:
                            mouse.move_cursor(screen_x, screen_y)
                            last_screen_pos = (screen_x, screen_y)

                else:
                    # Transient NONE or unconfirmed posture:
                    # Do NOT move cursor, but DO NOT call smoother.reset() so EMA filter
                    # history remains intact and resumption to MOVE is completely smooth.
                    pass

            if all_raw_hands:
                for raw_hand in all_raw_hands:
                    ImageProcessor.draw_landmarks(
                        frame, raw_hand, detector.mp_hands, detector.mp_drawing
                    )

            if landmarks is None:
                recognizer.reset()
                smoother.reset()
                last_screen_pos = None

            if gesture != Gesture.SCROLL:
                last_scroll_y = None
                scroll_accumulator = 0.0

            prev_confirmed_gesture = gesture

            now = time.time()
            fps = 1 / (now - prev_time) if now != prev_time else 0
            prev_time = now

            label = GESTURE_LABELS.get(gesture, "")
            if presentation_mode:
                label = f"[PRESENTATION MODE] {label}"
            elif media_mode:
                label = f"[MEDIA MODE] {label}"
                
            ImageProcessor.draw_gesture_label(frame, label)
            ImageProcessor.draw_fps(frame, fps)
            ImageProcessor.show("Gesture Mouse Control", frame)

            if ImageProcessor.wait_key(1) == ord('q'):
                break

    detector.close()
    ImageProcessor.destroy_all_windows()


if __name__ == "__main__":
    run()
