# Ninja Fruit - Hand Edition

A Fruit Ninja style game you play with your bare hand. Point your index
finger at the webcam and slice fruit out of the air.

This is **endless mode**: fruit spawns from the bottom and rises forever, it
never falls back down and there's no penalty for missing. No bombs, no
lives - just keep slicing for points and combos until you decide to stop.

This is a **separate standalone project**, not part of the FYP mouse-control
system. It reuses the same core idea (OpenCV + MediaPipe hand tracking) but
renders the actual game with pygame, so it's not limited by what you can draw
directly on a raw OpenCV frame - smooth 60fps physics, glowing slice trail,
particle juice splashes, screen shake, combo popups, the works.

## How it works (architecture)

```
main.py                  entry point, wires camera + tracker + game together
game/
  constants.py           every tunable number lives here (spawn rate, colors, physics...)
  hand_tracker.py        MediaPipe wrapper -> returns index fingertip position(s) only
  fruit.py               Fruit / FruitHalf objects, procedurally drawn sprites, rise-forever physics
  trail.py                fading glow trail + line-segment vs circle collision test
  particles.py           juice splash particles, slice-flash cut effect, floating score/combo text
  sounds.py              procedurally synthesized sound effects (no audio assets needed)
  game.py                NinjaFruitGame: state machine, spawning, scoring, drawing
models/                  MediaPipe model file gets auto-downloaded here on first run
```

`HandTracker` only ever hands back `(x, y)` fingertip positions - it has no
idea what a "fruit" is. `NinjaFruitGame` only ever receives fingertip
positions - it has no idea whether they came from a webcam, a mouse, or a
replay file. That separation is what makes this reusable for the FYP too.

## Setup

```bash
cd ninja_fruit_hand_game
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

First run downloads a small MediaPipe hand-landmark model file into
`models/` (needs internet once). After that it works fully offline.

## Controls

- Show your hand to the webcam. Slice fruit with your **index fingertip**.
- `SPACE` - start / restart
- `Q` - end the current round and see your score summary
- `ESC` - quit

## Gameplay

- Fruit spawns from the bottom of the screen and rises straight up forever
  with a gentle wobble - it never falls back down, so there's no "miss"
  penalty.
- Slicing a fruit scores points; slicing fruit quickly in a row builds a
  **combo multiplier**, so chaining cuts is worth a lot more than picking
  fruit off one at a time.
- Every cut flashes a bright slash aligned to the direction your finger was
  moving, on top of a juice-splash particle burst and two halves flying
  apart - built to actually feel like cutting something.
- Spawn rate ramps up the longer you play, so it naturally gets busier.
- Press `Q` whenever you want to stop and see your final score, fruit
  sliced, and best combo. Press `SPACE` to go again.

## Tuning

Everything that affects feel and difficulty (rise speed, spawn interval,
fruit size, colors, slash appearance) is in `game/constants.py`. Nothing else
in the codebase hardcodes these values, so balancing the game is a one-file
job.

## Notes

- No external image or audio assets required - fruit sprites are drawn with
  pygame primitives and sounds are synthesized with numpy at startup.
- If your webcam isn't device 0, change `CAM_INDEX` in `game/constants.py`.
- Two hands are tracked by default (`MAX_HANDS = 2` in constants.py), so a
  friend can drop in and slice alongside you.
