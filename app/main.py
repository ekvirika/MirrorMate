"""
MirrorMate Control Center - one app for every InMoov hand demo.

Run from the repo root:
    python -m app.main            # auto-detect Arduino port
    python -m app.main --port COM3
    python -m app.main --camera 1

Global keys:
    1-5   switch demo        M / TAB / ESC   back to menu
    Q     quit (or ESC from the menu)
    everything else goes to the active mode
"""

import argparse
import sys
import time

import cv2
import mediapipe as mp

if __package__ in (None, ""):
    # Allow `python app/main.py` as well as `python -m app.main`.
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from app.main import main  # re-import as a package and delegate
    if __name__ == "__main__":
        main()
    sys.exit(0)

from .core import fx, gestures
from .core.camera import open_camera
from .core.idle import IdleBuddy
from .core.robot import RobotHand
from .modes.base import FrameContext
from .modes.counting import CountingMode
from .modes.high_five import HighFiveMode
from .modes.menu import MenuMode
from .modes.mirror import MirrorMode
from .modes.reaction import ReactionMode
from .modes.rps import RpsMode
from .modes.rude import RudeMode
from .modes.simon import SimonMode

WINDOW = "MirrorMate"


def main():
    parser = argparse.ArgumentParser(description="MirrorMate Control Center")
    parser.add_argument("--port", help="Arduino serial port (default: auto-detect)")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default 0)")
    args = parser.parse_args()

    robot = RobotHand(port=args.port)

    cap = open_camera(args.camera)
    if not cap.isOpened():
        print(f"❌ Could not open camera {args.camera} — try --camera 1")
        robot.close()
        return

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    hands = mp_hands.Hands(
        static_image_mode=False, max_num_hands=1,
        min_detection_confidence=0.6, min_tracking_confidence=0.6,
    )

    demos = [
        ("1", MirrorMode()),
        ("2", RpsMode()),
        ("3", RudeMode()),
        ("4", SimonMode()),
        ("5", HighFiveMode()),
        ("6", ReactionMode()),
        ("7", CountingMode()),
    ]
    menu = MenuMode(demos)
    mode_by_key = {ord(k): m for k, m in demos}

    particles = fx.Particles()
    flash = fx.Flash()
    idle_buddy = IdleBuddy()

    current = menu
    current.on_enter(robot)

    print("\n🤖 MirrorMate Control Center")
    print("   1 Mirror  2 RPS  3 Rude  4 Simon  5 High-Five  6 Reaction  7 Count")
    print("   M/ESC menu  Q quit\n")

    prev_time = time.time()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("❌ Camera read failed")
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            now = time.time()
            dt = min(now - prev_time, 0.1)
            prev_time = now

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)
            landmarks = None
            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(
                    frame, landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 220, 255), thickness=2, circle_radius=3),
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2),
                )

            ctx = FrameContext(
                frame=frame, w=w, h=h, now=now, dt=dt,
                landmarks=landmarks,
                gesture=gestures.detect_gesture(landmarks),
                robot=robot, particles=particles, flash=flash,
            )

            robot.tick()
            current.update(ctx)
            idle_buddy.tick(ctx, current)
            particles.tick(frame, dt)
            flash.tick(frame)

            caption = idle_buddy.active_caption(now)
            if caption:
                fx.center_text(frame, caption, w // 2, 110, 0.9, (180, 180, 180), 2)

            # Footer: mode name + hint + robot status.
            footer = f"[{current.name}]  {current.hint}"
            if current is not menu:
                footer += "  |  M/ESC menu"
            cv2.putText(frame, footer, (14, h - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1)
            status = "ROBOT OK" if robot.connected else "SIMULATION"
            color = (0, 255, 0) if robot.connected else (0, 165, 255)
            cv2.putText(frame, status, (w - 150, h - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(1) & 0xFF

            back_to_menu = key in (ord("m"), ord("M"), 9, 27)    # M / TAB / ESC

            if key in (ord("q"), ord("Q")):
                break
            elif key == 27 and current is menu:          # ESC on the menu quits
                break
            elif back_to_menu and current is not menu:
                current.on_exit(robot)
                current = menu
                current.on_enter(robot)
                print("→ Menu")
            elif key in mode_by_key and mode_by_key[key] is not current:
                current.on_exit(robot)
                current = mode_by_key[key]
                current.on_enter(robot)
                print(f"→ {current.name}")
            elif key != 255:
                current.on_key(key, ctx)

    except KeyboardInterrupt:
        pass
    finally:
        current.on_exit(robot)
        robot.pose("open")
        robot.tick()
        time.sleep(0.2)
        robot.tick()
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        robot.close()
        print("👋 Bye!")


if __name__ == "__main__":
    main()
