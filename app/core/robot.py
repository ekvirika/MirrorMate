"""
RobotHand - single shared interface to the InMoov hand.

Owns the serial connection (auto-detected port), and a time-based command
scheduler so modes can queue poses and animations without ever blocking the
camera loop. All servo writes go through here.

Servo protocol: "<servo_id>:<angle>!\n" at 9600 baud.
Convention: 0 = finger extended/open, 180 = finger folded/closed.
"""

import platform
import subprocess
import time

import serial
import serial.tools.list_ports

BAUD_RATE = 9600

# servo id per finger
SERVOS = {"thumb": 3, "index": 1, "middle": 2, "ring": 4, "pinky": 5, "wrist": 6}

FINGERS = ["thumb", "index", "middle", "ring", "pinky"]

POSES = {
    "rock":      {"thumb": 180, "index": 180, "middle": 180, "ring": 180, "pinky": 180},
    "paper":     {"thumb": 0,   "index": 0,   "middle": 0,   "ring": 0,   "pinky": 0},
    "scissors":  {"thumb": 180, "index": 0,   "middle": 0,   "ring": 180, "pinky": 180},
    "point":     {"thumb": 180, "index": 0,   "middle": 180, "ring": 180, "pinky": 180},
    "middle_up": {"thumb": 180, "index": 180, "middle": 0,   "ring": 180, "pinky": 180},
    "open":      {"thumb": 0,   "index": 0,   "middle": 0,   "ring": 0,   "pinky": 0},
    "fist":      {"thumb": 180, "index": 180, "middle": 180, "ring": 180, "pinky": 180},
}

# Substrings that identify likely Arduino serial adapters.
_ARDUINO_HINTS = ("arduino", "usbserial", "wchusbserial", "usbmodem", "ch340", "cp210", "ftdi")

# Spacing between individual servo commands in a queued pose.
COMMAND_SPACING = 0.01


def find_port(preferred=None):
    """Auto-detect the Arduino serial port. Returns port name or None."""
    if preferred:
        return preferred

    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None

    # Prefer ports whose device/description looks like an Arduino adapter.
    def score(p):
        text = f"{p.device} {p.description or ''}".lower()
        return max((1 for hint in _ARDUINO_HINTS if hint in text), default=0)

    ports.sort(key=score, reverse=True)
    return ports[0].device


