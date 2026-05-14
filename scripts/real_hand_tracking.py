import cv2
import mediapipe as mp
import socket
import json
import time

# Configuration
UDP_IP = "127.0.0.1"  # Change if Unity is on another machine
UDP_PORT = 5065
CAMERA_INDEX = 0  # Default webcam (try 1, 2 if doesn't work)

# Initialize MediaPipe Hand Tracking
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Landmark names (MediaPipe order)
LANDMARK_NAMES = [
    "WRIST",
    "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_FINGER_MCP", "INDEX_FINGER_PIP", "INDEX_FINGER_DIP", "INDEX_FINGER_TIP",
    "MIDDLE_FINGER_MCP", "MIDDLE_FINGER_PIP", "MIDDLE_FINGER_DIP", "MIDDLE_FINGER_TIP",
    "RING_FINGER_MCP", "RING_FINGER_PIP", "RING_FINGER_DIP", "RING_FINGER_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP"
]

def send_hand_data(results):
    """Convert MediaPipe results to Unity format and send via UDP"""
    if not results.multi_hand_landmarks:
        return
    
    hands_data = []
    
    for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
        # Get handedness (Left/Right)
        handedness = results.multi_handedness[hand_idx].classification[0].label
        
        # Convert landmarks to Unity format
        landmarks = []
        for idx, landmark in enumerate(hand_landmarks.landmark):
            landmarks.append({
                "id": idx,
                "name": LANDMARK_NAMES[idx],
                "position": [
                    landmark.x,
                    landmark.y,
                    landmark.z
                ]
            })
        
        # Add forearm landmarks (21-24)
        # Get wrist position (landmark 0)
        wrist = landmarks[0]["position"]
        
        # Get middle finger MCP (landmark 9) to determine arm direction
        # The arm extends from wrist away from the hand
        if len(landmarks) > 9:
            mcp_middle = landmarks[9]["position"]
            # Direction from wrist to MCP (towards hand)
            hand_direction = [
                mcp_middle[0] - wrist[0],
                mcp_middle[1] - wrist[1], 
                mcp_middle[2] - wrist[2]
            ]
            
            # Normalize direction
            length = (hand_direction[0]**2 + hand_direction[1]**2 + hand_direction[2]**2) ** 0.5
            if length > 0:
                hand_direction = [d / length for d in hand_direction]
            
            # Extend in opposite direction for forearm (away from hand)
            forearm_direction = [-d for d in hand_direction]
            
            # Add forearm landmarks (21-24)
            forearm_names = ["ELBOW", "FOREARM_MID", "FOREARM_QUARTER", "FOREARM_THREE_QUARTER"]
            forearm_distances = [0.8, 0.6, 0.4, 0.2]  # Increased distances for better visibility
            
            for i, (name, distance) in enumerate(zip(forearm_names, forearm_distances)):
                forearm_pos = [
                    wrist[0] + forearm_direction[0] * distance,
                    wrist[1] + forearm_direction[1] * distance,
                    wrist[2] + forearm_direction[2] * distance
                ]
                
                landmarks.append({
                    "id": 21 + i,
                    "name": name,
                    "position": forearm_pos
                })
        
        # Create hand data
        hand_data = {
            "hand_type": handedness,
            "landmarks": landmarks,
            "timestamp": time.time()
        }
        hands_data.append(hand_data)
    
    # Wrap in multi-hand format
    multi_hand_data = {
        "hands": hands_data,
        "timestamp": time.time()
    }
    
    # Send via UDP
    message = json.dumps(multi_hand_data).encode('utf-8')
    sock.sendto(message, (UDP_IP, UDP_PORT))

def main():
    print("=" * 70)
    print("REAL-TIME HAND TRACKING TO UNITY")
    print("=" * 70)
    print(f"Sending to: {UDP_IP}:{UDP_PORT}")
    print(f"Camera: {CAMERA_INDEX}")
    print("\nInstructions:")
    print("  1. Make sure Unity is running in Play mode")
    print("  2. Show your hand(s) to the camera")
    print("  3. Watch the visualization in Unity!")
    print("\nControls:")
    print("  - Press 'Q' to quit")
    print("  - Press 'S' to show/hide skeleton on camera feed")
    print("=" * 70)
    
    # Open webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print(f"\nERROR: Could not open camera {CAMERA_INDEX}")
        print("Try changing CAMERA_INDEX to 1 or 2")
        return
    
    # Set camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    show_skeleton = True
    frame_count = 0
    start_time = time.time()
    
    print("\nCamera opened successfully! Starting hand tracking...")
    print("Show your hand to the camera!\n")
    
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
            
            # Send data to Unity
            if results.multi_hand_landmarks:
                send_hand_data(results)
                frame_count += 1
            
            # Draw hand landmarks on frame (optional)
            if show_skeleton and results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=3),
                        mp_drawing.DrawingSpec(color=(255, 0, 255), thickness=2)
                    )
            
            # Display FPS and hand count
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            hand_count = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
            
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Hands: {hand_count}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Packets sent: {frame_count}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "Press Q to quit | S to toggle skeleton", (10, frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Show frame
            cv2.imshow('Hand Tracking - Camera Feed', frame)
            
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
        print(f"\nStopping... Total packets sent: {frame_count}")
        cap.release()
        cv2.destroyAllWindows()
        sock.close()
        hands.close()
        print("Cleanup complete!")

if __name__ == "__main__":
    main()
