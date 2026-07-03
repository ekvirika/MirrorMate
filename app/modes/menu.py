"""Home menu - pick a demo. The robot waves at you while you decide."""

import cv2

from ..core.fx import center_text
from .base import Mode

WAVE_INTERVAL = 6.0


class MenuMode(Mode):
    name = "Menu"
    icon = "🏠"
    hint = "Press a number to pick a demo  |  Q quit"

    def __init__(self, entries):
        """entries: list of (key_char, Mode) shown as menu items."""
        self.entries = entries
        self.last_wave = 0.0

    def on_enter(self, robot):
        robot.pose("open")
        self.last_wave = 0.0

    def idle_ok(self):
        # The menu has its own attract wave - don't double up.
        return False

    def update(self, ctx):
        # Friendly attract wave every few seconds.
        if ctx.now - self.last_wave > WAVE_INTERVAL and not ctx.robot.busy():
            ctx.robot.wave()
            self.last_wave = ctx.now

        frame, w, h = ctx.frame, ctx.w, ctx.h

        # Dim the camera feed so the menu pops.
        ov = frame.copy()
        cv2.rectangle(ov, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(ov, 0.55, frame, 0.45, 0, frame)

        center_text(frame, "MIRRORMATE", w // 2, 90, 2.6, (0, 220, 255), 5)
        center_text(frame, "InMoov Hand Control Center", w // 2, 150,
                    0.9, (190, 190, 190), 2)

        # Menu tiles - sized so any number of entries fits above the footer.
        tile_w = 520
        y = 195
        available = h - y - 70
        tile_h = min(56, available // len(self.entries) - 10)
        gap = 10
        x = w // 2 - tile_w // 2
        text_y = tile_h // 2 + 12
        for key_char, mode in self.entries:
            cv2.rectangle(frame, (x, y), (x + tile_w, y + tile_h), (30, 30, 30), -1)
            cv2.rectangle(frame, (x, y), (x + tile_w, y + tile_h), (0, 160, 200), 2)
            cv2.putText(frame, key_char, (x + 22, y + text_y),
                        cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 220, 255), 3)
            cv2.putText(frame, mode.name, (x + 72, y + text_y),
                        cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2)
            y += tile_h + gap

        status = f"Robot: {ctx.robot.port}" if ctx.robot.connected else "Robot: SIMULATION MODE"
        color = (0, 255, 0) if ctx.robot.connected else (0, 165, 255)
        center_text(frame, status, w // 2, y + 30, 0.7, color, 2, outline=False)
