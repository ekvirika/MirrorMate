"""
Reaction Duel - quick-draw against the robot.

Arm the round, wait for the green GO flash, then make a FIST faster than
the robot closes its own. The robot gets faster every time it loses.
"""

import random

from ..core.fx import center_text, top_bar
from ..core.robot import speak
from .base import Mode

ARM_DELAY_RANGE = (1.5, 4.0)    # random wait before GO
TIMEOUT = 2.0                   # you get this long after GO
RESULT_HOLD = 3.2

ROBOT_START_TIME = 0.55         # robot's initial "reaction time" (seconds)
ROBOT_MIN_TIME = 0.26
ROBOT_SPEEDUP = 0.04            # how much faster it gets after each loss


class ReactionMode(Mode):
    name = "Reaction Duel"
    icon = "⚡"
    hint = "SPACE arm round - make a FIST when GO flashes!"

    def on_enter(self, robot):
        self.phase = "idle"       # idle -> armed -> go -> result
        self.phase_start = 0.0
        self.go_at = 0.0
        self.player_score = 0
        self.robot_score = 0
        self.best_ms = None
        self.robot_time = ROBOT_START_TIME
        self.result_text = ""
        self.result_color = (255, 255, 255)
        self.player_ms = None
        robot.pose("open")

    def idle_ok(self):
        return self.phase == "idle"

    def on_key(self, key, ctx):
        if key == ord(" ") and self.phase in ("idle", "result"):
            self.phase = "armed"
            self.phase_start = ctx.now
            self.go_at = ctx.now + random.uniform(*ARM_DELAY_RANGE)
            self.player_ms = None
            ctx.robot.cancel()
            ctx.robot.pose("open")

    def update(self, ctx):
        if self.phase == "armed":
            # Jumping the gun costs you the round.
            if ctx.gesture == "rock" and ctx.now - self.phase_start > 0.5:
                self._finish(ctx, "FALSE START!", (0, 80, 255), robot_wins=True)
                speak("Too early!")
            elif ctx.now >= self.go_at:
                self.phase = "go"
                ctx.flash.trigger((0, 220, 0), 0.2)
                # The robot "reacts" after its own reaction time.
                ctx.robot.pose("fist", delay=self.robot_time)

        elif self.phase == "go":
            elapsed = ctx.now - self.go_at
            if ctx.gesture == "rock":
                ms = int(elapsed * 1000)
                self.player_ms = ms
                if self.best_ms is None or ms < self.best_ms:
                    self.best_ms = ms
                if elapsed < self.robot_time:
                    self._finish(ctx, f"YOU WIN!  {ms} ms", (0, 255, 0), robot_wins=False)
                    ctx.particles.confetti(ctx.w)
                    speak("You win!")
                    # Losing makes the robot faster next round...
                    self.robot_time = max(ROBOT_MIN_TIME, self.robot_time - ROBOT_SPEEDUP)
                else:
                    self._finish(ctx, f"ROBOT WINS - {ms} ms, too slow!",
                                 (0, 100, 255), robot_wins=True)
                    speak("Too slow!")
            elif elapsed >= TIMEOUT:
                self._finish(ctx, "ASLEEP AT THE WHEEL?", (0, 100, 255), robot_wins=True)
                speak("Wake up!")

        elif self.phase == "result" and ctx.now - self.phase_start >= RESULT_HOLD:
            self.phase = "idle"
            ctx.robot.pose("open")

        self._draw(ctx)

    def _finish(self, ctx, text, color, robot_wins):
        self.phase = "result"
        self.phase_start = ctx.now
        self.result_text = text
        self.result_color = color
        if robot_wins:
            self.robot_score += 1
        else:
            self.player_score += 1

    def _draw(self, ctx):
        frame, w, h = ctx.frame, ctx.w, ctx.h
        import cv2
        top_bar(frame)
        cv2.putText(frame, f"You: {self.player_score}", (20, 46),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 255, 0), 2)
        cv2.putText(frame, f"Robot: {self.robot_score}", (w - 230, 46),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 100, 255), 2)
        if self.best_ms is not None:
            cv2.putText(frame, f"Best: {self.best_ms} ms", (w // 2 - 100, 46),
                        cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 220, 255), 2)

        if self.phase == "idle":
            center_text(frame, "REACTION DUEL", w // 2, h // 2 - 60, 2.2, (0, 220, 255), 5)
            center_text(frame, "Press SPACE - fist on GO, faster than the robot",
                        w // 2, h // 2 + 30, 0.9, (200, 200, 200), 2)
            robot_ms = int(self.robot_time * 1000)
            center_text(frame, f"Robot reaction time: {robot_ms} ms",
                        w // 2, h // 2 + 80, 0.8, (0, 160, 255), 2)

        elif self.phase == "armed":
            center_text(frame, "wait for it...", w // 2, h // 2, 1.6, (0, 0, 220), 3)

        elif self.phase == "go":
            center_text(frame, "GO! GO! GO!", w // 2, h // 2, 3.0, (0, 255, 0), 6)

        elif self.phase == "result":
            center_text(frame, self.result_text, w // 2, h // 2, 1.6, self.result_color, 3)
            center_text(frame, "SPACE to go again", w // 2, h // 2 + 70,
                        0.8, (180, 180, 180), 2)
