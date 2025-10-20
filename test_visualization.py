import socket
import json
import time
import math

# Configuration
UDP_IP = "127.0.0.1"
UDP_PORT = 5065

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def generate_simple_hand():
    """Generate a simple, easy-to-see hand positioned in front of camera"""
    landmarks = []
    
    # Landmark names
    landmark_names = [
        "WRIST", "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
        "INDEX_FINGER_MCP", "INDEX_FINGER_PIP", "INDEX_FINGER_DIP", "INDEX_FINGER_TIP",
        "MIDDLE_FINGER_MCP", "MIDDLE_FINGER_PIP", "MIDDLE_FINGER_DIP", "MIDDLE_FINGER_TIP",
        "RING_FINGER_MCP", "RING_FINGER_PIP", "RING_FINGER_DIP", "RING_FINGER_TIP",
        "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP"
    ]
    
    # Create a simple vertical line of points (easy to see)
    for i in range(21):
        x = 0.0  # Centered horizontally
        y = i * 2.0  # Vertical spacing (2 units apart)
        z = 10.0  # 10 units in front of camera
        
        landmarks.append({
            "id": i,
            "name": landmark_names[i],
            "position": [x, y, z]
        })
    
    # Create hand data
    hand_data = {
        "hand_type": "Left",
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
    print("=" * 60)
    print("UNITY VISUALIZATION TEST")
    print("=" * 60)
    print(f"Sending to: {UDP_IP}:{UDP_PORT}")
    print("\nWhat you should see in Unity:")
    print("  - 21 cyan/blue spheres in a vertical line")
    print("  - Lines connecting them")
    print("  - Position: centered, 10 units in front of camera")
    print("\nCamera settings for best view:")
    print("  - Position: (0, 10, 0)")
    print("  - Rotation: (0, 0, 0)")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)
    
    packet_count = 0
    
    try:
        while True:
            # Generate and send data
            hand_data = generate_simple_hand()
            message = json.dumps(hand_data).encode('utf-8')
            sock.sendto(message, (UDP_IP, UDP_PORT))
            
            packet_count += 1
            if packet_count % 100 == 0:
                print(f"Sent {packet_count} packets...")
            
            time.sleep(0.05)  # 20 FPS
            
    except KeyboardInterrupt:
        print(f"\n\nStopped. Total packets sent: {packet_count}")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
