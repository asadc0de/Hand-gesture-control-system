"""
Ninja Fruit - Hand Edition
==========================
Run: python main.py

Controls:
  - Show your hand to the webcam, slice fruit with your INDEX FINGERTIP.
  - SPACE  : start / restart
  - Q      : end the current round and see your score
  - ESC    : quit

Endless mode: fruit rises from the bottom forever, nothing falls back down
and there are no bombs or lives - just keep slicing for points until you
decide to stop.

This is a standalone project (separate from the FYP mouse-control system).
It reuses the same idea - OpenCV + MediaPipe hand tracking - but renders the
game itself with pygame for smooth, juicy visuals (particles, glow trail,
screen shake) instead of drawing directly on raw OpenCV frames.
"""

import sys
import cv2
import pygame

from game import constants as C
from game.hand_tracker import HandTracker
from game.game import NinjaFruitGame, MENU, PLAYING, ROUND_END


def main():
    pygame.init()
    pygame.display.set_caption("Ninja Fruit - Hand Edition")
    screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    cap = cv2.VideoCapture(C.CAM_INDEX)
    if not cap.isOpened():
        print("ERROR: could not open webcam. Check CAM_INDEX in game/constants.py")
        sys.exit(1)

    tracker = HandTracker()
    game = NinjaFruitGame(screen)

    running = True
    while running:
        dt = clock.tick(C.FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if game.state in (MENU, ROUND_END):
                        game.start()
                elif event.key == pygame.K_q:
                    game.end_round()

        ok, frame = cap.read()
        finger_points = []
        camera_surface = None
        if ok:
            if C.MIRROR_CAMERA:
                frame = cv2.flip(frame, 1)
            tips_norm = tracker.process(frame)
            finger_points = [(x * C.SCREEN_WIDTH, y * C.SCREEN_HEIGHT) for x, y in tips_norm]
            camera_surface = game.camera_frame_to_surface(frame)

        game.update(dt, finger_points)
        game.draw(camera_surface)
        pygame.display.flip()

    cap.release()
    tracker.close()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
