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

GESTURE_SERVOS = {
    'rock':  {3: 180, 1: 180, 2: 180, 4: 180, 5: 180},
    'paper': {3: 0,   1: 0,   2: 0,   4: 0,   5: 0  },
}

# Servo queue
servo_state = "idle"   # idle, sending, displaying, resetting
servo_queue = []
servo_queue_idx = 0
last_servo_time = 0
SERVO_DELAY = 0.01

# High-five state
total_hf = 0
last_hf_time = 0.0
HF_COOLDOWN = 2.2       # seconds before another high-five counts
HF_HOLD_OPEN = 1.4      # seconds robot holds hand open before closing

# Visual effects
flash_time = 0.0
FLASH_DUR = 0.22
stars = []
STAR_LIFE = 1.1
IMPACT_WORDS = ["SLAP!", "HIGH FIVE!", "POW!", "YES!", "NICE!"]
impact_word = ""
impact_time = 0.0
IMPACT_DUR = 0.9

# "Tired" drooping effect after lots of high-fives (just cosmetic text)
TIRED_THRESHOLD = 10


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


def queue_gesture(gesture):
    global servo_state
    _load_queue(GESTURE_SERVOS[gesture].items())
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
        if servo_state == "sending":
            servo_state = "displaying"
        elif servo_state == "resetting":
            servo_state = "idle"


def tick_robot():
    """Auto-close robot hand after holding open."""
    global servo_state
    if servo_state == "displaying" and time.time() - last_hf_time > HF_HOLD_OPEN:
        _load_queue(GESTURE_SERVOS['rock'].items())
        servo_state = "resetting"


# ── Gesture detection ─────────────────────────────────────────────────────────

def detect_gesture(lm):
    p = lm.landmark
    index  = p[8].y  < p[6].y
    middle = p[12].y < p[10].y
    ring   = p[16].y < p[14].y
    pinky  = p[20].y < p[18].y
    ext = sum([index, middle, ring, pinky])
    if ext == 0:                      return 'rock'
    if ext >= 4:                      return 'paper'
    if ext == 2 and index and middle: return 'scissors'
    return None


def detect_high_five(lm, frame_h):
    """Open palm large enough = hand is close / raised toward camera."""
    if detect_gesture(lm) != 'paper':
        return False
    p = lm.landmark
    hand_h = abs(p[12].y - p[0].y) * frame_h
    return hand_h > frame_h * 0.22


def hand_center(lm, frame_w, frame_h):
    xs = [p.x for p in lm.landmark]
    ys = [p.y for p in lm.landmark]
    return int(sum(xs) / len(xs) * frame_w), int(sum(ys) / len(ys) * frame_h)


# ── Trigger ───────────────────────────────────────────────────────────────────

def trigger_high_five(cx, cy):
    global total_hf, last_hf_time, flash_time, impact_word, impact_time
    total_hf += 1
    last_hf_time = time.time()
    flash_time = time.time()
    impact_word = random.choice(IMPACT_WORDS)
    impact_time = time.time()
    spawn_stars(cx, cy, count=16)
    queue_gesture('paper')
    print(f"🖐  HIGH FIVE #{total_hf}!")


# ── Visual effects ────────────────────────────────────────────────────────────

def draw_star(frame, cx, cy, r, color):
    pts = []
    for i in range(10):
        a = i * math.pi / 5 - math.pi / 2
        rad = r if i % 2 == 0 else r // 2
        pts.append([int(cx + rad * math.cos(a)), int(cy + rad * math.sin(a))])
    cv2.fillPoly(frame, [np.array(pts, np.int32)], color)


def spawn_stars(cx, cy, count=12):
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(60, 160)
        stars.append({
            'x': float(cx), 'y': float(cy),
            'vx': math.cos(angle) * speed,
            'vy': math.sin(angle) * speed,
            'r': random.randint(14, 30),
            'color': random.choice([
                (0, 220, 255), (0, 255, 120), (255, 210, 0),
                (255, 80, 200), (255, 255, 255)
            ]),
            'born': time.time(),
        })


def tick_stars(frame, dt):
    alive = []
    now = time.time()
    for s in stars:
        age = now - s['born']
        if age < STAR_LIFE:
            frac = 1.0 - age / STAR_LIFE
            r = max(3, int(s['r'] * frac))
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            s['vy'] += 180 * dt   # gravity
            draw_star(frame, int(s['x']), int(s['y']), r, s['color'])
            alive.append(s)
    stars[:] = alive


def draw_flash(frame):
    elapsed = time.time() - flash_time
    if elapsed >= FLASH_DUR:
        return
    alpha = 0.65 * (1.0 - elapsed / FLASH_DUR)
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (frame.shape[1], frame.shape[0]), (0, 220, 255), -1)
    cv2.addWeighted(ov, alpha, frame, 1.0 - alpha, 0, frame)