class RobotHand:
    def __init__(self, port=None):
        self.serial = None
        self.connected = False
        self.port = None
        self._schedule = []       # list of (fire_time, servo_id, angle)
        self._last_sent = {}      # servo_id -> last angle actually sent
        self._connect(port)

    # ── connection ────────────────────────────────────────────────────────────

    def _connect(self, preferred_port):
        port = find_port(preferred_port)
        if not port:
            print("⚠️  No serial ports found — running in SIMULATION mode")
            return
        try:
            self.serial = serial.Serial(port, BAUD_RATE, timeout=1)
            time.sleep(0.5)
            self.connected = True
            self.port = port
            print(f"✅ Robot hand connected on {port}")
        except Exception as e:
            print(f"⚠️  Could not open {port}: {e} — running in SIMULATION mode")

    def close(self):
        if self.connected and self.serial:
            try:
                self.serial.close()
            except Exception:
                pass
        self.connected = False

    # ── low level ─────────────────────────────────────────────────────────────

    def send_now(self, servo_id, angle):
        """Write one servo command immediately (still non-blocking-ish)."""
        angle = int(max(0, min(180, angle)))
        self._last_sent[servo_id] = angle
        if not self.connected:
            return
        try:
            self.serial.write(f"{servo_id}:{angle}!\n".encode())
            self.serial.flush()
        except Exception:
            pass

    # ── scheduler ─────────────────────────────────────────────────────────────

    def tick(self):
        """Call once per frame: sends any scheduled commands that are due."""
        if not self._schedule:
            return
        now = time.time()
        due = [c for c in self._schedule if c[0] <= now]
        self._schedule = [c for c in self._schedule if c[0] > now]
        for _, servo_id, angle in due:
            self.send_now(servo_id, angle)

    def busy(self):
        """True while a queued pose/animation is still playing."""
        return bool(self._schedule)

    def cancel(self):
        """Drop all pending scheduled commands."""
        self._schedule = []

    def _queue(self, commands, start_delay=0.0, spacing=COMMAND_SPACING):
        """Schedule [(servo_id, angle), ...] spaced out starting at now+delay."""
        base = time.time() + start_delay
        for i, (servo_id, angle) in enumerate(commands):
            self._schedule.append((base + i * spacing, servo_id, angle))

    # ── high level ────────────────────────────────────────────────────────────

    def pose(self, name, delay=0.0):
        """Move the hand into a named pose (see POSES)."""
        finger_angles = POSES[name]
        self._queue(
            [(SERVOS[f], a) for f, a in finger_angles.items()],
            start_delay=delay,
        )

    def set_fingers(self, angles, min_change=6):
        """
        Directly set finger angles from {'thumb': 0-180, ...}.
        Skips servos whose angle barely changed - used by live mirroring so
        we don't flood the serial line.
        """
        for finger, angle in angles.items():
            sid = SERVOS[finger]
            angle = int(max(0, min(180, angle)))
            if abs(angle - self._last_sent.get(sid, -999)) >= min_change:
                self.send_now(sid, angle)

    def wag_finger(self, cycles=3, step=0.22):
        """Disapproving index-finger wag (used by the Rude Detector)."""
        self.cancel()
        # Fold everything except the index first.
        cmds = [(SERVOS[f], 180) for f in ("thumb", "middle", "ring", "pinky")]
        cmds.append((SERVOS["index"], 0))
        self._queue(cmds)
        # Then alternate the index open/curled.
        for i in range(cycles * 2):
            angle = 130 if i % 2 == 0 else 0
            self._schedule.append(
                (time.time() + 0.3 + i * step, SERVOS["index"], angle)
            )

    def pump(self):
        """One fist pump (half-open then close) - RPS countdown beats."""
        self._queue([(SERVOS[f], 90) for f in FINGERS])
        self._queue([(SERVOS[f], 180) for f in FINGERS], start_delay=0.25)

    def wave(self, cycles=2):
        """Open/close all fingers - a friendly attract animation."""
        self.cancel()
        for i in range(cycles * 2):
            angle = 0 if i % 2 == 0 else 150
            self._queue(
                [(SERVOS[f], angle) for f in FINGERS],
                start_delay=i * 0.45,
            )

    def drum(self, cycles=2, step=0.12):
        """Drum the fingers one after another - bored-robot fidget."""
        self.cancel()
        base = time.time()
        t = 0.0
        for _ in range(cycles):
            for finger in ("pinky", "ring", "middle", "index"):
                self._schedule.append((base + t, SERVOS[finger], 140))
                self._schedule.append((base + t + step * 2, SERVOS[finger], 0))
                t += step
        self._queue([(SERVOS[f], 0) for f in FINGERS], start_delay=t + 0.4)

    def stretch(self):
        """Slow full stretch: splay wide, curl a little, relax."""
        self.cancel()
        self._queue([(SERVOS[f], 0) for f in FINGERS])
        self._queue([(SERVOS[f], 60) for f in FINGERS], start_delay=1.2)
        self._queue([(SERVOS[f], 0) for f in FINGERS], start_delay=2.0)

    def show_count(self, n):
        """Raise n fingers (0-5) in the natural counting order."""
        order = ["index", "middle", "ring", "pinky", "thumb"]
        up = set(order[:max(0, min(5, n))])
        self._queue([(SERVOS[f], 0 if f in up else 180) for f in FINGERS])


def speak(text):
    """Non-blocking text-to-speech (macOS 'say', Windows SAPI, else silent)."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(
                ["say", "-r", "170", text],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        elif system == "Windows":
            safe = text.replace("'", "")
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command",
                 "Add-Type -AssemblyName System.Speech; "
                 f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe}')"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass
