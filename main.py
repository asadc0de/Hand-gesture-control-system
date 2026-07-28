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
from gesture_mouse.volume_control import VolumeController
from gesture_mouse.brightness_control import BrightnessController
from gesture_mouse import config
import math


GESTURE_LABELS = {
    Gesture.NONE: "",
    Gesture.MOVE: "MOVE",
    Gesture.CLICK: "CLICK",
    Gesture.RIGHT_CLICK: "RIGHT CLICK",
    Gesture.DRAG: "DRAG",
    Gesture.SCROLL: "SCROLL",
    Gesture.MINIMIZE: "MINIMIZE",
    Gesture.MINIMIZE_ALL: "MINIMIZE ALL",
    Gesture.RESTORE_ALL: "RESTORE ALL",
    Gesture.RESTORE_LAST: "RESTORE LAST",
    Gesture.RESTORE_ACTIVE: "RESTORE ACTIVE",
    Gesture.BACK: "BACK",
    Gesture.FORWARD: "FORWARD",
    Gesture.DOUBLE_CLICK: "DOUBLE CLICK",
    Gesture.CLOSE: "CLOSE WINDOW",
    Gesture.TOGGLE_PRESENTATION_MODE: "TOGGLE PRESENTATION MODE",
    Gesture.TOGGLE_MEDIA_MODE: "TOGGLE MEDIA MODE",
    Gesture.SCREENSHOT: "SCREENSHOT",
}


def run():
    detector = HandDetector()
    recognizer = GestureRecognizer()
    mouse = MouseControlAPI()
    smoother = ExponentialSmoother()
    window_manager = WindowManager()
    volume_controller = VolumeController()
    brightness_controller = BrightnessController()

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
            
            for hl in all_landmarks:
                if hl["label"] == "Right":
                    right_hand_landmarks = hl["landmarks"]
                elif hl["label"] == "Left":
                    wrist = hl["landmarks"][config.WRIST]
                    middle_mcp = hl["landmarks"][config.MIDDLE_MCP]
                    
                    dy = abs(wrist[1] - middle_mcp[1])
                    dx = abs(wrist[0] - middle_mcp[0])
                    
                    # If hand is vertical (fingers pointing up) -> Volume
                    # If hand is horizontal (fingers pointing sideways) -> Brightness
                    if media_mode:
                        if dy > dx:
                            volume_controller.process_hand(hl["landmarks"], frame)
                            volume_controller.draw_overlay(frame)
                        else:
                            brightness_controller.process_hand(hl["landmarks"], frame)
                            brightness_controller.draw_overlay(frame)

            landmarks = right_hand_landmarks

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
                recognizer.reset_single()
            elif landmarks is not None:
                gesture = recognizer.recognize(landmarks)

            if landmarks is not None:
                anchor_x, anchor_y = GestureRecognizer.get_cursor_anchor(landmarks)
                screen_x, screen_y = mouse.map_to_screen(anchor_x, anchor_y)

                def move_if_beyond_deadzone():
                    # Prevent pointer movement while transitioning to a fist or open hand
                    if recognizer._candidate_gesture in (Gesture.MINIMIZE, Gesture.MINIMIZE_ALL, Gesture.NONE, Gesture.RESTORE_ACTIVE, Gesture.BACK, Gesture.FORWARD, Gesture.DOUBLE_CLICK, Gesture.CLOSE, Gesture.TOGGLE_PRESENTATION_MODE) or \
                       recognizer._multi_candidate_gesture in (Gesture.MINIMIZE_ALL, Gesture.RESTORE_ALL, Gesture.RESTORE_LAST):
                        return
                        
                    mouse.move_cursor(screen_x, screen_y)

                if gesture == Gesture.TOGGLE_PRESENTATION_MODE:
                    if prev_confirmed_gesture != Gesture.TOGGLE_PRESENTATION_MODE:
                        presentation_mode = not presentation_mode
                        # Media mode and presentation mode should probably not be active simultaneously to avoid confusion
                        if presentation_mode:
                            media_mode = False
                        print(f"Presentation Mode: {'ON' if presentation_mode else 'OFF'}")

                elif gesture == Gesture.TOGGLE_MEDIA_MODE:
                    if prev_confirmed_gesture != Gesture.TOGGLE_MEDIA_MODE:
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
                    
                    # Hijack gestures for Pinch to Zoom
                    # (Allowing MINIMIZE/NONE prevents the zoom from dropping out when the index finger naturally curls during a pinch)
                    if gesture in (Gesture.MOVE, Gesture.DRAG, Gesture.CLICK, Gesture.MINIMIZE, Gesture.NONE):
                        thumb = landmarks[config.THUMB_TIP]
                        index = landmarks[config.INDEX_TIP]
                        dist = math.hypot(thumb[0] - index[0], thumb[1] - index[1])
                        if presentation_zoom_dist is None:
                            presentation_zoom_dist = dist
                        else:
                            delta_dist = dist - presentation_zoom_dist
                            if abs(delta_dist) > config.ZOOM_SENSITIVITY:
                                steps = int(abs(delta_dist) / config.ZOOM_SENSITIVITY)
                                zoom_amount = 120 * steps if delta_dist > 0 else -120 * steps
                                print(f"ZOOM detected! Amount: {zoom_amount}")
                                mouse.zoom(zoom_amount)
                                # Advance the baseline by the amount consumed to prevent dropping fast movements
                                if delta_dist > 0:
                                    presentation_zoom_dist += steps * config.ZOOM_SENSITIVITY
                                else:
                                    presentation_zoom_dist -= steps * config.ZOOM_SENSITIVITY
                    else:
                        presentation_zoom_dist = None

                # Normal operation when not in presentation mode
                elif gesture == Gesture.MOVE:
                    move_if_beyond_deadzone()

                elif gesture == Gesture.CLICK:
                    mouse.click()

                elif gesture == Gesture.RIGHT_CLICK:
                    if prev_confirmed_gesture != Gesture.RIGHT_CLICK:
                        mouse.right_click()

                elif gesture == Gesture.DRAG:
                    move_if_beyond_deadzone()
                    mouse.start_drag()

                elif gesture == Gesture.SCROLL:
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
                    # One-shot: only fire the instant we transition INTO a
                    # confirmed fist, not on every frame the fist is held.
                    # Without this, holding the fist for even half a second
                    # would spam the minimize hotkey repeatedly.
                    if prev_confirmed_gesture != Gesture.MINIMIZE:
                        window_manager.minimize_active()
                        
                elif gesture == Gesture.RESTORE_ACTIVE:
                    if prev_confirmed_gesture != Gesture.RESTORE_ACTIVE:
                        window_manager.restore_last_single()

                elif gesture == Gesture.BACK:
                    if prev_confirmed_gesture != Gesture.BACK:
                        mouse.back()

                elif gesture == Gesture.FORWARD:
                    if prev_confirmed_gesture != Gesture.FORWARD:
                        mouse.forward()

                elif gesture == Gesture.DOUBLE_CLICK:
                    mouse.double_click()

                elif gesture == Gesture.CLOSE:
                    if prev_confirmed_gesture != Gesture.CLOSE:
                        mouse.close_window()

                elif gesture == Gesture.SCREENSHOT:
                    if prev_confirmed_gesture != Gesture.SCREENSHOT:
                        mouse.take_screenshot()

            if gesture != Gesture.DRAG and mouse.is_dragging():
                mouse.end_drag()

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
