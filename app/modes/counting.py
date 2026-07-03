"""Finger Count - hold up 0-5 fingers and the robot copies the count."""

from collections import Counter, deque

import cv2

from ..core import gestures
from ..core.fx import center_text, top_bar
from ..core.robot import speak
from .base import Mode

HISTORY = 10          # frames of majority-vote smoothing
STABLE_FRACTION = 0.7
SPEAK_COOLDOWN = 1.0


class CountingMode(Mode):
    name = "Finger Count"
    icon = "🖐"
    hint = "Hold up 0-5 fingers - the robot copies you"

    def on_enter(self, robot):
        self.history = deque(maxlen=HISTORY)
        self.shown = None         # count the robot is currently showing
        self.last_change = 0.0
        robot.pose("fist")

    def update(self, ctx):
        if ctx.landmarks is not None:
            self.history.append(gestures.count_extended(ctx.landmarks))
        else:
            self.history.clear()

        stable = self._stable_count()
        if (stable is not None and stable != self.shown
                and ctx.now - self.last_change > SPEAK_COOLDOWN):
            self.shown = stable
            self.last_change = ctx.now
            ctx.robot.show_count(stable)
            speak(str(stable))

        self._draw(ctx, stable)

    def _stable_count(self):
        """Majority vote over recent frames, only when it's decisive."""
        if len(self.history) < HISTORY:
            return None
        count, votes = Counter(self.history).most_common(1)[0]
        return count if votes >= HISTORY * STABLE_FRACTION else None

    def _draw(self, ctx, stable):
        frame, w, h = ctx.frame, ctx.w, ctx.h
        top_bar(frame)
        center_text(frame, "FINGER COUNT", w // 2, 38, 1.2, (0, 220, 255), 2)

        if self.shown is not None:
            # Giant mirrored number.
            center_text(frame, str(self.shown), w - 130, h // 2, 6.0, (0, 220, 255), 10)
            cv2.putText(frame, "robot shows", (w - 220, h // 2 + 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

        if ctx.landmarks is None:
            center_text(frame, "Show your hand to the camera", w // 2, h - 40,
                        0.9, (200, 200, 200), 2)
        elif stable is None and self.shown is None:
            center_text(frame, "Hold a count steady...", w // 2, h - 40,
                        0.9, (200, 200, 200), 2)
