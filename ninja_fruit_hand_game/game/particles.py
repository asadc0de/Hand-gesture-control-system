"""
Small particle system for juice splashes, bomb flashes and score pop-text.
Kept dependency-free (just pygame) so it's easy to drop into other projects.
"""

import math
import random
import pygame


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "gravity")

    def __init__(self, x, y, vx, vy, life, color, size, gravity=900.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        t = max(0.0, self.life / self.max_life)
        alpha = int(255 * t)
        radius = max(1, int(self.size * t))
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (radius, radius), radius)
        surface.blit(s, (self.x - radius, self.y - radius))


class FloatingText:
    """Small combo / score pop-up that drifts up and fades."""

    def __init__(self, x, y, text, color, font, life=0.7):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.font = font
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.y -= 55 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        t = max(0.0, self.life / self.max_life)
        alpha = int(255 * t)
        rendered = self.font.render(self.text, True, self.color)
        rendered.set_alpha(alpha)
        surface.blit(rendered, (self.x - rendered.get_width() / 2, self.y))


class SliceFlash:
    """A quick bright blade-streak flashed at the exact point of a cut,
    oriented along the direction the finger was swiping. This is the 'I am
    cutting this' feedback - separate from the longer-lived finger trail."""

    def __init__(self, x, y, angle_rad, length, color=(255, 255, 255), life=0.16):
        self.x, self.y = x, y
        self.angle = angle_rad
        self.length = length
        self.color = color
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        t = max(0.0, self.life / self.max_life)
        half = self.length / 2
        dx = math.cos(self.angle) * half
        dy = math.sin(self.angle) * half
        p1 = (self.x - dx, self.y - dy)
        p2 = (self.x + dx, self.y + dy)

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        # outer glow, wide and soft
        glow_alpha = int(140 * t)
        pygame.draw.line(overlay, (*self.color, glow_alpha), p1, p2, int(16 * t) + 2)
        # bright core, thin and sharp
        core_alpha = int(255 * t)
        pygame.draw.line(overlay, (*self.color, core_alpha), p1, p2, max(1, int(5 * t) + 1))
        # small starburst at the center for extra punch
        star_alpha = int(200 * t)
        r = int(self.length * 0.18 * t) + 2
        pygame.draw.circle(overlay, (*self.color, star_alpha), (int(self.x), int(self.y)), r)
        surface.blit(overlay, (0, 0))


class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.texts = []
        self.flashes = []

    def spawn_burst(self, x, y, color, count=18, speed_range=(80, 420), size_range=(3, 8), life_range=(0.35, 0.8)):
        for _ in range(count):
            angle = random.uniform(0, 6.2831853)
            speed = random.uniform(*speed_range)
            vx = speed * random.uniform(0.6, 1.0) * (1 if random.random() > 0.5 else -1)
            vy = speed * random.uniform(-1.2, -0.2)
            life = random.uniform(*life_range)
            size = random.uniform(*size_range)
            self.particles.append(Particle(x, y, vx, vy, life, color, size))

    def spawn_text(self, x, y, text, color, font, life=0.7):
        self.texts.append(FloatingText(x, y, text, color, font, life))

    def spawn_slash(self, x, y, angle_rad, length, color=(255, 255, 255), life=0.16):
        self.flashes.append(SliceFlash(x, y, angle_rad, length, color, life))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]
        self.flashes = [f for f in self.flashes if f.update(dt)]

    def draw(self, surface):
        for f in self.flashes:
            f.draw(surface)
        for p in self.particles:
            p.draw(surface)
        for t in self.texts:
            t.draw(surface)
