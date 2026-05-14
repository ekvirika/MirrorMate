import cv2
import mediapipe as mp
import serial
import json
import time
import math

# Arduino Configuration
ARDUINO_PORT = "COM6"  # Change to your Arduino port
BAUD_RATE = 9600
CAMERA_INDEX = 0  # Default webcam

# Initialize MediaPipe Hand Tracking
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Arduino serial connection
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Wait for Arduino to initialize
    print(f"✅ Connected to Arduino on {ARDUINO_PORT}")
    arduino_connected = True
except Exception as e:
    print(f"❌ Failed to connect to Arduino: {e}")
    print("Make sure Arduino is plugged in and code is uploaded!")
    arduino_connected = False

# Landmark names for reference
LANDMARK_NAMES = [
    "WRIST", "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_FINGER_MCP", "INDEX_FINGER_PIP", "INDEX_FINGER_DIP", "INDEX_FINGER_TIP",
    "MIDDLE_FINGER_MCP", "MIDDLE_FINGER_PIP", "MIDDLE_FINGER_DIP", "MIDDLE_FINGER_TIP",
    "RING_FINGER_MCP", "RING_FINGER_PIP", "RING_FINGER_DIP", "RING_FINGER_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP"
]

def calculate_finger_angle(landmarks, palm_idx, mcp_idx, pip_idx, dip_idx, tip_idx):
    """Calculate angle for a finger based on joint positions"""
    try:
        # Get positions
        palm = landmarks[palm_idx]
        mcp = landmarks[mcp_idx]
        pip = landmarks[pip_idx]
        dip = landmarks[dip_idx]
        tip = landmarks[tip_idx]

        # Calculate vectors
        mcp_to_pip = (pip[0] - mcp[0], pip[1] - mcp[1], pip[2] - mcp[2])
        pip_to_dip = (dip[0] - pip[0], dip[1] - pip[1], dip[2] - pip[2])

        # Calculate angle at PIP joint
        dot_product = (mcp_to_pip[0] * pip_to_dip[0] +
                      mcp_to_pip[1] * pip_to_dip[1] +
                      mcp_to_pip[2] * pip_to_dip[2])

        mcp_magnitude = math.sqrt(mcp_to_pip[0]**2 + mcp_to_pip[1]**2 + mcp_to_pip[2]**2)
        pip_magnitude = math.sqrt(pip_to_dip[0]**2 + pip_to_dip[1]**2 + pip_to_dip[2]**2)

        if mcp_magnitude == 0 or pip_magnitude == 0:
            return 90  # Neutral position

        cos_angle = dot_product / (mcp_magnitude * pip_magnitude)
        cos_angle = max(min(cos_angle, 1.0), -1.0)  # Clamp to valid range

        angle = math.degrees(math.acos(cos_angle))

        # Normalize to servo range (0-179 degrees)
        # Adjust based on your servo orientation
        normalized_angle = max(0, min(179, 90 + (angle - 90)))

        return int(normalized_angle)

    except (IndexError, TypeError):
        return 90  # Return neutral if calculation fails

def calculate_hand_rotation(landmarks):
    """Calculate overall hand rotation"""
    try:
        wrist = landmarks[0]
        middle_mcp = landmarks[9]  # Middle finger MCP

        # Calculate hand direction
        hand_vector = (middle_mcp[0] - wrist[0], middle_mcp[1] - wrist[1])

        # Calculate rotation angle
        angle = math.degrees(math.atan2(hand_vector[1], hand_vector[0]))

        # Normalize to 0-179 degrees
        normalized_angle = (angle + 180) / 2
        normalized_angle = max(0, min(179, normalized_angle))

        return int(normalized_angle)

    except (IndexError, TypeError):
        return 90

def send_servo_angles(results):
    """Calculate servo angles and send to Arduino"""
    if not results.multi_hand_landmarks or not arduino_connected:
        return

    for hand_landmarks in results.multi_hand_landmarks:
        # Convert landmarks to list of tuples
        landmarks = []
        for landmark in hand_landmarks.landmark:
            landmarks.append((landmark.x, landmark.y, landmark.z))

        # Calculate finger angles
        thumb_angle = calculate_finger_angle(landmarks, 0, 1, 2, 3, 4)
        index_angle = calculate_finger_angle(landmarks, 0, 5, 6, 7, 8)
        middle_angle = calculate_finger_angle(landmarks, 0, 9, 10, 11, 12)
        ring_angle = calculate_finger_angle(landmarks, 0, 13, 14, 15, 16)
        pinky_angle = calculate_finger_angle(landmarks, 0, 17, 18, 19, 20)
        hand_angle = calculate_hand_rotation(landmarks)

        # Send to Arduino
        data = f"T:{thumb_angle},I:{index_angle},M:{middle_angle},R:{ring_angle},P:{pinky_angle},H:{hand_angle}\n"

        try:
            arduino.write(data.encode())
            print(f"Sent: {data.strip()}")
        except Exception as e:
            print(f"Error sending to Arduino: {e}")

def main():
    print("=" * 60)
    print("DIRECT CAMERA TO ARDUINO HAND CONTROL")
    print("=" * 60)
    print(f"Arduino Port: {ARDUINO_PORT}")
    print(f"Camera: {CAMERA_INDEX}")
    print("\nInstructions:")
    print("  1. Make sure Arduino is connected and code is uploaded")
    print("  2. Show your hand to the camera")
    print("  3. Your InMoov hand should mirror your movements!")
    print("\nControls:")
    print("  - Press 'Q' to quit")
    print("  - Press 'S' to toggle hand skeleton overlay")
    print("=" * 60)

    # Open webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print(f"\n❌ Could not open camera {CAMERA_INDEX}")
        print("Try changing CAMERA_INDEX to 1 or 2")
        return

    # Set camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    show_skeleton = True
    frame_count = 0
    start_time = time.time()

    print("\n🎥 Camera opened successfully!")
    print("🤖 Arduino connected!")
    print("👋 Show your hand to the camera!\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process frame with MediaPipe
            results = hands.process(rgb_frame)

            # Send servo angles to Arduino
            if results.multi_hand_landmarks:
                send_servo_angles(results)
                frame_count += 1

            # Draw hand landmarks on frame (optional)
            if show_skeleton and results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=4),
                        mp_drawing.DrawingSpec(color=(255, 0, 255), thickness=2)
                    )

            # Display info
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            hand_count = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0

            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Hands: {hand_count}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Arduino: {'Connected' if arduino_connected else 'Disconnected'}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if arduino_connected else (0, 0, 255), 2)
            cv2.putText(frame, "Press Q to quit | S to toggle skeleton", (10, frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Show frame
            cv2.imshow('Hand Tracking - Arduino Control', frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('s') or key == ord('S'):
                show_skeleton = not show_skeleton
                print(f"Skeleton display: {'ON' if show_skeleton else 'OFF'}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    finally:
        print(f"\n📊 Session complete! Total frames processed: {frame_count}")

        # Cleanup
        cap.release()
        cv2.destroyAllWindows()

        if arduino_connected:
            try:
                arduino.close()
                print("🔌 Arduino connection closed")
            except:
                pass

        hands.close()
        print("✅ Cleanup complete!")

if __name__ == "__main__":
    main()
