"""
ImageProcessor module.
Handles all raw frame preprocessing: mirroring, color conversion, and the
on-screen overlay drawing (skeleton + gesture label). Keeping drawing code
here (instead of jammed into main.py) keeps HandDetector and MouseControlAPI
free of any OpenCV drawing concerns.
"""

import cv2


class ImageProcessor:
    @staticmethod
    def mirror(frame):
        """Flips the frame horizontally so movement feels natural (mirror-like)."""
        return cv2.flip(frame, 1)

    @staticmethod
    def to_rgb(frame):
        """MediaPipe expects RGB; OpenCV captures in BGR."""
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    @staticmethod
    def draw_landmarks(frame, hand_landmarks, mp_hands, mp_drawing):
        """Draws the hand skeleton on the frame in place."""
        mp_drawing.draw_landmarks(
            frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
        )
        return frame

    @staticmethod
    def draw_gesture_label(frame, gesture_name: str, position=(20, 40)):
        """Draws the currently recognized gesture as text overlay."""
        cv2.putText(
            frame, gesture_name, position,
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA
        )
        return frame

    @staticmethod
    def draw_fps(frame, fps: float, position=(20, 80)):
        cv2.putText(
            frame, f"FPS: {fps:.0f}", position,
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA
        )
        return frame

    @staticmethod
    def show(window_name, frame):
        cv2.imshow(window_name, frame)

    @staticmethod
    def wait_key(delay_ms: int = 1):
        return cv2.waitKey(delay_ms) & 0xFF

    @staticmethod
    def destroy_all_windows():
        cv2.destroyAllWindows()
