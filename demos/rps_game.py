import cv2
import mediapipe as mp
import serial
import time
import random

# Arduino Configuration
ARDUINO_PORT = "/dev/cu.usbserial-1110"  # Arduino port for macOS
BAUD_RATE = 9600
CAMERA_INDEX = 0  # Default webcam

# Initialize MediaPipe Hand Tracking
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,  # Only track one hand for the game
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Game state
player_score = 0
robot_score = 0
ties = 0
current_player_gesture = None
current_robot_gesture = None
game_result = None
countdown_active = False
countdown_start_time = 0
COUNTDOWN_DURATION = 3  # seconds

# Servo animation state (non-blocking)
servo_state = "idle"  # idle, sending, displaying, resetting
gesture_display_start = 0
servo_queue = []
servo_queue_idx = 0
last_servo_time = 0
SERVO_DELAY = 0.01

# Arduino serial connection (optional for now)
arduino = None
arduino_connected = False

def connect_to_arduino():
    """Try to connect to Arduino"""
    global arduino, arduino_connected
    
    try:
        print(f"Connecting to Arduino on {ARDUINO_PORT}...")
        arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(0.5)  # Wait for Arduino to initialize
        arduino_connected = True
        print(f"✅ Connected to Arduino on {ARDUINO_PORT}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Arduino: {e}")
        print("Continuing without Arduino connection...")
        return False

def detect_gesture(hand_landmarks):
    """
    Detect rock, paper, or scissors gesture based on finger positions
    Returns: 'rock', 'paper', 'scissors', or None
    """
    if not hand_landmarks:
        return None
    
    # Get landmark positions
    landmarks = hand_landmarks.landmark
    
    # Check if fingers are extended
    # Thumb: compare tip (4) with IP joint (3) x-coordinate
    thumb_extended = abs(landmarks[4].x - landmarks[3].x) > 0.05
    
    # Index finger: compare tip (8) with PIP joint (6) y-coordinate
    index_extended = landmarks[8].y < landmarks[6].y
    
    # Middle finger: compare tip (12) with PIP joint (10) y-coordinate
    middle_extended = landmarks[12].y < landmarks[10].y
    
    # Ring finger: compare tip (16) with PIP joint (14) y-coordinate
    ring_extended = landmarks[16].y < landmarks[14].y
    
    # Pinky: compare tip (20) with PIP joint (18) y-coordinate
    pinky_extended = landmarks[20].y < landmarks[18].y
    
    # Count extended fingers (excluding thumb for simplicity)
    extended_fingers = sum([index_extended, middle_extended, ring_extended, pinky_extended])
    
    # Gesture detection logic
    if extended_fingers == 0:
        return 'rock'
    elif extended_fingers >= 4:
        return 'paper'
    elif extended_fingers == 2 and index_extended and middle_extended:
        return 'scissors'
    
    return None

def randomize_robot_gesture():
    """Generate a random gesture for the robot"""
    return random.choice(['rock', 'paper', 'scissors'])

def determine_winner(player, robot):
    """
    Determine the winner of the round
    Returns: 'player', 'robot', or 'tie'
    """
    if player == robot:
        return 'tie'
    
    winning_combinations = {
        'rock': 'scissors',
        'scissors': 'paper',
        'paper': 'rock'
    }
    
    if winning_combinations[player] == robot:
        return 'player'
    else:
        return 'robot'

FINGER_NAMES = {3: "Thumb", 1: "Index", 2: "Middle", 4: "Ring", 5: "Pinky"}

GESTURE_SERVOS = {
    'rock':     {3: 180, 1: 180, 2: 180, 4: 180, 5: 180},
    'paper':    {3: 0,   1: 0,   2: 0,   4: 0,   5: 0  },
    'scissors': {3: 180, 1: 0,   2: 0,   4: 180, 5: 180},
}

def queue_gesture(gesture):
    """Queue servo commands for a gesture without blocking."""
    global servo_queue, servo_queue_idx, servo_state

    if gesture not in GESTURE_SERVOS:
        print(f"⚠️ Unknown gesture: {gesture}")
        return

    servo_queue = list(GESTURE_SERVOS[gesture].items())
    servo_queue_idx = 0
    servo_state = "sending"
    print(f"\n🤖 Robot showing: {gesture.upper()}")

def process_servo_queue():
    """Send one queued servo command per frame. Called every frame."""
    global servo_queue_idx, servo_state, last_servo_time, gesture_display_start

    if servo_state not in ("sending", "resetting"):
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
                print(f"  ✓ {FINGER_NAMES[servo_id]} (S{servo_id}): {angle}°")
            except Exception as e:
                print(f"❌ Error sending to Arduino: {e}")
        else:
            print(f"  → {FINGER_NAMES[servo_id]} (S{servo_id}): {angle}°")

        servo_queue_idx += 1
        last_servo_time = now
    else:
        # All commands sent
        if servo_state == "sending":
            print("✅ Gesture sent to robot")
            servo_state = "displaying"
            gesture_display_start = now
        elif servo_state == "resetting":
            print("✅ Hand reset complete")
            servo_state = "idle"

def tick_servo_animation():
    """Check display timer and trigger reset when 3 seconds have passed."""
    global servo_state, servo_queue_idx

    if servo_state == "displaying":
        if time.time() - gesture_display_start >= COUNTDOWN_DURATION:
            print("🔄 Resetting to open hand...")
            servo_queue[:] = list(GESTURE_SERVOS['paper'].items())
            servo_queue_idx = 0
            servo_state = "resetting"

