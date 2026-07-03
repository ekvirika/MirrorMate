import cv2
import mediapipe as mp
import serial
import subprocess
import time
import random
import sys
import platform
sys.path.insert(0, '..')

from arduino_utils import find_arduino_port, connect_arduino

# Configuration
BAUD_RATE = 9600
CAMERA_INDEX = 0

# Initialize MediaPipe Hand Tracking
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Game state
player_score = 0
robot_score = 0
ties = 0
current_player_gesture = None   # live reading every frame
locked_player_gesture = None    # locked at the SHOOT moment
current_robot_gesture = None
game_result = None
countdown_active = False
countdown_start_time = 0
last_beat = -1
COUNTDOWN_DURATION = 3

# SHOOT flash
shoot_flash_time = 0
SHOOT_FLASH_DURATION = 0.6

# Servo animation state
# States: idle → sending_fist → holding → (pumping → holding) → sending → displaying → resetting → idle
servo_state = "idle"
gesture_display_start = 0
servo_queue = []
servo_queue_idx = 0
last_servo_time = 0
SERVO_DELAY = 0.01

arduino = None
arduino_connected = False

FINGER_NAMES = {3: "Thumb", 1: "Index", 2: "Middle", 4: "Ring", 5: "Pinky"}

GESTURE_SERVOS = {
    'rock':     {3: 180, 1: 180, 2: 180, 4: 180, 5: 180},
    'paper':    {3: 0,   1: 0,   2: 0,   4: 0,   5: 0  },
    'scissors': {3: 180, 1: 0,   2: 0,   4: 180, 5: 180},
}

BEAT_WORDS  = {3: "Rock...", 2: "Paper...", 1: "Scissors..."}
BEAT_SPEECH = {3: "Rock",   2: "Paper",   1: "Scissors"}  # spoken aloud


