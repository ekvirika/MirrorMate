"""Rock Paper Scissors - countdown with fist pumps, gesture locked at SHOOT."""

import random
import time

import cv2

from ..core.fx import center_text, top_bar
from ..core.robot import speak
from .base import Mode

COUNTDOWN = 3
SHOOT_FLASH = 0.6
RESULT_HOLD = 3.0

BEAT_WORDS = {3: "Rock...", 2: "Paper...", 1: "Scissors..."}
BEAT_SPEECH = {3: "Rock", 2: "Paper", 1: "Scissors"}


class RpsMode(Mode):
    name = "Rock Paper Scissors"
    icon = "✊"
    hint = "SPACE play round  |  R reset scores"

    def on_enter(self, robot):
        self.player_score = 0
        self.robot_score = 0
        self.ties = 0
        self._reset_round()

    def _reset_round(self):
        self.phase = "idle"          # idle -> countdown -> reveal
        self.phase_start = 0.0
        self.last_beat = -1
        self.locked_gesture = None
        self.robot_gesture = None
        self.result = None
        self.shoot_time = 0.0

    def idle_ok(self):
        return self.phase == "idle"

    def on_key(self, key, ctx):
        if key == ord(" ") and self.phase == "idle" and not ctx.robot.busy():
            self.phase = "countdown"
            self.phase_start = ctx.now
            self.last_beat = -1
            self.locked_gesture = None
            self.robot_gesture = None
            self.result = None
            ctx.robot.pose("fist")
        elif key == ord("r"):
            self.player_score = self.robot_score = self.ties = 0
            self._reset_round()

    def update(self, ctx):
        if self.phase == "countdown":
            elapsed = ctx.now - self.phase_start
            remaining = COUNTDOWN - int(elapsed)

            if remaining != self.last_beat and remaining > 0:
                self.last_beat = remaining
                speak(BEAT_SPEECH[remaining])
                if not ctx.robot.busy():
                    ctx.robot.pump()

            if elapsed >= COUNTDOWN:
                self._shoot(ctx)

        elif self.phase == "reveal":
            if ctx.now - self.phase_start >= RESULT_HOLD:
                ctx.robot.pose("open")
                self._reset_round()

        self._draw(ctx)

    def _shoot(self, ctx):
        self.locked_gesture = ctx.gesture
        self.shoot_time = ctx.now
        self.phase = "reveal"
        self.phase_start = ctx.now
        speak("Shoot!")

        if not self.locked_gesture:
            self.result = None
            return

        self.robot_gesture = random.choice(["rock", "paper", "scissors"])
        ctx.robot.pose(self.robot_gesture)

        if self.locked_gesture == self.robot_gesture:
            self.result = "tie"
            self.ties += 1
            speak("Tie!")
        else:
            beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
            if beats[self.locked_gesture] == self.robot_gesture:
                self.result = "player"
                self.player_score += 1
                speak("You win!")
                ctx.particles.confetti(ctx.w)
            else:
                self.result = "robot"
                self.robot_score += 1
                speak("Robot wins!")

    def _draw(self, ctx):
        frame, w, h = ctx.frame, ctx.w, ctx.h
        top_bar(frame, 110)
        cv2.putText(frame, f"You: {self.player_score}", (20, 44),
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 0), 3)
        cv2.putText(frame, f"Ties: {self.ties}", (w // 2 - 70, 44),
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 3)
        cv2.putText(frame, f"Robot: {self.robot_score}", (w - 240, 44),
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 100, 255), 3)

        if self.locked_gesture:
            cv2.putText(frame, f"You: {self.locked_gesture.upper()}", (20, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        if self.robot_gesture:
            cv2.putText(frame, f"Robot: {self.robot_gesture.upper()}", (w - 240, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        if self.phase == "idle":
            center_text(frame, "Press SPACE to play!", w // 2, h - 40, 0.9, (220, 220, 220), 2)

        elif self.phase == "countdown":
            remaining = COUNTDOWN - int(ctx.now - self.phase_start)
            word = BEAT_WORDS.get(remaining, "")
            if word:
                center_text(frame, word, w // 2, h // 2 + 60, 2.0, (255, 255, 0), 4)

        elif self.phase == "reveal":
            shoot_elapsed = ctx.now - self.shoot_time
            if shoot_elapsed < SHOOT_FLASH:
                center_text(frame, "SHOOT!", w // 2, h // 2 + 60, 3.0, (0, 80, 255), 6)
            elif self.result:
                labels = {
                    "player": ("YOU WIN!", (0, 255, 0)),
                    "robot": ("ROBOT WINS!", (0, 100, 255)),
                    "tie": ("TIE!", (255, 255, 0)),
                }
                text, color = labels[self.result]
                center_text(frame, text, w // 2, h // 2, 2.2, color, 4)
            else:
                center_text(frame, "No gesture seen - try again!", w // 2, h // 2,
                            1.1, (0, 160, 255), 2)
