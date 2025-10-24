import cv2
import mediapipe as mp
import serial
import json
import time
import math

# Arduino Configuration
ARDUINO_PORT = "/dev/cu.usbserial-1140"  # Arduino port for macOS
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
arduino = None
arduino_connected = False

def connect_to_arduino():
    """Try to connect to Arduino"""
    global arduino, arduino_connected

    try:
        print(f"Connecting to Arduino on {ARDUINO_PORT}...")
        arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for Arduino to initialize
        arduino_connected = True
        print(f"✅ Connected to Arduino on {ARDUINO_PORT}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Arduino: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if the Arduino is properly plugged in")
        print("2. Verify the port name using 'ls /dev/cu.*' in Terminal")
        print("3. Make sure you have permission to access the port")
        print("4. Close any other programs that might be using the port")
        print("5. Try unplugging and plugging the Arduino back in")
        return False

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

        # Calculate vectors for both joints
        palm_to_mcp = (mcp[0] - palm[0], mcp[1] - palm[1], mcp[2] - palm[2])
        mcp_to_pip = (pip[0] - mcp[0], pip[1] - mcp[1], pip[2] - mcp[2])
        pip_to_tip = (tip[0] - pip[0], tip[1] - pip[1], tip[2] - pip[2])

        # Calculate the vertical vector (assuming y-axis is vertical in camera space)
        vertical = (0, -1, 0)  # Pointing upward in camera space

        # Calculate angles between segments
        dot_product1 = (mcp_to_pip[0] * pip_to_tip[0] +
                       mcp_to_pip[1] * pip_to_tip[1] +
                       mcp_to_pip[2] * pip_to_tip[2])

        # Calculate magnitudes
        mcp_pip_magnitude = math.sqrt(mcp_to_pip[0]**2 + mcp_to_pip[1]**2 + mcp_to_pip[2]**2)
        pip_tip_magnitude = math.sqrt(pip_to_tip[0]**2 + pip_to_tip[1]**2 + pip_to_tip[2]**2)

        if mcp_pip_magnitude == 0 or pip_tip_magnitude == 0:
            return 90  # Neutral position

        # Calculate bend angle
        cos_angle = dot_product1 / (mcp_pip_magnitude * pip_tip_magnitude)
        cos_angle = max(min(cos_angle, 1.0), -1.0)  # Clamp to valid range
        bend_angle = math.degrees(math.acos(cos_angle))

        # Calculate the overall finger extension (0° = fully extended, 180° = fully bent)
        # We invert the angle because servos typically work in reverse (180° = open, 0° = closed)
        servo_angle = 180 - min(180, bend_angle)

        # Ensure the angle is within servo bounds
        servo_angle = max(0, min(180, servo_angle))

        return int(servo_angle)

    except (IndexError, TypeError):
        return 90  # Return neutral if calculation fails