def speak(text):
    """Non-blocking text-to-speech via macOS say command."""
    subprocess.Popen(
        ["say", "-r", "160", text],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def connect_to_arduino():
    global arduino, arduino_connected
    port = find_arduino_port(verbose=True)
    if not port:
        print("Continuing without Arduino connection...")
        return False

    arduino = connect_arduino(port, BAUD_RATE)
    if arduino:
        time.sleep(0.5)
        arduino_connected = True
        print(f"✅ Connected!")
        return True
    else:
        print("Continuing without Arduino connection...")
        return False


def detect_gesture(hand_landmarks):
    if not hand_landmarks:
        return None
    landmarks = hand_landmarks.landmark
    index_extended  = landmarks[8].y  < landmarks[6].y
    middle_extended = landmarks[12].y < landmarks[10].y
    ring_extended   = landmarks[16].y < landmarks[14].y
    pinky_extended  = landmarks[20].y < landmarks[18].y
    extended = sum([index_extended, middle_extended, ring_extended, pinky_extended])
    if extended == 0:
        return 'rock'
    elif extended >= 4:
        return 'paper'
    elif extended == 2 and index_extended and middle_extended:
        return 'scissors'
    return None


def determine_winner(player, robot):
    if player == robot:
        return 'tie'
    beats = {'rock': 'scissors', 'scissors': 'paper', 'paper': 'rock'}
    return 'player' if beats[player] == robot else 'robot'


# --- Servo helpers ---

def _load_queue(commands):
    global servo_queue, servo_queue_idx
    servo_queue = commands
    servo_queue_idx = 0


def queue_fist():
    """Robot makes a fist at round start — same as a human player."""
    global servo_state
    _load_queue(list(GESTURE_SERVOS['rock'].items()))
    servo_state = "sending_fist"


def queue_pump():
    """Half-open then re-close — one pump on each beat."""
    global servo_state
    open_cmds  = [(s, 90)  for s in [3, 1, 2, 4, 5]]
    close_cmds = [(s, 180) for s in [3, 1, 2, 4, 5]]
    _load_queue(open_cmds + close_cmds)
    servo_state = "pumping"


def queue_gesture(gesture):
    """Reveal the robot's chosen gesture at SHOOT."""
    global servo_state
    if gesture not in GESTURE_SERVOS:
        return
    _load_queue(list(GESTURE_SERVOS[gesture].items()))
    servo_state = "sending"
    print(f"🤖 Robot reveals: {gesture.upper()}")


def process_servo_queue():
    global servo_queue_idx, servo_state, last_servo_time, gesture_display_start

    if servo_state not in ("sending_fist", "sending", "resetting", "pumping"):
        return

    now = time.time()
    if now - last_servo_time < SERVO_DELAY:
        return

    if servo_queue_idx < len(servo_queue):
        servo_id, angle = servo_queue[servo_queue_idx]
        if arduino_connected:
            try:
                arduino.write(f"{servo_id}:{angle}!\n".encode())
                arduino.flush()
            except Exception as e:
                print(f"❌ Arduino error: {e}")
        servo_queue_idx += 1
        last_servo_time = now
    else:
        if servo_state == "sending_fist":
            servo_state = "holding"           # hold fist, no auto-reset
        elif servo_state == "pumping":
            servo_state = "holding"           # return to holding after pump
        elif servo_state == "sending":
            servo_state = "displaying"
            gesture_display_start = now
        elif servo_state == "resetting":
            servo_state = "idle"
            print("✅ Hand reset")


def tick_servo_animation():
    """Auto-reset hand 3 seconds after SHOOT reveal."""
    global servo_state
    if servo_state == "displaying":
        if time.time() - gesture_display_start >= COUNTDOWN_DURATION:
            _load_queue(list(GESTURE_SERVOS['paper'].items()))
            servo_state = "resetting"
            print("🔄 Resetting hand...")


# --- UI ---

def draw_game_ui(frame):
    height, width = frame.shape[:2]
    now = time.time()

    # Score bar overlay
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, 120), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    cv2.putText(frame, f"Player: {player_score}", (20, 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 0), 3)
    cv2.putText(frame, f"Ties: {ties}", (width // 2 - 80, 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 3)
    cv2.putText(frame, f"Robot: {robot_score}", (width - 250, 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 100, 255), 3)

    # Locked gestures (shown after SHOOT)
    if locked_player_gesture:
        cv2.putText(frame, f"You: {locked_player_gesture.upper()}", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    if current_robot_gesture:
        cv2.putText(frame, f"Robot: {current_robot_gesture.upper()}", (width - 250, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Countdown beat words (Rock... Paper... Scissors...)
    if countdown_active:
        elapsed = now - countdown_start_time
        remaining = COUNTDOWN_DURATION - int(elapsed)
        beat_word = BEAT_WORDS.get(remaining, "")
        if beat_word:
            ts = cv2.getTextSize(beat_word, cv2.FONT_HERSHEY_DUPLEX, 2, 4)[0]
            tx = (width - ts[0]) // 2
            cv2.putText(frame, beat_word, (tx, height // 2 + 60),
                        cv2.FONT_HERSHEY_DUPLEX, 2, (255, 255, 0), 4)

    # SHOOT flash
    shoot_elapsed = now - shoot_flash_time if shoot_flash_time > 0 else 999
    if shoot_elapsed < SHOOT_FLASH_DURATION:
        ts = cv2.getTextSize("SHOOT!", cv2.FONT_HERSHEY_DUPLEX, 3, 6)[0]
        tx = (width - ts[0]) // 2
        cv2.putText(frame, "SHOOT!", (tx, height // 2 + 60),
                    cv2.FONT_HERSHEY_DUPLEX, 3, (0, 80, 255), 6)

    # Result (shown after SHOOT flash fades)
    if game_result and shoot_elapsed >= SHOOT_FLASH_DURATION:
        labels = {
            'player': ("YOU WIN!",    (0, 255, 0)),
            'robot':  ("ROBOT WINS!", (0, 100, 255)),
            'tie':    ("TIE!",        (255, 255, 0)),
        }
        result_text, result_color = labels[game_result]
        ts = cv2.getTextSize(result_text, cv2.FONT_HERSHEY_DUPLEX, 2, 4)[0]
        tx = (width - ts[0]) // 2
        ty = height // 2
        cv2.rectangle(frame, (tx - 20, ty - ts[1] - 20), (tx + ts[0] + 20, ty + 20), (0, 0, 0), -1)
        cv2.putText(frame, result_text, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, 2, result_color, 4)

    # Status / instructions
    status = "Arduino: CONNECTED" if arduino_connected else "Arduino: SIMULATION MODE"
    status_color = (0, 255, 0) if arduino_connected else (255, 165, 0)
    cv2.putText(frame, status, (width - 300, height - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
    cv2.putText(frame, "SPACE to play  |  R reset  |  Q quit",
                (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


# --- Main ---

def main():
    global player_score, robot_score, ties
    global current_player_gesture, locked_player_gesture, current_robot_gesture, game_result
    global countdown_active, countdown_start_time, last_beat
    global servo_state, shoot_flash_time

    connect_to_arduino()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return

    print("\n🎮 Rock Paper Scissors — Ready!")
    print("  Form your gesture during countdown, reveal on SHOOT!")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        # Live hand detection (shown during countdown, not locked yet)
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
                )
                current_player_gesture = detect_gesture(hand_landmarks)
        else:
            current_player_gesture = None

        # Servo animation tick
        process_servo_queue()
        tick_servo_animation()

        # Countdown logic
        if countdown_active:
            elapsed = time.time() - countdown_start_time
            remaining = COUNTDOWN_DURATION - int(elapsed)

            # Pump fist and speak on each beat change
            if remaining != last_beat and remaining > 0:
                last_beat = remaining
                speak(BEAT_SPEECH[remaining])
                if servo_state == "holding":
                    queue_pump()

            # SHOOT moment
            if elapsed >= COUNTDOWN_DURATION:
                countdown_active = False
                locked_player_gesture = current_player_gesture  # lock whatever they're showing
                shoot_flash_time = time.time()
                speak("Shoot!")

                if locked_player_gesture:
                    current_robot_gesture = random.choice(['rock', 'paper', 'scissors'])
                    queue_gesture(current_robot_gesture)

                    result = determine_winner(locked_player_gesture, current_robot_gesture)
                    if result == 'player':
                        player_score += 1
                        speak("You win!")
                    elif result == 'robot':
                        robot_score += 1
                        speak("Robot wins!")
                    else:
                        ties += 1
                        speak("Tie!")
                    game_result = result

                    print(f"   You: {locked_player_gesture.upper()} | "
                          f"Robot: {current_robot_gesture.upper()} → {result.upper()}")
                    print(f"   Score → Player {player_score} | Robot {robot_score} | Ties {ties}")
                else:
                    print("⚠️ No gesture detected at SHOOT — try again")
                    game_result = None
                    servo_state = "idle"

        draw_game_ui(frame)
        cv2.imshow('Rock Paper Scissors', frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord(' ') and not countdown_active and servo_state == "idle":
            print("\n🥊 Round starting...")
            countdown_active = True
            countdown_start_time = time.time()
            last_beat = -1
            locked_player_gesture = None
            current_robot_gesture = None
            game_result = None
            shoot_flash_time = 0
            queue_fist()    # robot goes to fist — same starting position as player
        elif key == ord('r'):
            player_score = robot_score = ties = 0
            game_result = None
            locked_player_gesture = None
            current_robot_gesture = None
            servo_state = "idle"
            print("🔄 Scores reset")

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    if arduino_connected:
        arduino.close()

    print(f"\n📊 Final: Player {player_score} | Robot {robot_score} | Ties {ties}")


if __name__ == "__main__":
    main()
