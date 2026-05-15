import cv2
import mediapipe as mp
import serial
import time
import random
import math
import numpy as np

ARDUINO_PORT = "/dev/cu.usbserial-1110"
BAUD_RATE = 9600
CAMERA_INDEX = 0

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False, max_num_hands=1,
    min_detection_confidence=0.7, min_tracking_confidence=0.7
)

arduino = None
arduino_connected = False

# Servo positions
SERVO_FIST        = {3: 180, 1: 180, 2: 180, 4: 180, 5: 180}
SERVO_OPEN        = {3: 0,   1: 0,   2: 0,   4: 0,   5: 0  }
SERVO_MIDDLE_UP   = {3: 180, 1: 180, 2: 0,   4: 180, 5: 180}

# Servo queue
servo_state = "idle"   # idle, sending, displaying, resetting
servo_queue = []
servo_queue_idx = 0
last_servo_time = 0
SERVO_DELAY = 0.01

# App state
phase = "watching"   # watching, shocked, responding, cooldown
phase_start = 0.0
rude_count = 0
last_detected_lm = None

SHOCK_DURATION    = 1.6   # dramatic pause before robot responds
RESPOND_DURATION  = 2.5   # how long robot holds middle finger
COOLDOWN_DURATION = 2.0   # before we detect again

SHOCKED_LINES = [
    "EXCUSE ME?!",
    "HOW RUDE!",
    "OH NO YOU DIDN'T.",
    "REALLY?!",
    "I SEE WHAT YOU DID.",
    "BOLD MOVE.",
    "WOW. JUST WOW.",
    "MOM WOULD BE DISAPPOINTED.",
]

# Visual effects
shake_until = 0.0
flash_time = 0.0
FLASH_DUR = 0.3
shocked_line = ""


# ── Arduino ──────────────────────────────────────────────────────────────────

def connect_to_arduino():
    global arduino, arduino_connected
    try:
        arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(0.5)
        arduino_connected = True
        print(f"✅ Arduino connected on {ARDUINO_PORT}")
    except Exception as e:
        print(f"⚠️  No Arduino: {e}")


def _send(servo_id, angle):
    if arduino_connected:
        try:
            arduino.write(f"{servo_id}:{angle}!\n".encode())
            arduino.flush()
        except Exception:
            pass


# ── Servo queue ───────────────────────────────────────────────────────────────

def _load_queue(commands):
    global servo_queue, servo_queue_idx
    servo_queue = list(commands)
    servo_queue_idx = 0


def queue_servos(positions):
    global servo_state
    _load_queue(positions.items())
    servo_state = "sending"


def process_servo_queue():
    global servo_queue_idx, servo_state, last_servo_time
    if servo_state not in ("sending", "resetting"):
        return
    now = time.time()
    if now - last_servo_time < SERVO_DELAY:
        return
    if servo_queue_idx < len(servo_queue):
        sid, ang = servo_queue[servo_queue_idx]
        _send(sid, ang)
        servo_queue_idx += 1
        last_servo_time = now
    else:
        servo_state = "idle" if servo_state == "resetting" else "holding"


# ── Detection ─────────────────────────────────────────────────────────────────

def detect_middle_finger(lm):
    """True when only the middle finger is extended."""
    p = lm.landmark
    index  = p[8].y  < p[6].y
    middle = p[12].y < p[10].y
    ring   = p[16].y < p[14].y
    pinky  = p[20].y < p[18].y
    return middle and not index and not ring and not pinky


# ── Visual effects ────────────────────────────────────────────────────────────

def apply_shake(frame, intensity=12):
    """Shift the frame randomly to simulate camera shake."""
    dx = random.randint(-intensity, intensity)
    dy = random.randint(-intensity, intensity)
    h, w = frame.shape[:2]
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(frame, M, (w, h))


def draw_flash(frame, color=(0, 0, 220)):
    elapsed = time.time() - flash_time
    if elapsed >= FLASH_DUR:
        return
    alpha = 0.7 * (1.0 - elapsed / FLASH_DUR)
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (frame.shape[1], frame.shape[0]), color, -1)
    cv2.addWeighted(ov, alpha, frame, 1.0 - alpha, 0, frame)


def draw_censor_bar(frame, lm, w, h):
    """Black censored bar over the middle finger."""
    p = lm.landmark
    tip_x = int(p[12].x * w)
    tip_y = int(p[12].y * h)
    mcp_x = int(p[9].x * w)
    mcp_y = int(p[9].y * h)

    pad_x, pad_y = 18, 10
    x1 = min(tip_x, mcp_x) - pad_x
    y1 = min(tip_y, mcp_y) - pad_y
    x2 = max(tip_x, mcp_x) + pad_x
    y2 = max(tip_y, mcp_y) + pad_y

    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), -1)
    ts = cv2.getTextSize("CENSORED", cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)[0]
    cx = (x1 + x2) // 2 - ts[0] // 2
    cy = (y1 + y2) // 2 + ts[1] // 2
    cv2.putText(frame, "CENSORED", (cx, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)


def center_text(frame, text, cx, cy, scale, color, thick, shadow=True):
    ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thick)[0]
    x = cx - ts[0] // 2
    y = cy + ts[1] // 2
    if shadow:
        cv2.putText(frame, text, (x + 3, y + 3),
                    cv2.FONT_HERSHEY_DUPLEX, scale, (0, 0, 0), thick + 3)
    cv2.putText(frame, text, (x, y),
                cv2.FONT_HERSHEY_DUPLEX, scale, color, thick)


