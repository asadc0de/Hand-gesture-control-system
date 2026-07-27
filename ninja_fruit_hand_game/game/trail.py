"""
Trail: keeps a short rolling history of a fingertip's position and renders it
as a glowing, tapering blade streak. Also exposes the last two points so the
game can test line-segment vs circle collision (needed so fast swipes don't
"tunnel" through a fruit between two frames).
"""

import time
import pygame

from . import constants as C


class Trail:
    def __init__(self, color=(255, 255, 255)):
        self.points = []   # list of (x, y, timestamp)
        self.color = color

    def add_point(self, x, y):
        now = time.time()
        self.points.append((x, y, now))
        if len(self.points) > C.TRAIL_MAX_POINTS:
            self.points.pop(0)
        self._prune(now)

    def clear(self):
        self.points = []

    def _prune(self, now=None):
        now = now or time.time()
        self.points = [p for p in self.points if now - p[2] < C.TRAIL_POINT_LIFETIME]

    def last_segment(self):
        """Return the most recent 2 points as ((x1,y1),(x2,y2)) or None."""
        self._prune()
        if len(self.points) < 2:
            return None
        (x1, y1, _), (x2, y2, _) = self.points[-2], self.points[-1]
        return (x1, y1), (x2, y2)

    def draw(self, surface):
        self._prune()
        pts = self.points
        n = len(pts)
        if n < 2:
            return
        now = time.time()
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for i in range(1, n):
            x1, y1, t1 = pts[i - 1]
            x2, y2, t2 = pts[i]
            age = now - t2
            fade = max(0.0, 1.0 - age / C.TRAIL_POINT_LIFETIME)
            progress = i / n  # newer segments (larger i) are thicker/brighter
            width = max(1, int(9 * progress * fade))
            alpha = int(255 * fade * (0.4 + 0.6 * progress))
            if width <= 0 or alpha <= 0:
                continue
            # glow pass (soft, wide, translucent) then a bright core line
            pygame.draw.line(overlay, (*self.color, alpha // 3), (x1, y1), (x2, y2), width + 6)
            pygame.draw.line(overlay, (*self.color, alpha), (x1, y1), (x2, y2), width)
        surface.blit(overlay, (0, 0))
