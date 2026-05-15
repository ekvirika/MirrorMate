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
    'rock':     {3: 180, 1: 180, 2: 180, 4: 180, 5: 180},
    'paper':    {3: 0,   1: 0,   2: 0,   4: 0,   5: 0  },
    'scissors': {3: 180, 1: 0,   2: 0,   4: 180, 5: 180},
}
GESTURE_COLOR = {'rock': (80, 80, 220), 'paper': (60, 200, 80), 'scissors': (220, 80, 80)}

# Servo queue state
servo_state = "idle"   # idle, sending, resetting, wagging
servo_queue = []
servo_queue_idx = 0
last_servo_time = 0
SERVO_DELAY = 0.01

# Finger-wag state (time-based, bypasses queue)
wag_step = 0
wag_step_time = 0
WAG_STEPS = 6        # 3 open/close cycles
WAG_STEP_DUR = 0.22  # seconds per step

# Game phases: idle → showing → player_turn → correct/wrong → idle
phase = "idle"
phase_start = 0.0
simon_gesture = None
player_gesture_live = None

score = 0
streak = 0
streak_best = 0

SHOW_DURATION   = 3.0
PLAYER_DURATION = 4.0
RESULT_DURATION = 2.8

# Confetti particles
confetti = []


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


def queue_reset():
    global servo_state
    _load_queue(GESTURE_SERVOS['paper'].items())
    servo_state = "resetting"


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
        servo_state = "idle"


# ── Finger wag ────────────────────────────────────────────────────────────────

def start_wag():
    global wag_step, wag_step_time, servo_state
    # Put all fingers closed except index (pointing position first)
    for sid, ang in {3: 180, 2: 180, 4: 180, 5: 180}.items():
        _send(sid, ang)
    _send(1, 0)   # index extended
    wag_step = 0
    wag_step_time = time.time()
    servo_state = "wagging"


def tick_wag():
    global wag_step, wag_step_time, servo_state
    if servo_state != "wagging":
        return
    now = time.time()
    if now - wag_step_time < WAG_STEP_DUR:
        return
    angle = 0 if wag_step % 2 == 0 else 130   # open / curl
    _send(1, angle)
    wag_step += 1
    wag_step_time = now
    if wag_step >= WAG_STEPS:
        servo_state = "idle"


# ── Gesture detection ─────────────────────────────────────────────────────────

def detect_gesture(lm):
    if not lm:
        return None
    p = lm.landmark
    index  = p[8].y  < p[6].y
    middle = p[12].y < p[10].y
    ring   = p[16].y < p[14].y
    pinky  = p[20].y < p[18].y
    ext = sum([index, middle, ring, pinky])
    if ext == 0:                           return 'rock'
    if ext >= 4:                           return 'paper'
    if ext == 2 and index and middle:      return 'scissors'
    return None


# ── Visual effects ────────────────────────────────────────────────────────────

def spawn_confetti(w, h, count=90):
    global confetti
    confetti = []
    for _ in range(count):
        confetti.append({
            'x': float(random.randint(0, w)),
            'y': float(random.randint(-120, 0)),
            'vx': random.uniform(-3, 3),
            'vy': random.uniform(4, 11),
            'color': (random.randint(30, 255), random.randint(30, 255), random.randint(30, 255)),
            'size': random.randint(5, 11),
            'rect': random.random() > 0.5,
        })


