"""
NinjaFruitGame
--------------
Endless mode: fruit spawns from the bottom and rises forever, you slice it
with your index fingertip for points, nothing ever punishes you for missing.
No bombs, no lives - it's a pure score-attack sandbox. You end a run
yourself (press Q) whenever you want to see your score summary.

Owns the state machine (MENU / PLAYING / ROUND_END), spawns fruit, runs
physics, tests slice collisions against each tracked fingertip's trail, and
draws everything - camera background, fruit, particles, slash flash, trail,
HUD.

Kept deliberately decoupled from HandTracker: this class only receives a
list of (x, y) fingertip positions in *screen* pixel coordinates each frame.
Where those positions come from (webcam + MediaPipe, a mouse, a replay file)
is none of its business.
"""

import math
import random
import time

import cv2
import numpy as np
import pygame

from . import constants as C
from .fruit import Fruit, FruitHalf, spawn_launch_params
from .particles import ParticleSystem
from .trail import Trail
from .sounds import SoundBank

MENU, PLAYING, ROUND_END = "menu", "playing", "round_end"


def _segment_hits_circle(p1, p2, center, radius):
    """True if segment p1->p2 passes within `radius` of `center`."""
    x1, y1 = p1
    x2, y2 = p2
    cx, cy = center
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        dist_sq = (x1 - cx) ** 2 + (y1 - cy) ** 2
        return dist_sq <= radius * radius
    t = ((cx - x1) * dx + (cy - y1) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    dist_sq = (closest_x - cx) ** 2 + (closest_y - cy) ** 2
    return dist_sq <= radius * radius


class NinjaFruitGame:
    def __init__(self, screen):
        self.screen = screen
        self.font_big = pygame.font.SysFont("arialrounded,arial", 72, bold=True)
        self.font_med = pygame.font.SysFont("arialrounded,arial", 40, bold=True)
        self.font_small = pygame.font.SysFont("arial", 26)
        self.font_combo = pygame.font.SysFont("arial", 34, bold=True)

        self.particles = ParticleSystem()
        self.trails = {}  # hand index -> Trail
        self.sounds = SoundBank()
        self.high_score = 0

        self._bg_cache = self._build_background()
        self.reset()

    # ---------- lifecycle ----------

    def reset(self):
        self.state = MENU
        self.score = 0
        self.combo_count = 0
        self.combo_timer = 0.0
        self.best_combo = 0
        self.sliced_count = 0
        self.fruits = []
        self.halves = []
        self.spawn_timer = 0.0
        self.elapsed = 0.0
        self.trails = {}
        self.particles = ParticleSystem()

    def start(self):
        self.reset()
        self.state = PLAYING

    def end_round(self):
        if self.state == PLAYING:
            self.high_score = max(self.high_score, self.score)
            self.state = ROUND_END

    # ---------- background ----------

    def _build_background(self):
        """Pre-render a smooth vertical gradient once instead of per frame."""
        surf = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        top = pygame.Color(*C.COLOR_BG_TOP)
        bottom = pygame.Color(*C.COLOR_BG_BOTTOM)
        for y in range(C.SCREEN_HEIGHT):
            t = y / C.SCREEN_HEIGHT
            color = top.lerp(bottom, t)
            pygame.draw.line(surf, color, (0, y), (C.SCREEN_WIDTH, y))
        return surf

    def camera_frame_to_surface(self, bgr_frame):
        """Convert an OpenCV BGR frame to a pygame Surface sized to the screen."""
        frame = cv2.resize(bgr_frame, (C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        surf = pygame.surfarray.make_surface(frame)
        surf = pygame.transform.flip(surf, True, False)
        return surf

    # ---------- spawning ----------

    def _difficulty_t(self):
        return min(1.0, self.elapsed / C.DIFFICULTY_RAMP_TIME)

    def _spawn_wave(self):
        count = 1
        if random.random() < C.MULTI_SPAWN_CHANCE:
            count = random.choice([2, 3])
        for _ in range(count):
            x, y, vx, vy = spawn_launch_params(C.SCREEN_WIDTH, C.SCREEN_HEIGHT)
            self.fruits.append(Fruit(x, y, vx, vy))

    # ---------- update ----------

    def update(self, dt, finger_points):
        self.elapsed += dt
        self.particles.update(dt)
        self.halves = [h for h in self.halves if h.update(dt)]

        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo_count = 0

        # keep one Trail per tracked hand index, feed it this frame's point
        active_indices = set(range(len(finger_points)))
        for idx in list(self.trails.keys()):
            if idx not in active_indices:
                del self.trails[idx]
        for idx, (x, y) in enumerate(finger_points):
            if idx not in self.trails:
                self.trails[idx] = Trail(color=(255, 255, 255))
            self.trails[idx].add_point(x, y)

        if self.state != PLAYING:
            return

        # difficulty ramps spawn interval down over time (more fruit, not harder to miss)
        t = self._difficulty_t()
        interval = C.SPAWN_INTERVAL_START + (C.SPAWN_INTERVAL_MIN - C.SPAWN_INTERVAL_START) * t
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self._spawn_wave()
            self.spawn_timer = interval

        for f in self.fruits:
            f.update(dt)

        self._check_slices()

        # fruit that rises off the top just disappears - no penalty, endless mode
        self.fruits = [f for f in self.fruits if f.alive]

    def _check_slices(self):
        segments = []
        for trail in self.trails.values():
            seg = trail.last_segment()
            if seg:
                segments.append(seg)
        if not segments:
            return

        for f in self.fruits:
            if f.sliced:
                continue
            for p1, p2 in segments:
                if _segment_hits_circle(p1, p2, (f.x, f.y), f.radius):
                    self._slice_fruit(f, p1, p2)
                    break

    def _slice_fruit(self, f, p1, p2):
        f.sliced = True
        f.alive = False

        self.combo_count += 1
        self.combo_timer = 1.0
        self.best_combo = max(self.best_combo, self.combo_count)
        self.sliced_count += 1
        points = 10 * max(1, self.combo_count)
        self.score += points

        # slash flash aligned to the direction the finger was actually moving
        angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        self.particles.spawn_slash(f.x, f.y, angle, f.radius * 2.6, color=C.SLASH_COLOR, life=C.SLASH_LIFE)

        color = f.flesh_color()
        self.particles.spawn_burst(f.x, f.y, color, count=22)
        label = f"+{points}" if self.combo_count <= 1 else f"+{points}  x{self.combo_count} combo!"
        self.particles.spawn_text(f.x, f.y - f.radius, label, C.COLOR_COMBO, self.font_combo)
        self.sounds.play_slice()

        # spawn two flying halves for a satisfying cut animation, kicked apart
        # roughly along the swipe direction for extra "that was a real cut" feel
        perp_x, perp_y = math.cos(angle + math.pi / 2), math.sin(angle + math.pi / 2)
        kick = 170
        self.halves.append(FruitHalf(f.x - perp_x * 6, f.y - perp_y * 6, f.vx - perp_x * kick, f.vy - perp_y * kick - 40, f.sprite, side=-1))
        self.halves.append(FruitHalf(f.x + perp_x * 6, f.y + perp_y * 6, f.vx + perp_x * kick, f.vy + perp_y * kick - 40, f.sprite, side=1))

    # ---------- draw ----------

    def draw(self, camera_surface=None):
        base = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        base.blit(self._bg_cache, (0, 0))

        if camera_surface is not None:
            dimmed = camera_surface.copy()
            dark = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 140))
            dimmed.blit(dark, (0, 0))
            base.blit(dimmed, (0, 0))

        for f in self.fruits:
            f.draw(base)
        for h in self.halves:
            h.draw(base)

        for trail in self.trails.values():
            trail.draw(base)

        self.particles.draw(base)

        self._draw_hud(base)

        if self.state == MENU:
            self._draw_menu(base)
        elif self.state == ROUND_END:
            self._draw_round_end(base)

        self.screen.blit(base, (0, 0))

    def _draw_hud(self, surf):
        score_surf = self.font_med.render(f"Score: {self.score}", True, C.COLOR_HUD_TEXT)
        surf.blit(score_surf, (24, 20))

        if self.high_score > 0:
            hs_surf = self.font_small.render(f"Best: {self.high_score}", True, (200, 200, 200))
            surf.blit(hs_surf, (C.SCREEN_WIDTH - hs_surf.get_width() - 24, 24))

        if self.combo_count > 1:
            combo_surf = self.font_small.render(f"Combo x{self.combo_count}", True, C.COLOR_COMBO)
            surf.blit(combo_surf, (24, 70))

        if self.state == PLAYING:
            hint = self.font_small.render("Q: end round    ESC: quit", True, (200, 200, 200))
            surf.blit(hint, (24, C.SCREEN_HEIGHT - 40))

    def _panel(self, surf, alpha=170):
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surf.blit(overlay, (0, 0))

    def _draw_menu(self, surf):
        self._panel(surf)
        title = self.font_big.render("NINJA FRUIT", True, (255, 255, 255))
        surf.blit(title, title.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 - 120)))
        sub = self.font_med.render("Hand Edition", True, C.COLOR_COMBO)
        surf.blit(sub, sub.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 - 55)))
        instr = self.font_small.render(
            "Slice rising fruit with your index fingertip - endless mode!", True, (230, 230, 230))
        surf.blit(instr, instr.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 + 10)))
        prompt = self.font_med.render("Press SPACE to start", True, (255, 255, 255))
        alpha = int(180 + 75 * abs((time.time() * 2) % 2 - 1))
        prompt.set_alpha(alpha)
        surf.blit(prompt, prompt.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 + 90)))

    def _draw_round_end(self, surf):
        self._panel(surf)
        title = self.font_big.render("ROUND COMPLETE", True, C.COLOR_COMBO)
        surf.blit(title, title.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 - 100)))
        score_line = self.font_med.render(
            f"Score: {self.score}   Fruit sliced: {self.sliced_count}   Best combo: x{self.best_combo}",
            True, (255, 255, 255))
        surf.blit(score_line, score_line.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 - 20)))
        prompt = self.font_med.render("Press SPACE to play again", True, (255, 255, 255))
        surf.blit(prompt, prompt.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 + 50)))
        quit_hint = self.font_small.render("Press ESC to quit", True, (200, 200, 200))
        surf.blit(quit_hint, quit_hint.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 + 100)))
