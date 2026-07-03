"""Rude Detector - flip off the robot and it gets offended, then retaliates."""

import random
import time

import cv2

from ..core import gestures
from ..core.fx import center_text, top_bar
from ..core.robot import speak
from .base import Mode

SHOCK_DURATION = 1.6
RESPOND_DURATION = 2.5
COOLDOWN_DURATION = 2.0

SHOCKED_LINES = [
    "EXCUSE ME?!", "HOW RUDE!", "OH NO YOU DIDN'T.", "REALLY?!",
    "I SEE WHAT YOU DID.", "BOLD MOVE.", "WOW. JUST WOW.",
    "MOM WOULD BE DISAPPOINTED.",
]


class RudeMode(Mode):
    name = "Rude Detector"
    icon = "🖕"
    hint = "Show the middle finger... if you dare"

    def on_enter(self, robot):
        self.phase = "watching"    # watching -> shocked -> responding -> cooldown
        self.phase_start = 0.0
        self.rude_count = 0
        self.line = ""
        self.shake_until = 0.0
        robot.pose("open")

    def idle_ok(self):
        return self.phase == "watching"

    def update(self, ctx):
        elapsed = ctx.now - self.phase_start

        if self.phase == "watching":
            if gestures.is_middle_finger(ctx.landmarks):
                self.phase = "shocked"
                self.phase_start = ctx.now
                self.rude_count += 1
                self.line = random.choice(SHOCKED_LINES)
                self.shake_until = ctx.now + 0.7
                ctx.flash.trigger((0, 0, 220), 0.3)
                speak(random.choice(["Excuse me?!", "How rude!", "Wow."]))

        elif self.phase == "shocked" and elapsed >= SHOCK_DURATION:
            self.phase = "responding"
            self.phase_start = ctx.now
            ctx.robot.pose("middle_up")   # right back at you
            speak("Right back at you, buddy.")

        elif self.phase == "responding" and elapsed >= RESPOND_DURATION:
            self.phase = "cooldown"
            self.phase_start = ctx.now
            ctx.robot.pose("open")

        elif self.phase == "cooldown" and elapsed >= COOLDOWN_DURATION:
            self.phase = "watching"

        self._draw(ctx)

    def _draw(self, ctx):
        frame, w, h = ctx.frame, ctx.w, ctx.h
        top_bar(frame)
        center_text(frame, "RUDE DETECTOR", w // 2, 38, 1.2, (0, 120, 255), 2)
        cv2.putText(frame, f"Offenses: {self.rude_count}", (20, 46),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 160, 255), 2)

        if self.phase == "watching":
            center_text(frame, "I'm watching you...", w // 2, h - 40,
                        0.9, (180, 180, 180), 2)
        elif self.phase == "shocked":
            center_text(frame, self.line, w // 2, h // 2, 2.0, (0, 0, 230), 5)
        elif self.phase == "responding":
            center_text(frame, "RIGHT BACK AT YOU", w // 2, h // 2,
                        1.6, (0, 120, 255), 4)
        elif self.phase == "cooldown":
            center_text(frame, "...we good now?", w // 2, h - 40,
                        0.9, (160, 160, 160), 2)
