"""High Five - raise an open palm and the robot slaps it (in spirit)."""

import math
import random

import cv2

from ..core import gestures
from ..core.fx import center_text, progress_bar, top_bar
from ..core.robot import speak
from .base import Mode

COOLDOWN = 2.2       # seconds before another high-five counts
HOLD_OPEN = 1.4      # how long the robot holds its palm open
IMPACT_WORDS = ["SLAP!", "HIGH FIVE!", "POW!", "YES!", "NICE!"]
IMPACT_DURATION = 0.9
TIRED_THRESHOLD = 10


class HighFiveMode(Mode):
    name = "High Five"
    icon = "🖐"
    hint = "Raise your open palm close to the camera!"

    def on_enter(self, robot):
        self.total = 0
        self.last_time = 0.0
        self.impact_word = ""
        self.impact_time = 0.0
        self.holding_open = False
        robot.pose("fist")

    def idle_ok(self):
        # The hand waits in a fist here; a fidget would leave it mid-pose.
        return False

    def update(self, ctx):
        # Close the robot hand again after holding the high-five open.
        if self.holding_open and ctx.now - self.last_time > HOLD_OPEN:
            ctx.robot.pose("fist")
            self.holding_open = False

        ready = ctx.now - self.last_time >= COOLDOWN
        lm = ctx.landmarks

        if lm is not None and ready and gestures.is_open_palm_close(lm, ctx.h):
            cx, cy = gestures.hand_center(lm, ctx.w, ctx.h)
            self.total += 1
            self.last_time = ctx.now
            self.impact_word = random.choice(IMPACT_WORDS)
            self.impact_time = ctx.now
            self.holding_open = True
            ctx.robot.pose("open")
            ctx.flash.trigger((0, 220, 255), 0.22)
            ctx.particles.burst(cx, cy)
            speak(random.choice(["Nice!", "Yeah!", "High five!"]))

        self._draw(ctx)

    def _draw(self, ctx):
        frame, w, h = ctx.frame, ctx.w, ctx.h
        top_bar(frame)
        cv2.putText(frame, f"High-fives: {self.total}", (20, 46),
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 220, 255), 3)
        if self.total >= TIRED_THRESHOLD:
            cv2.putText(frame, "ok I need a break...", (w - 330, 46),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (160, 160, 160), 2)

        # Pulsing ring around the hand while tracking.
        if ctx.landmarks is not None:
            cx, cy = gestures.hand_center(ctx.landmarks, w, h)
            p = ctx.landmarks.landmark
            hand_h = int(abs(p[12].y - p[0].y) * h)
            pulse = int(8 * math.sin(ctx.now * 8))
            cv2.circle(frame, (cx, cy), int(hand_h * 0.75) + pulse, (0, 220, 255), 3)

        # Impact word.
        impact_elapsed = ctx.now - self.impact_time
        if self.impact_word and impact_elapsed < IMPACT_DURATION:
            t = impact_elapsed / IMPACT_DURATION
            scale = 3.5 - 1.5 * t
            center_text(frame, self.impact_word, w // 2, h // 2,
                        scale, (0, 220, 255), max(4, int(8 * (1 - t * 0.5))))

        # Cooldown bar or prompt.
        cooldown_left = max(0.0, COOLDOWN - (ctx.now - self.last_time)) if self.last_time else 0.0
        if cooldown_left > 0:
            progress_bar(frame, w // 2, h - 55, 180,
                         1 - cooldown_left / COOLDOWN, (0, 180, 255))
        else:
            center_text(frame, "Raise your open palm to high-five the robot!",
                        w // 2, h - 40, 0.8, (220, 220, 220), 2)
