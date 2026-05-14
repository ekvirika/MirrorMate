import socket
import json
import time
import random
import math

# Configuration
UDP_IP = "127.0.0.1"  # Change to your Unity machine's IP if needed
UDP_PORT = 5065

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def generate_hand_data(handedness="Left"):
    """Generate mock hand landmark data"""
    landmarks = []
    
    # Landmark names for MediaPipe hand tracking
    landmark_names = [
        "WRIST", "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
        "INDEX_FINGER_MCP", "INDEX_FINGER_PIP", "INDEX_FINGER_DIP", "INDEX_FINGER_TIP",
        "MIDDLE_FINGER_MCP", "MIDDLE_FINGER_PIP", "MIDDLE_FINGER_DIP", "MIDDLE_FINGER_TIP",
        "RING_FINGER_MCP", "RING_FINGER_PIP", "RING_FINGER_DIP", "RING_FINGER_TIP",
        "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP"
    ]
    
    # Generate 21 landmarks (0-20) for a basic hand
    for i in range(21):
        # Simple hand shape - MUCH bigger and centered
        x = math.sin(i * 0.3) * 5.0  # Much bigger
        y = -i * 1.0  # Bigger spacing
        z = 0.5  # Very close to camera at origin
        
        # Add some animation
        t = time.time()
        x += math.sin(t + i * 0.1) * 0.5
        y += math.cos(t * 0.5) * 2.0
        
        landmarks.append({
            "id": i,
            "name": landmark_names[i],
            "position": [x, y, z]
        })
    
    # Create the hand data structure
    hand_data = {
        "hand_type": handedness,
        "landmarks": landmarks,
        "timestamp": time.time()
    }
    
    # Wrap in multi-hand format
    multi_hand_data = {
        "hands": [hand_data],
        "timestamp": time.time()
    }
    
    return multi_hand_data

def main():
    print(f"Sending test hand data to {UDP_IP}:{UDP_PORT}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            # Generate and send left hand data
            hand_data = generate_hand_data("Left")
            message = json.dumps(hand_data).encode('utf-8')
            sock.sendto(message, (UDP_IP, UDP_PORT))
            
            # Small delay to avoid flooding
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nStopped sending data")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
