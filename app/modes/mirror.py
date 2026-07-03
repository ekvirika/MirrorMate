"""
Mirror mode - the InMoov hand copies your hand, live.

Finger curls are estimated from MediaPipe joint angles, smoothed with an
exponential moving average, and streamed to the servos with a deadband so
the serial line isn't flooded.
"""

import cv2

from ..core import gestures
from ..core.fx import center_text, top_bar
from ..core.robot import FINGERS
from .base import Mode

SEND_INTERVAL = 0.06   # max ~16 servo updates/sec
SMOOTHING = 0.35       # EMA factor: higher = snappier, lower = smoother
SNAP_HIGH = 0.82       # curls beyond this drive the servo fully closed
SNAP_LOW = 0.10        # ...and below this fully open


def _to_angle(curl):
    """Map curl to servo angle, snapping the extremes so a fist really
    squeezes to 180 and an open hand really rests at 0 (EMA smoothing
    otherwise approaches the endpoints but never lands on them)."""
    if curl >= SNAP_HIGH:
        return 180
    if curl <= SNAP_LOW:
        return 0
    # Rescale the middle so there's no jump at the snap points.
    return (curl - SNAP_LOW) / (SNAP_HIGH - SNAP_LOW) * 180


class MirrorMode(Mode):
    name = "Hand Mirror"
    icon = "🪞"
    hint = "Move your hand - the robot copies it live"

    def on_enter(self, robot):
        self.smoothed = {f: 0.0 for f in FINGERS}
        self.last_send = 0.0
        self.tracking = False
        robot.pose("open")

    def on_exit(self, robot):
        robot.cancel()
        robot.pose("open")

    def update(self, ctx):
        lm = ctx.landmarks
        self.tracking = lm is not None

        if lm is not None:
            curls = gestures.finger_curls(lm)
            for f in FINGERS:
                self.smoothed[f] += SMOOTHING * (curls[f] - self.smoothed[f])

            if ctx.now - self.last_send >= SEND_INTERVAL:
                ctx.robot.set_fingers(
                    {f: _to_angle(self.smoothed[f]) for f in FINGERS}
                )
                self.last_send = ctx.now

        self._draw(ctx)

    def _draw(self, ctx):
        frame, w, h = ctx.frame, ctx.w, ctx.h
        top_bar(frame)
        center_text(frame, "HAND MIRROR", w // 2, 38, 1.2, (0, 220, 255), 2)

        # Live curl bars, one per finger.
        bar_h = 110
        bar_w = 26
        gap = 46
        x0 = w - len(FINGERS) * gap - 30
        y0 = h - bar_h - 60
        for i, finger in enumerate(FINGERS):
            x = x0 + i * gap
            fill = int(bar_h * self.smoothed[finger])
            color = (0, 200, 255) if self.tracking else (90, 90, 90)
            cv2.rectangle(frame, (x, y0), (x + bar_w, y0 + bar_h), (40, 40, 40), -1)
            cv2.rectangle(frame, (x, y0 + bar_h - fill), (x + bar_w, y0 + bar_h), color, -1)
            cv2.rectangle(frame, (x, y0), (x + bar_w, y0 + bar_h), (120, 120, 120), 1)
            cv2.putText(frame, finger[0].upper(), (x + 6, y0 + bar_h + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 2)

        if not self.tracking:
            center_text(frame, "Show your hand to the camera", w // 2, h // 2,
                        1.0, (200, 200, 200), 2)
