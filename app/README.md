# MirrorMate Control Center

One application for every InMoov hand demo. One camera loop, one robot
connection, switchable modes.

## Run

```bash
cd MirrorMate
python -m app.main               # auto-detects the Arduino port
python -m app.main --port COM3   # force a port (Windows example)
python -m app.main --camera 1    # use a different webcam
```

Works on macOS and Windows — camera backend and text-to-speech are picked
per-OS automatically. Without an Arduino attached it runs in simulation mode
(camera, games, and UI all still work).

## Modes

| Key | Mode | What it does |
|-----|------|--------------|
| `1` | **Hand Mirror** | The robot hand copies your fingers live, with per-finger curl bars on screen |
| `2` | **Rock Paper Scissors** | Spoken countdown, robot pumps its fist on each beat, both reveal at SHOOT |
| `3` | **Rude Detector** | Flip off the robot → it gets shocked, then flips you off right back |
| `4` | **Simon Says** | Robot shows a gesture, you copy it before the timer runs out; streaks + confetti |
| `5` | **High Five** | Raise an open palm close to the camera and the robot opens up to meet it |
| `6` | **Reaction Duel** | Quick-draw: make a fist when GO flashes, faster than the robot — it gets faster every time it loses |
| `7` | **Finger Count** | Hold up 0-5 fingers and the robot copies the count (and says it out loud) |
| `M` / `TAB` / `ESC` | Menu | Back to the home screen (robot waves at you) |
| `Q` | Quit | Also `ESC` from the menu. Hand resets to open on exit |

Mode-specific keys: `SPACE` starts a round (RPS, Simon, Reaction), `R` resets scores (RPS).

**Idle personality:** if nobody shows a hand for ~15-30 s (and no game is mid-round),
the robot gets bored — it drums its fingers, stretches, or waves at nobody, with a
little caption on screen.

## Structure

```
app/
├── main.py            # camera loop, MediaPipe, mode switching
├── core/
│   ├── camera.py      # cross-platform webcam (AVFoundation / DirectShow)
│   ├── robot.py       # RobotHand: auto port detect, non-blocking servo scheduler,
│   │                  #   named poses, wag/pump/wave animations, cross-platform TTS
│   ├── gestures.py    # RPS classification, middle-finger & high-five detection,
│   │                  #   per-finger curl estimation for mirroring
│   └── fx.py          # confetti, star bursts, flashes, shake, text/bar helpers
└── modes/
    ├── base.py        # Mode interface + FrameContext passed to modes each frame
    ├── menu.py  mirror.py  rps.py  rude.py  simon.py  high_five.py
```

## Adding a new demo

1. Create `app/modes/my_mode.py` subclassing `Mode` — implement `on_enter`,
   `update(ctx)`, and optionally `on_key(key, ctx)`.
2. `ctx` gives you the frame to draw on, hand landmarks, the detected RPS
   gesture, the shared `robot`, and `particles`/`flash` effects.
3. Register it in the `demos` list in `app/main.py` with a number key. Done.

Servo convention: `0` = finger extended, `180` = folded.
Servo ids: thumb 3, index 1, middle 2, ring 4, pinky 5, wrist 6.