def draw_impact(frame, w, h):
    elapsed = time.time() - impact_time
    if elapsed >= IMPACT_DUR or not impact_word:
        return
    # Shrinks from huge to normal as it settles
    t = elapsed / IMPACT_DUR
    scale = 3.5 - 1.5 * t
    thick = max(4, int(8 * (1 - t * 0.5)))
    ts = cv2.getTextSize(impact_word, cv2.FONT_HERSHEY_DUPLEX, scale, thick)[0]
    cx = w // 2 - ts[0] // 2
    cy = h // 2 + ts[1] // 2
    # Black outline for comic feel
    cv2.putText(frame, impact_word, (cx + 4, cy + 4),
                cv2.FONT_HERSHEY_DUPLEX, scale, (0, 0, 0), thick + 4)
    cv2.putText(frame, impact_word, (cx, cy),
                cv2.FONT_HERSHEY_DUPLEX, scale, (0, 220, 255), thick)


def draw_hand_ring(frame, lm, w, h):
    """Animated ring that pulses around the detected hand."""
    cx, cy = hand_center(lm, w, h)
    p = lm.landmark
    hand_h = int(abs(p[12].y - p[0].y) * h)
    radius = int(hand_h * 0.75)
    pulse = int(8 * math.sin(time.time() * 8))
    cv2.circle(frame, (cx, cy), radius + pulse, (0, 220, 255), 3)


# ── UI ────────────────────────────────────────────────────────────────────────

def draw_ui(frame, hand_lm, dt):
    h, w = frame.shape[:2]
    now = time.time()

    draw_flash(frame)
    tick_stars(frame, dt)
    draw_impact(frame, w, h)

    if hand_lm is not None:
        draw_hand_ring(frame, hand_lm, w, h)

    # Top bar
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, 70), (0, 0, 0), -1)
    cv2.addWeighted(ov, 0.65, frame, 0.35, 0, frame)

    hf_color = (0, 220, 255)
    cv2.putText(frame, f"High-fives: {total_hf}", (20, 47),
                cv2.FONT_HERSHEY_DUPLEX, 1.3, hf_color, 3)

    # Tired commentary
    if total_hf >= TIRED_THRESHOLD:
        cv2.putText(frame, "ok I need a break...", (w - 320, 47),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (160, 160, 160), 2)

    # Cooldown indicator
    cooldown_left = max(0.0, HF_COOLDOWN - (now - last_hf_time)) if last_hf_time > 0 else 0.0
    if cooldown_left > 0:
        bw = 180
        bx = w // 2 - bw // 2
        by = h - 55
        frac = cooldown_left / HF_COOLDOWN
        cv2.rectangle(frame, (bx, by), (bx + bw, by + 14), (40, 40, 40), -1)
        cv2.rectangle(frame, (bx, by), (bx + int(bw * (1 - frac)), by + 14), (0, 180, 255), -1)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + 14), (100, 100, 100), 1)
        cv2.putText(frame, "recharging...", (bx, by - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (140, 140, 140), 1)

    # Prompt
    if cooldown_left <= 0:
        msg = "Raise your open palm to high-five the robot!"
        ts = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)[0]
        cv2.putText(frame, msg, ((w - ts[0]) // 2, h - 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (220, 220, 220), 2)

    # Robot status
    if servo_state in ("sending", "resetting"):
        rs, rc = "Robot moving...", (255, 200, 0)
    elif servo_state == "displaying":
        rs, rc = "Robot ready!", (0, 255, 100)
    else:
        rs, rc = "Robot waiting", (160, 160, 160)
    cv2.putText(frame, rs, (w - 260, h - 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, rc, 2)

    # Arduino status
    status = "Arduino: OK" if arduino_connected else "SIMULATION"
    sc = (0, 255, 0) if arduino_connected else (255, 165, 0)
    cv2.putText(frame, status, (20, h - 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, sc, 2)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    connect_to_arduino()
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return

    print("\n🖐  High-Five Detector — Ready!")
    print("  Raise your open palm close to the camera to high-five the robot!")
    print("  Press Q to quit\n")

    prev_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        dt = now - prev_time
        prev_time = now

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        process_servo_queue()
        tick_robot()

        ready = (now - last_hf_time) >= HF_COOLDOWN
        detected_lm = None

        if results.multi_hand_landmarks:
            for lm in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, lm, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 220, 255), thickness=2, circle_radius=3),
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
                )
                detected_lm = lm
                if ready and detect_high_five(lm, h):
                    cx, cy = hand_center(lm, w, h)
                    trigger_high_five(cx, cy)

        draw_ui(frame, detected_lm, dt)
        cv2.imshow("High-Five Detector", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    if arduino_connected:
        arduino.close()
    print(f"\n🖐  Total high-fives: {total_hf}  —  thanks for the slaps!")


if __name__ == "__main__":
    main()