def map_value(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def calculate_hand_rotation(landmarks):
    """Calculate overall hand rotation using multiple reference points for stability"""
    try:
        # Get key landmarks
        wrist = landmarks[0]
        index_mcp = landmarks[5]   # Index finger MCP
        middle_mcp = landmarks[9]  # Middle finger MCP
        ring_mcp = landmarks[13]   # Ring finger MCP
        pinky_mcp = landmarks[17]  # Pinky MCP

        # Calculate palm center using average of MCP joints
        palm_center_x = (index_mcp[0] + middle_mcp[0] + ring_mcp[0] + pinky_mcp[0]) / 4
        palm_center_y = (index_mcp[1] + middle_mcp[1] + ring_mcp[1] + pinky_mcp[1]) / 4

        # Calculate primary direction vector (wrist to palm center)
        primary_vector = (palm_center_x - wrist[0], palm_center_y - wrist[1])
        
        # Calculate angle relative to vertical axis (Y-axis in image space)
        angle = math.degrees(math.atan2(primary_vector[0], -primary_vector[1]))  # Negative Y for image space
        
        # Normalize angle to 0-180 range with some constraints for more natural movement
        # Map the natural hand rotation range (about -60 to +60 degrees) to servo range
        normalized_angle = map_value(angle, -60, 60, 0, 180)
        normalized_angle = max(0, min(180, normalized_angle))

        # Add stability threshold to prevent jitter
        if abs(normalized_angle - 90) < 5:  # 5-degree dead zone around center
            normalized_angle = 90

        return int(normalized_angle)

    except (IndexError, TypeError):
        return 90  # Return neutral position on error

def send_servo_angles(results):
    """Calculate servo angles and send to Arduino"""
    if not results.multi_hand_landmarks or not arduino_connected:
        return

    for hand_landmarks in results.multi_hand_landmarks:
        # Convert landmarks to list of tuples
        landmarks = []
        for landmark in hand_landmarks.landmark:
            landmarks.append((landmark.x, landmark.y, landmark.z))

        # Calculate wrist rotation (Servo 5)
        wrist_angle = calculate_hand_rotation(landmarks)
        wrist_servo = int(min(max(map_value(wrist_angle, 70, 110, 0, 180), 0), 180))

        # Calculate angles for all fingers
        # Thumb (Servo 0)
        thumb_angle = calculate_finger_angle(landmarks, 0, 1, 2, 3, 4)
        # Thumb has a more limited range of motion
        thumb_servo = int(min(max(map_value(thumb_angle, 170, 120, 0, 180), 0), 180))
        
        # Index (Servo 1)
        index_angle = calculate_finger_angle(landmarks, 0, 5, 6, 7, 8)
        # Index finger typically has full range of motion
        index_servo = int(min(max(map_value(index_angle, 180, 30, 0, 180), 0), 180))
        
        # Middle (Servo 2)
        middle_angle = calculate_finger_angle(landmarks, 0, 9, 10, 11, 12)
        # Middle finger typically has full range of motion
        middle_servo = int(min(max(map_value(middle_angle, 180, 30, 0, 180), 0), 180))
        
        # Ring (Servo 3)
        ring_angle = calculate_finger_angle(landmarks, 0, 13, 14, 15, 16)
        # Ring finger has slightly reduced range
        ring_servo = int(min(max(map_value(ring_angle, 180, 20, 0, 180), 30), 180))
        
        # Pinky (Servo 4)
        pinky_angle = calculate_finger_angle(landmarks, 0, 17, 18, 19, 20)
        # Pinky has more limited range of motion
        pinky_servo = int(min(max(map_value(pinky_angle, 175, 20, 0, 180), 0), 180))
        
        # Send commands one by one with a small delay
        try:
            print("\nFinger Angles Debug:")
            
            # Thumb (Servo 0)
            data = f"3:{thumb_servo}!\n"
            arduino.write(data.encode())
            arduino.flush()
            print(f"  Thumb  (S0): {thumb_angle:3.1f}° -> Servo: {thumb_servo}° [Sending: {data.strip()}]")
            time.sleep(0.02)  # Increased delay for thumb

            # Index (Servo 1)
            data = f"1:{index_servo}!\n"
            arduino.write(data.encode())
            arduino.flush()
            print(f"  Index  (S1): {index_angle:3.1f}° -> Servo: {index_servo}° [Sent: {data.strip()}]")
            time.sleep(0.01)
            
            # Middle (Servo 2)
            data = f"2:{middle_servo}!\n"
            arduino.write(data.encode())
            arduino.flush()
            print(f"  Middle (S2): {middle_angle:3.1f}° -> Servo: {middle_servo}° [Sent: {data.strip()}]")
            time.sleep(0.01)  # 10ms delay between commands
            
            # Ring (Servo 3)
            data = f"4:{ring_servo}!\n"
            arduino.write(data.encode())
            arduino.flush()
            print(f"  Ring   (S3): {ring_angle:3.1f}° -> Servo: {ring_servo}° [Sent: {data.strip()}]")
            time.sleep(0.01)

            # Pinky (Servo 4)
            data = f"5:{pinky_servo}!\n"
            print(f"  Pinky  (S4): {pinky_angle:3.1f}° -> Servo: {pinky_servo}° [Sending: {data.strip()}]")
            arduino.write(data.encode())
            arduino.flush()
            time.sleep(0.02)  # Increased delay for pinky
            
            # Wrist (Servo 5) with smoothing
            # Store current wrist angle for smoothing
            if not hasattr(send_servo_angles, 'last_wrist_angle'):
                send_servo_angles.last_wrist_angle = wrist_servo
            
            # Apply smoothing (reduce sudden changes)
            smoothing_factor = 0.3  # Adjust this value (0-1) to change smoothing amount
            smoothed_wrist = int(send_servo_angles.last_wrist_angle * (1 - smoothing_factor) + 
                               wrist_servo * smoothing_factor)
            
            # Update last angle
            send_servo_angles.last_wrist_angle = smoothed_wrist
            
            # Send wrist command
            data = f"6:{smoothed_wrist}!\n"
            print(f"  Wrist  (S5): Raw:{wrist_angle:3.1f}° -> Smooth:{smoothed_wrist}° [Sending: {data.strip()}]")
            arduino.write(data.encode())
            arduino.flush()
            time.sleep(0.03)  # Slightly longer delay for wrist stability
            
            print("-" * 40)
        except Exception as e:
            print(f"Error sending to Arduino: {e}")

def main():
    print("=" * 60)
    print("DIRECT CAMERA TO ARDUINO HAND CONTROL (PCA9685)")
    print("=" * 60)
    print("This script works with your existing PCA9685 servo setup")
    print("\nInstructions:")
    print("  1. Upload arduino_inmoov_pca9685.ino to your Arduino")
    print("  2. Make sure Arduino is connected and powered")
    print("  3. Show your hand to the camera")
    print("  4. Your InMoov hand should mirror your movements!")
    print("\nControls:")
    print("  - Press 'Q' to quit")
    print("  - Press 'S' to toggle hand skeleton overlay")
    print("=" * 60)

    # Try to connect to Arduino
    if not connect_to_arduino():
        print("\n❌ Arduino connection failed!")
        print("Troubleshooting steps:")
        print("1. Check if Arduino is plugged in")
        print("2. Check Device Manager for correct COM port")
        print("3. Close Arduino IDE if it's open")
        print("4. Make sure arduino_inmoov_pca9685.ino is uploaded")
        print("5. Try different COM ports (COM3, COM4, etc.)")
        return

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
            cv2.imshow('Hand Tracking - Arduino Control (PCA9685)', frame)

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

        if arduino_connected and arduino:
            try:
                arduino.close()
                print("🔌 Arduino connection closed")
            except:
                pass

        hands.close()
        print("✅ Cleanup complete!")

if __name__ == "__main__":
    main()
