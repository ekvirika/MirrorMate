"""Shared visual effects and UI drawing helpers (OpenCV)."""

import math
import random
import time

import cv2
import numpy as np

# ── text ──────────────────────────────────────────────────────────────────────

def center_text(frame, text, cx, cy, scale, color, thick, outline=True):
    ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thick)[0]
    x, y = cx - ts[0] // 2, cy + ts[1] // 2
    if outline:
        cv2.putText(frame, text, (x + 3, y + 3),
                    cv2.FONT_HERSHEY_DUPLEX, scale, (0, 0, 0), thick + 3)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_DUPLEX, scale, color, thick)


def top_bar(frame, height=70, alpha=0.65):
    """Darkened bar across the top for scores/titles."""
    w = frame.shape[1]
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, height), (0, 0, 0), -1)
    cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, frame)


def progress_bar(frame, cx, cy, width, frac, color, bg=(40, 40, 40)):
    """Horizontal progress bar centered at (cx, cy)."""
    x = cx - width // 2
    cv2.rectangle(frame, (x, cy), (x + width, cy + 16), bg, -1)
    cv2.rectangle(frame, (x, cy), (x + int(width * max(0, min(1, frac))), cy + 16), color, -1)
    cv2.rectangle(frame, (x, cy), (x + width, cy + 16), (120, 120, 120), 1)


# ── shapes ────────────────────────────────────────────────────────────────────

def draw_star(frame, cx, cy, r, color):
    pts = []
    for i in range(10):
        a = i * math.pi / 5 - math.pi / 2
        rad = r if i % 2 == 0 else r // 2
        pts.append([int(cx + rad * math.cos(a)), int(cy + rad * math.sin(a))])
    cv2.fillPoly(frame, [np.array(pts, np.int32)], color)


def draw_big_x(frame, cx, cy, size, color=(0, 0, 200), thick=10):
    cv2.line(frame, (cx - size, cy - size), (cx + size, cy + size), color, thick)
    cv2.line(frame, (cx + size, cy - size), (cx - size, cy + size), color, thick)


# ── particles ─────────────────────────────────────────────────────────────────

class Particles:
    """Confetti / star-burst particle system. Create once, tick every frame."""

    def __init__(self):
        self.items = []

    def confetti(self, w, count=90):
        for _ in range(count):
            self.items.append({
                "kind": "confetti",
                "x": float(random.randint(0, w)), "y": float(random.randint(-120, 0)),
                "vx": random.uniform(-60, 60), "vy": random.uniform(120, 320),
                "color": (random.randint(30, 255), random.randint(30, 255), random.randint(30, 255)),
                "size": random.randint(5, 11),
                "rect": random.random() > 0.5,
                "born": time.time(), "life": 3.5,
            })

    def burst(self, cx, cy, count=16):
        colors = [(0, 220, 255), (0, 255, 120), (255, 210, 0), (255, 80, 200), (255, 255, 255)]
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 160)
            self.items.append({
                "kind": "star",
                "x": float(cx), "y": float(cy),
                "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
                "color": random.choice(colors),
                "size": random.randint(14, 30),
                "born": time.time(), "life": 1.1,
            })

    def tick(self, frame, dt):
        h = frame.shape[0]
        now = time.time()
        alive = []
        for p in self.items:
            age = now - p["born"]
            if age >= p["life"] or p["y"] > h + 20:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 180 * dt
            x, y = int(p["x"]), int(p["y"])
            if p["kind"] == "star":
                r = max(3, int(p["size"] * (1 - age / p["life"])))
                draw_star(frame, x, y, r, p["color"])
            elif p.get("rect"):
                cv2.rectangle(frame, (x, y), (x + p["size"], y + p["size"] // 2), p["color"], -1)
            else:
                cv2.circle(frame, (x, y), p["size"] // 2, p["color"], -1)
            alive.append(p)
        self.items = alive


# ── full-frame effects ────────────────────────────────────────────────────────

class Flash:
    """Brief colored full-screen flash."""

    def __init__(self):
        self.time = 0.0
        self.color = (0, 220, 255)
        self.duration = 0.25

    def trigger(self, color=(0, 220, 255), duration=0.25):
        self.time = time.time()
        self.color = color
        self.duration = duration

    def tick(self, frame):
        elapsed = time.time() - self.time
        if elapsed >= self.duration:
            return
        alpha = 0.6 * (1 - elapsed / self.duration)
        ov = frame.copy()
        cv2.rectangle(ov, (0, 0), (frame.shape[1], frame.shape[0]), self.color, -1)
        cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, frame)


def shake_offset(until_time, amplitude=14):
    """Random (dx, dy) while a screen-shake is active, else (0, 0)."""
    if time.time() >= until_time:
        return 0, 0
    return random.randint(-amplitude, amplitude), random.randint(-amplitude, amplitude)


def apply_shake(frame, dx, dy):
    if dx == 0 and dy == 0:
        return frame
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(frame, m, (frame.shape[1], frame.shape[0]))
