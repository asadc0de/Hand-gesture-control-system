"""
SoundBank generates every sound effect on the fly with numpy so the project
ships with zero binary audio assets. If the machine has no audio device,
everything degrades gracefully to silence instead of crashing the game.
"""

import numpy as np
import pygame


class SoundBank:
    def __init__(self, sample_rate=44100):
        self.enabled = True
        self.sample_rate = sample_rate
        try:
            pygame.mixer.init(frequency=sample_rate, size=-16, channels=2)
            self.slice_sounds = [self._make_swoosh() for _ in range(3)]
            self.bomb_sound = self._make_bomb()
            self.miss_sound = self._make_miss()
            self.gameover_sound = self._make_gameover()
        except Exception:
            self.enabled = False

    def _to_sound(self, wave):
        wave = np.clip(wave, -1, 1)
        stereo = np.column_stack([wave, wave])
        audio = (stereo * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(np.ascontiguousarray(audio))

    def _make_swoosh(self):
        dur = 0.18
        n = int(self.sample_rate * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        noise = np.random.uniform(-1, 1, n)
        envelope = np.exp(-8 * t) * np.sin(np.pi * t / dur)
        freq_sweep = 1800 + 2500 * np.exp(-6 * t)
        tone = np.sin(2 * np.pi * freq_sweep * t)
        wave = (0.6 * noise + 0.4 * tone) * envelope
        return self._to_sound(wave * 0.5)

    def _make_bomb(self):
        dur = 0.5
        n = int(self.sample_rate * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        low = np.sin(2 * np.pi * 60 * t)
        noise = np.random.uniform(-1, 1, n)
        envelope = np.exp(-4 * t)
        wave = (0.7 * low + 0.5 * noise) * envelope
        return self._to_sound(wave * 0.8)

    def _make_miss(self):
        dur = 0.22
        n = int(self.sample_rate * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        freq = 500 - 300 * (t / dur)
        wave = np.sin(2 * np.pi * freq * t) * np.exp(-5 * t)
        return self._to_sound(wave * 0.35)

    def _make_gameover(self):
        dur = 0.8
        n = int(self.sample_rate * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        freq = 300 * np.exp(-1.2 * t)
        wave = np.sin(2 * np.pi * freq * t) * np.exp(-1.5 * t)
        return self._to_sound(wave * 0.5)

    def play_slice(self):
        if self.enabled:
            import random
            random.choice(self.slice_sounds).play()

    def play_bomb(self):
        if self.enabled:
            self.bomb_sound.play()

    def play_miss(self):
        if self.enabled:
            self.miss_sound.play()

    def play_gameover(self):
        if self.enabled:
            self.gameover_sound.play()