def tick_confetti(frame, h):
    alive = []
    for p in confetti:
        p['x'] += p['vx']
        p['y'] += p['vy']
        if p['y'] < h:
            x, y = int(p['x']), int(p['y'])
            if p['rect']:
                cv2.rectangle(frame, (x, y), (x + p['size'], y + p['size'] // 2), p['color'], -1)
            else:
                cv2.circle(frame, (x, y), p['size'] // 2, p['color'], -1)
            alive.append(p)
    confetti[:] = alive


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


def center_text(frame, text, cx, cy, scale, color, thick):
    ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thick)[0]
    cv2.putText(frame, text, (cx - ts[0] // 2, cy + ts[1] // 2),
                cv2.FONT_HERSHEY_DUPLEX, scale, color, thick)


# ── UI ────────────────────────────────────────────────────────────────────────

def draw_ui(frame):
    h, w = frame.shape[:2]
    now = time.time()
    elapsed = now - phase_start

    # Score bar
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, 72), (0, 0, 0), -1)
    cv2.addWeighted(ov, 0.65, frame, 0.35, 0, frame)

    cv2.putText(frame, f"Score: {score}", (20, 48),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2)
    streak_label = f"Streak: {streak}" + (" 🔥" if streak >= 3 else "")
    cv2.putText(frame, streak_label, (w // 2 - 100, 48),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 200, 255), 2)
    cv2.putText(frame, f"Best: {streak_best}", (w - 210, 48),
                cv2.FONT_HERSHEY_DUPLEX, 1.0, (160, 160, 160), 2)

    if phase == "idle":
        center_text(frame, "SIMON SAYS", w // 2, h // 2 - 60, 2.8, (0, 220, 255), 5)
        center_text(frame, "Press SPACE to play", w // 2, h // 2 + 40, 1.0, (200, 200, 200), 2)
        cv2.putText(frame, "Q to quit", (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 2)

    elif phase == "showing":
        remaining = max(0.0, SHOW_DURATION - elapsed)
        col = GESTURE_COLOR.get(simon_gesture, (200, 200, 200))
        center_text(frame, "SIMON SAYS...", w // 2, h // 2 - 110, 1.6, (255, 220, 0), 3)
        center_text(frame, simon_gesture.upper(), w // 2, h // 2, 3.2, col, 6)
        center_text(frame, f"Remember it!  {remaining:.1f}s", w // 2, h // 2 + 100, 0.9, (180, 180, 180), 2)

    elif phase == "player_turn":
        remaining = max(0.0, PLAYER_DURATION - elapsed)
        frac = remaining / PLAYER_DURATION
        center_text(frame, "YOUR TURN!", w // 2, h // 2 - 110, 1.8, (80, 255, 80), 3)
        col = GESTURE_COLOR.get(simon_gesture, (200, 200, 200))
        center_text(frame, f"Show:  {simon_gesture.upper()}", w // 2, h // 2 - 48, 1.6, col, 3)

        # Timer bar
        bw = int(w * 0.55)
        bx = (w - bw) // 2
        by = h // 2 + 20
        bar_col = (0, 200, 0) if frac > 0.4 else (0, 160, 255) if frac > 0.2 else (0, 0, 220)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + 22), (40, 40, 40), -1)
        cv2.rectangle(frame, (bx, by), (bx + int(bw * frac), by + 22), bar_col, -1)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + 22), (140, 140, 140), 2)

        if player_gesture_live:
            match = player_gesture_live == simon_gesture
            mc = (0, 255, 0) if match else (0, 80, 220)
            label = f"You: {player_gesture_live.upper()}" + (" ✓" if match else " ✗")
            center_text(frame, label, w // 2, h // 2 + 78, 1.1, mc, 2)

    elif phase == "correct":
        tick_confetti(frame, h)
        # Pulsing star
        r = int(55 + 18 * math.sin(elapsed * 12))
        draw_star(frame, w // 2, h // 2 - 80, r, (0, 255, 100))
        center_text(frame, "CORRECT!", w // 2, h // 2 + 20, 3.0, (0, 255, 80), 6)
        if streak > 1:
            center_text(frame, f"STREAK  x{streak}!", w // 2, h // 2 + 100, 1.4, (0, 220, 255), 3)

    elif phase == "wrong":
        draw_big_x(frame, w // 2, h // 2 - 60, 70)
        center_text(frame, "WRONG!", w // 2, h // 2 + 30, 3.0, (0, 0, 220), 6)
        if simon_gesture:
            center_text(frame, f"It was  {simon_gesture.upper()}", w // 2, h // 2 + 110, 1.1, (180, 180, 180), 2)

    # Arduino status (bottom-right)
    status = "Arduino: CONNECTED" if arduino_connected else "SIMULATION MODE"
    sc = (0, 255, 0) if arduino_connected else (255, 165, 0)
    cv2.putText(frame, status, (w - 290, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, sc, 2)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global phase, phase_start, simon_gesture, player_gesture_live
    global score, streak, streak_best

    connect_to_arduino()
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return

    print("\n🤖 Simon Says — Ready!")
    print("  Robot shows a gesture → you copy it → robot reacts")
    print("  Press SPACE to start each round, Q to quit\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        player_gesture_live = None
        if results.multi_hand_landmarks:
            for lm in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, lm, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
                )
                player_gesture_live = detect_gesture(lm)

        process_servo_queue()
        tick_wag()

        now = time.time()
        elapsed = now - phase_start

        if phase == "showing" and elapsed >= SHOW_DURATION:
            phase = "player_turn"
            phase_start = now

        elif phase == "player_turn" and elapsed >= PLAYER_DURATION:
            if player_gesture_live == simon_gesture:
                phase = "correct"
                score += 1
                streak += 1
                streak_best = max(streak_best, streak)
                queue_gesture('paper')
                spawn_confetti(frame.shape[1], frame.shape[0])
                print(f"✅ Correct! Score={score}  Streak={streak}")
            else:
                phase = "wrong"
                streak = 0
                start_wag()
                shown = player_gesture_live or "nothing"
                print(f"❌ Wrong — Simon: {simon_gesture}  You: {shown}")
            phase_start = now

        elif phase in ("correct", "wrong") and elapsed >= RESULT_DURATION:
            if phase == "correct":
                queue_reset()
            phase = "idle"

        draw_ui(frame)
        cv2.imshow("Simon Says", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord(' ') and phase == "idle":
            simon_gesture = random.choice(['rock', 'paper', 'scissors'])
            phase = "showing"
            phase_start = time.time()
            queue_gesture(simon_gesture)
            print(f"\n🤖 Simon says: {simon_gesture.upper()}")

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    if arduino_connected:
        arduino.close()
    print(f"\n📊 Final — Score: {score}  Best Streak: {streak_best}")


if __name__ == "__main__":
    main()