def draw_shocked_face(frame, cx, cy, r):
    """Simple O_O face drawn with cv2."""
    # Eyes
    eye_r = r // 3
    cv2.circle(frame, (cx - r // 2, cy - r // 4), eye_r, (255, 255, 255), -1)
    cv2.circle(frame, (cx + r // 2, cy - r // 4), eye_r, (255, 255, 255), -1)
    cv2.circle(frame, (cx - r // 2, cy - r // 4), eye_r // 2, (0, 0, 0), -1)
    cv2.circle(frame, (cx + r // 2, cy - r // 4), eye_r // 2, (0, 0, 0), -1)
    # Open mouth (O shape)
    cv2.ellipse(frame, (cx, cy + r // 3), (r // 3, r // 4), 0, 0, 360, (255, 255, 255), -1)
    cv2.ellipse(frame, (cx, cy + r // 3), (r // 3, r // 4), 0, 0, 360, (0, 0, 0), 2)


# ── UI ────────────────────────────────────────────────────────────────────────

def draw_ui(frame, hand_lm):
    h, w = frame.shape[:2]
    now = time.time()
    elapsed = now - phase_start

    draw_flash(frame)

    # Top bar
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, 65), (0, 0, 0), -1)
    cv2.addWeighted(ov, 0.65, frame, 0.35, 0, frame)
    cv2.putText(frame, f"Rude count: {rude_count}", (20, 44),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 80, 220), 2)

    if rude_count >= 5:
        cv2.putText(frame, "Absolute menace.", (w - 310, 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (160, 100, 100), 2)

    # Arduino status
    status = "Arduino: OK" if arduino_connected else "SIMULATION"
    sc = (0, 255, 0) if arduino_connected else (255, 165, 0)
    cv2.putText(frame, status, (w - 200, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, sc, 2)

    if phase == "watching":
        if hand_lm is None:
            center_text(frame, "Show your hand...", w // 2, h - 40, 0.9, (180, 180, 180), 2, shadow=False)

    elif phase == "shocked":
        # Pulsing shocked face
        pulse = int(5 * math.sin(elapsed * 20))
        draw_shocked_face(frame, w // 2, h // 2 - 60, 55 + pulse)

        # Shocked text
        scale = 2.2 + 0.3 * math.sin(elapsed * 15)
        center_text(frame, shocked_line, w // 2, h // 2 + 60, scale, (0, 60, 255), 5)

        # Countdown bar to robot response
        frac = elapsed / SHOCK_DURATION
        bw = 300
        bx = (w - bw) // 2
        by = h - 50
        cv2.rectangle(frame, (bx, by), (bx + bw, by + 14), (40, 40, 40), -1)
        cv2.rectangle(frame, (bx, by), (bx + int(bw * frac), by + 14), (0, 60, 220), -1)
        cv2.putText(frame, "robot preparing response...", (bx, by - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 140), 1)

    elif phase == "responding":
        center_text(frame, "RIGHT BACK AT YA.", w // 2, h // 2, 2.0, (0, 60, 220), 4)
        remaining = max(0.0, RESPOND_DURATION - elapsed)
        cv2.putText(frame, f"({remaining:.1f}s)", (w // 2 - 40, h // 2 + 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (140, 140, 140), 2)

    cv2.putText(frame, "Q to quit", (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120, 120, 120), 1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global phase, phase_start, rude_count, last_detected_lm
    global shake_until, flash_time, shocked_line

    connect_to_arduino()
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return

    print("\n🖕  Rude Detector — Ready!")
    print("  Show the middle finger and see what happens...\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        process_servo_queue()

        now = time.time()
        elapsed = now - phase_start
        hand_lm = None

        if results.multi_hand_landmarks:
            for lm in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, lm, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(80, 80, 200), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(200, 200, 200), thickness=2)
                )
                hand_lm = lm

                # Censor bar always on when middle finger visible
                if detect_middle_finger(lm):
                    draw_censor_bar(frame, lm, w, h)

                # Trigger detection only while watching
                if phase == "watching" and detect_middle_finger(lm):
                    rude_count += 1
                    shocked_line = SHOCKED_LINES[(rude_count - 1) % len(SHOCKED_LINES)]
                    phase = "shocked"
                    phase_start = now
                    flash_time = now
                    shake_until = now + 0.5
                    last_detected_lm = lm
                    queue_servos(SERVO_OPEN)   # robot reacts — opens hand in surprise
                    print(f"🖕  Detected! Count: {rude_count}  →  {shocked_line}")

        # Phase transitions
        if phase == "shocked" and elapsed >= SHOCK_DURATION:
            phase = "responding"
            phase_start = now
            queue_servos(SERVO_MIDDLE_UP)   # robot shows it back
            print("🤖 Robot responds...")

        elif phase == "responding" and elapsed >= RESPOND_DURATION:
            phase = "cooldown"
            phase_start = now
            queue_servos(SERVO_FIST)        # robot closes fist, resets

        elif phase == "cooldown" and elapsed >= COOLDOWN_DURATION:
            phase = "watching"
            print("👀 Watching...")

        # Screen shake during shocked phase
        if now < shake_until:
            frame = apply_shake(frame, intensity=10)

        draw_ui(frame, hand_lm)
        cv2.imshow("Rude Detector", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    if arduino_connected:
        arduino.close()
    print(f"\n📊 Total rude gestures: {rude_count}")
    if rude_count > 0:
        print("   Absolutely shameless.")


if __name__ == "__main__":
    main()