def draw_game_ui(frame, player_gesture, robot_gesture, result):
    """Draw game UI on the frame"""
    height, width = frame.shape[:2]
    
    # Draw semi-transparent overlay for score area
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, 120), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    
    # Draw scores
    cv2.putText(frame, f"Player: {player_score}", (20, 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 0), 3)
    cv2.putText(frame, f"Robot: {robot_score}", (width - 250, 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 100, 255), 3)
    cv2.putText(frame, f"Ties: {ties}", (width // 2 - 80, 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 3)
    
    # Draw current gestures
    if player_gesture:
        cv2.putText(frame, f"You: {player_gesture.upper()}", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    if robot_gesture:
        cv2.putText(frame, f"Robot: {robot_gesture.upper()}", (width - 250, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # Draw result
    if result:
        result_text = ""
        result_color = (255, 255, 255)
        
        if result == 'player':
            result_text = "YOU WIN!"
            result_color = (0, 255, 0)
        elif result == 'robot':
            result_text = "ROBOT WINS!"
            result_color = (0, 100, 255)
        elif result == 'tie':
            result_text = "TIE!"
            result_color = (255, 255, 0)
        
        # Draw result with background
        text_size = cv2.getTextSize(result_text, cv2.FONT_HERSHEY_DUPLEX, 2, 4)[0]
        text_x = (width - text_size[0]) // 2
        text_y = height // 2
        
        cv2.rectangle(frame, 
                     (text_x - 20, text_y - text_size[1] - 20),
                     (text_x + text_size[0] + 20, text_y + 20),
                     (0, 0, 0), -1)
        cv2.putText(frame, result_text, (text_x, text_y),
                    cv2.FONT_HERSHEY_DUPLEX, 2, result_color, 4)
    
    # Draw countdown if active
    if countdown_active:
        elapsed = time.time() - countdown_start_time
        remaining = COUNTDOWN_DURATION - int(elapsed)
        if remaining > 0:
            countdown_text = str(remaining)
            text_size = cv2.getTextSize(countdown_text, cv2.FONT_HERSHEY_DUPLEX, 4, 8)[0]
            text_x = (width - text_size[0]) // 2
            text_y = height // 2 + 100
            cv2.putText(frame, countdown_text, (text_x, text_y),
                       cv2.FONT_HERSHEY_DUPLEX, 4, (255, 255, 0), 8)
    
    # Draw Arduino connection status
    status_text = "Arduino: CONNECTED" if arduino_connected else "Arduino: SIMULATION MODE"
    status_color = (0, 255, 0) if arduino_connected else (255, 165, 0)
    cv2.putText(frame, status_text, (width - 300, height - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
    
    # Draw instructions
    cv2.putText(frame, "Press SPACE to play | Q to quit | R to reset scores",
                (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

def main():
    global player_score, robot_score, ties
    global current_player_gesture, current_robot_gesture, game_result
    global countdown_active, countdown_start_time, servo_state
    
    # Try to connect to Arduino (optional)
    connect_to_arduino()
    
    # Open webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print("❌ Error: Could not open webcam")
        return
    
    print("\n🎮 Rock Paper Scissors Game Started!")
    print("Instructions:")
    print("  - Show your hand gesture (rock/paper/scissors)")
    print("  - Press SPACE to start a round")
    print("  - Press R to reset scores")
    print("  - Press Q to quit")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Failed to read from webcam")
            break
        
        # Flip frame horizontally for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process hand detection
        results = hands.process(rgb_frame)
        
        # Detect player gesture
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
                )

                # Detect gesture
                current_player_gesture = detect_gesture(hand_landmarks)
        else:
            current_player_gesture = None

        # Tick servo animation (non-blocking)
        process_servo_queue()
        tick_servo_animation()

        # Handle countdown
        if countdown_active:
            elapsed = time.time() - countdown_start_time
            if elapsed >= COUNTDOWN_DURATION:
                # Countdown finished - play the round
                countdown_active = False
                
                if current_player_gesture:
                    # Generate robot gesture
                    current_robot_gesture = randomize_robot_gesture()

                    # Queue gesture commands (non-blocking)
                    print(f"\n🎮 Playing Round:")
                    print(f"   Your gesture: {current_player_gesture.upper()}")
                    queue_gesture(current_robot_gesture)
                    
                    # Determine winner
                    result = determine_winner(current_player_gesture, current_robot_gesture)
                    
                    if result == 'player':
                        player_score += 1
                        game_result = 'player'
                    elif result == 'robot':
                        robot_score += 1
                        game_result = 'robot'
                    else:
                        ties += 1
                        game_result = 'tie'
                    
                    print(f"\n🎮 Round Result:")
                    print(f"   Player: {current_player_gesture.upper()}")
                    print(f"   Robot: {current_robot_gesture.upper()}")
                    print(f"   Winner: {game_result.upper()}")
                    print(f"   Score - Player: {player_score} | Robot: {robot_score} | Ties: {ties}")
                else:
                    print("⚠️ No gesture detected! Try again.")
                    game_result = None
                    current_robot_gesture = None
        
        # Draw UI
        draw_game_ui(frame, current_player_gesture, current_robot_gesture, game_result)
        
        # Display frame
        cv2.imshow('Rock Paper Scissors Game', frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\n👋 Quitting game...")
            break
        elif key == ord(' ') and not countdown_active and servo_state == "idle":
            # Start countdown
            print("\n⏱️ Starting countdown...")
            countdown_active = True
            countdown_start_time = time.time()
            game_result = None
            current_robot_gesture = None
        elif key == ord('r'):
            # Reset scores
            player_score = 0
            robot_score = 0
            ties = 0
            game_result = None
            current_robot_gesture = None
            servo_state = "idle"
            print("\n🔄 Scores reset!")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    if arduino_connected:
        arduino.close()
    
    print("\n📊 Final Score:")
    print(f"   Player: {player_score}")
    print(f"   Robot: {robot_score}")
    print(f"   Ties: {ties}")

if __name__ == "__main__":
    main()
