"""
Fruit game objects.

Sprites are drawn procedurally with pygame (radial shading, stem, leaf,
highlight) so the game needs zero external image assets. Each fruit rises
straight up at a steady speed with a gentle side-to-side wobble - endless
mode, so nothing ever falls back down. Knows how to render itself whole,
and produces two cosmetic falling halves once sliced.
"""

import math
import random
import pygame

from . import constants as C

_SPRITE_CACHE = {}


def _shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def _build_fruit_sprite(kind, radius):
    """Procedurally render one fruit as a pygame.Surface with per-pixel alpha."""
    size = radius * 2 + 8
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    colors = C.FRUIT_COLORS[kind]
    body = colors["body"]

    # base radial shading: several concentric circles going darker outward
    steps = 10
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        factor = 0.75 + 0.5 * (i / steps)
        pygame.draw.circle(surf, _shade(body, factor), (cx, cy), r)

    # watermelon stripes
    if kind == "watermelon":
        stripe_color = _shade(body, 0.55)
        for a in range(-2, 3):
            offset = a * radius * 0.32
            pygame.draw.ellipse(
                surf, stripe_color,
                (cx + offset - 4, cy - radius + 4, 8, radius * 2 - 8)
            )

    # banana shape override: draw a curved capsule instead of a circle
    if kind == "banana":
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        rect = pygame.Rect(cx - radius, cy - radius * 0.55, radius * 2, radius * 1.1)
        pygame.draw.arc(surf, body, rect, math.radians(200), math.radians(340), width=int(radius * 0.55))
        pygame.draw.circle(surf, body, (int(rect.left + 6), int(rect.centery + 6)), int(radius * 0.28))
        pygame.draw.circle(surf, body, (int(rect.right - 6), int(rect.centery - 10)), int(radius * 0.24))

    # soft highlight (glossy shine)
    highlight = pygame.Surface((size, size), pygame.SRCALPHA)
    hl_r = int(radius * 0.35)
    pygame.draw.circle(highlight, (255, 255, 255, 90), (cx - radius // 3, cy - radius // 2), hl_r)
    surf.blit(highlight, (0, 0))

    # stem + leaf for round fruits
    if kind != "banana":
        stem_color = (90, 60, 30)
        pygame.draw.rect(surf, stem_color, (cx - 3, cy - radius - 6, 6, 12), border_radius=3)
        leaf_color = (60, 150, 60)
        leaf_points = [
            (cx + 4, cy - radius - 2),
            (cx + 22, cy - radius - 14),
            (cx + 10, cy - radius + 4),
        ]
        pygame.draw.polygon(surf, leaf_color, leaf_points)

    return surf


def _get_sprite(kind, radius):
    key = (kind, radius)
    if key not in _SPRITE_CACHE:
        _SPRITE_CACHE[key] = _build_fruit_sprite(kind, radius)
    return _SPRITE_CACHE[key]


class Fruit:
    def __init__(self, x, y, vx, vy, kind=None, radius=None):
        self.kind = kind or random.choice(C.FRUIT_TYPES)
        self.radius = radius or random.randint(C.FRUIT_RADIUS_MIN, C.FRUIT_RADIUS_MAX)
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.rotation = random.uniform(0, 360)
        self.angular_velocity = random.uniform(-140, 140)
        self.wobble_phase = random.uniform(0, 6.283)
        self.sliced = False
        self.alive = True
        self.sprite = _get_sprite(self.kind, self.radius)

    def update(self, dt):
        # gentle horizontal wobble instead of gravity - fruit rises forever
        self.wobble_phase += dt * 2.2
        self.x += (self.vx + math.sin(self.wobble_phase) * C.FRUIT_DRIFT_X) * dt
        self.y += self.vy * dt
        self.rotation = (self.rotation + self.angular_velocity * dt) % 360
        if self.y + self.radius < -60:
            self.alive = False

    def draw(self, surface):
        rotated = pygame.transform.rotate(self.sprite, self.rotation)
        rect = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rect)

    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

    def flesh_color(self):
        return C.FRUIT_COLORS[self.kind]["flesh"]

    def body_color(self):
        return C.FRUIT_COLORS[self.kind]["body"]


class FruitHalf:
    """A visual-only piece used right after a fruit is sliced - drifts apart
    and fades, no collision, purely cosmetic to sell the 'slice' moment."""

    def __init__(self, x, y, vx, vy, sprite, side, life=0.6):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.sprite = sprite
        self.side = side  # -1 left half, 1 right half
        self.rotation = 0
        self.angular_velocity = 220 * side
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.vy += C.HALF_GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rotation += self.angular_velocity * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        w, h = self.sprite.get_size()
        half_w = w // 2
        clip_rect = pygame.Rect(half_w if self.side > 0 else 0, 0, half_w, h)
        piece = self.sprite.subsurface(clip_rect).copy()
        t = max(0.0, self.life / self.max_life)
        piece.set_alpha(int(255 * t))
        rotated = pygame.transform.rotate(piece, self.rotation)
        rect = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rect)


def spawn_launch_params(screen_width, screen_height):
    """Compute a randomized (x, y, vx, vy) so the fruit enters from the
    bottom edge and rises straight up forever with a small wobble drift."""
    x = random.uniform(screen_width * 0.10, screen_width * 0.90)
    y = screen_height + 40
    vy = -random.uniform(C.FRUIT_RISE_SPEED_MIN, C.FRUIT_RISE_SPEED_MAX)
    vx = 0.0  # horizontal motion comes entirely from the wobble in Fruit.update
    return x, y, vx, vy
