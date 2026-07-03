"""Simon Says - the robot shows a gesture, you copy it before time runs out."""

import math
import random

import cv2

from ..core.fx import center_text, draw_big_x, draw_star, progress_bar, top_bar
from ..core.robot import speak
from .base import Mode

SHOW_DURATION = 3.0
PLAYER_DURATION = 4.0
RESULT_DURATION = 2.8

GESTURE_COLOR = {"rock": (80, 80, 220), "paper": (60, 200, 80), "scissors": (220, 80, 80)}


class SimonMode(Mode):
    name = "Simon Says"
    icon = "🎯"
    hint = "SPACE start round - copy the robot's gesture!"

    def on_enter(self, robot):
        self.phase = "idle"    # idle -> showing -> player_turn -> correct/wrong
        self.phase_start = 0.0
        self.simon_gesture = None
        self.score = 0
        self.streak = 0
        self.best = 0
        robot.pose("open")

    def idle_ok(self):
        return self.phase == "idle"

    def on_key(self, key, ctx):
        if key == ord(" ") and self.phase == "idle":
            self.simon_gesture = random.choice(["rock", "paper", "scissors"])
            self.phase = "showing"
            self.phase_start = ctx.now
            ctx.robot.pose(self.simon_gesture)
            speak(f"Simon says {self.simon_gesture}")

    def update(self, ctx):
        elapsed = ctx.now - self.phase_start

        if self.phase == "showing" and elapsed >= SHOW_DURATION:
            self.phase = "player_turn"
            self.phase_start = ctx.now
            ctx.robot.pose("fist")   # hide the answer

        elif self.phase == "player_turn" and elapsed >= PLAYER_DURATION:
            if ctx.gesture == self.simon_gesture:
                self.phase = "correct"
                self.score += 1
                self.streak += 1
                self.best = max(self.best, self.streak)
                ctx.robot.pose("open")
                ctx.particles.confetti(ctx.w)
                speak("Correct!")
            else:
                self.phase = "wrong"
                self.streak = 0
                ctx.robot.wag_finger()
                speak("Wrong!")
            self.phase_start = ctx.now

        elif self.phase in ("correct", "wrong") and elapsed >= RESULT_DURATION:
            self.phase = "idle"
            ctx.robot.pose("open")

        self._draw(ctx, elapsed)

    def _draw(self, ctx, elapsed):
        frame, w, h = ctx.frame, ctx.w, ctx.h
        top_bar(frame)
        cv2.putText(frame, f"Score: {self.score}", (20, 46),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(frame, f"Streak: {self.streak}", (w // 2 - 90, 46),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 200, 255), 2)
        cv2.putText(frame, f"Best: {self.best}", (w - 190, 46),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (160, 160, 160), 2)

        if self.phase == "idle":
            center_text(frame, "SIMON SAYS", w // 2, h // 2 - 50, 2.4, (0, 220, 255), 5)
            center_text(frame, "Press SPACE to play", w // 2, h // 2 + 40,
                        1.0, (200, 200, 200), 2)

        elif self.phase == "showing":
            remaining = max(0.0, SHOW_DURATION - elapsed)
            color = GESTURE_COLOR.get(self.simon_gesture, (200, 200, 200))
            center_text(frame, "SIMON SAYS...", w // 2, h // 2 - 100, 1.5, (255, 220, 0), 3)
            center_text(frame, self.simon_gesture.upper(), w // 2, h // 2, 2.8, color, 6)
            center_text(frame, f"Remember it!  {remaining:.1f}s", w // 2, h // 2 + 90,
                        0.9, (180, 180, 180), 2)

        elif self.phase == "player_turn":
            remaining = max(0.0, PLAYER_DURATION - elapsed)
            frac = remaining / PLAYER_DURATION
            center_text(frame, "YOUR TURN!", w // 2, h // 2 - 100, 1.6, (80, 255, 80), 3)
            bar_color = (0, 200, 0) if frac > 0.4 else (0, 160, 255) if frac > 0.2 else (0, 0, 220)
            progress_bar(frame, w // 2, h // 2 + 10, int(w * 0.5), frac, bar_color)
            if ctx.gesture:
                match = ctx.gesture == self.simon_gesture
                color = (0, 255, 0) if match else (0, 80, 220)
                center_text(frame, f"You: {ctx.gesture.upper()}", w // 2, h // 2 + 70,
                            1.0, color, 2)

        elif self.phase == "correct":
            r = int(55 + 18 * math.sin(elapsed * 12))
            draw_star(frame, w // 2, h // 2 - 80, r, (0, 255, 100))
            center_text(frame, "CORRECT!", w // 2, h // 2 + 20, 2.6, (0, 255, 80), 6)
            if self.streak > 1:
                center_text(frame, f"STREAK x{self.streak}!", w // 2, h // 2 + 100,
                            1.3, (0, 220, 255), 3)

        elif self.phase == "wrong":
            draw_big_x(frame, w // 2, h // 2 - 60, 70)
            center_text(frame, "WRONG!", w // 2, h // 2 + 30, 2.6, (0, 0, 220), 6)
            if self.simon_gesture:
                center_text(frame, f"It was {self.simon_gesture.upper()}",
                            w // 2, h // 2 + 110, 1.0, (180, 180, 180), 2)
