"""
Unity Hand Tracking Exporter
Exports hand tracking data to Unity via UDP for real-time visualization.
"""

import cv2
import numpy as np
import socket
import json
import time
import threading
from hand_tracker import HandTracker

class UnityHandExporter:
    def __init__(self, unity_ip="127.0.0.1", unity_port=5065):
        """
        Initialize the Unity hand tracking exporter
        
        Args:
            unity_ip: IP address of the Unity application
            unity_port: Port number of the Unity application
        """
        self.unity_ip = unity_ip
        self.unity_port = unity_port
        
        # Initialize hand tracker with support for 2 hands
        self.tracker = HandTracker(max_hands=2, detection_confidence=0.7, tracking_confidence=0.7)
        
        # Initialize UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Tracking state
        self.is_tracking = False
        self.tracking_thread = None
        
        # Additional landmarks for forearm (will be calculated based on wrist and elbow positions)
        self.forearm_landmarks = [
            "ELBOW",
            "FOREARM_MID",  # Midpoint between wrist and elbow
            "FOREARM_QUARTER",  # Quarter point from wrist to elbow
            "FOREARM_THREE_QUARTER"  # Three-quarter point from wrist to elbow
        ]
    
    def start_tracking(self):
        """
        Start hand tracking and exporting to Unity
        """
        if self.is_tracking:
            print("Tracking is already running")
            return
        
        self.is_tracking = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        print(f"Started tracking and exporting to Unity at {self.unity_ip}:{self.unity_port}")
    
    def stop_tracking(self):
        """
        Stop hand tracking
        """
        self.is_tracking = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=1.0)
            self.tracking_thread = None
        
        print("Stopped tracking")
    
    def _tracking_loop(self):
        """
        Main tracking loop (runs in a separate thread)
        """
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        
        # Check if camera opened successfully
        if not cap.isOpened():
            print("Error: Could not open webcam. Please check your camera connection.")
            self.is_tracking = False
            return
        
        print(f"Camera initialized successfully. Sending data to Unity at {self.unity_ip}:{self.unity_port}")
        print("Place your hands in front of the camera to begin tracking.")
        
        frame_count = 0
        while self.is_tracking:
            # Read frame from webcam
            success, img = cap.read()
            if not success:
                print("Failed to read from webcam")
                time.sleep(0.1)
                continue
            
            # Find hands and get landmarks
            img, results = self.tracker.find_hands(img)
            
            # Check if hands are detected
            if results.multi_hand_landmarks:
                frame_count += 1
                hands_data = []
                
                # Process each detected hand
                for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Get hand type (left or right)
                    if hand_idx < len(results.multi_handedness):
                        hand_type = results.multi_handedness[hand_idx].classification[0].label
                    else:
                        hand_type = "Unknown"
                    
                    # Get landmarks for this hand
                    landmarks = self.tracker.find_positions(img, hand_no=hand_idx)
                    
                    if landmarks:
                        # Add forearm landmarks if possible (estimating elbow position)
                        landmarks_with_forearm = self._add_forearm_landmarks(landmarks, img)
                        
                        # Add this hand's data to the list
                        hands_data.append({
                            "hand_type": hand_type,
                            "landmarks": landmarks_with_forearm
                        })
                        
                        # Draw hand type on image
                        wrist_x, wrist_y = landmarks[0][1], landmarks[0][2]
                        cv2.putText(img, f"{hand_type} Hand", (wrist_x, wrist_y - 15), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                
                # Send all hands data to Unity
                if hands_data:
                    self._send_to_unity_multi(hands_data)
                    
                    # Display status on image
                    cv2.putText(img, f"Sending to Unity: {len(hands_data)} hands", (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(img, f"Target: {self.unity_ip}:{self.unity_port}", (10, 70), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(img, f"Frames sent: {frame_count}", (10, 110), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                # Display warning if no hand detected
                cv2.putText(img, "No hands detected", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(img, f"Target: {self.unity_ip}:{self.unity_port}", (10, 70), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            
            # Show the image
            cv2.imshow("Unity Hand Exporter", img)
            
            # Exit on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.is_tracking = False
        
        # Release resources
        cap.release()
        cv2.destroyAllWindows()
        print("Hand tracking stopped.")
    
    def _add_forearm_landmarks(self, landmarks, img):
        """
        Add forearm landmarks based on wrist position and estimated elbow position
        
        Args:
            landmarks: List of hand landmarks [id, x, y, z]
            img: Image for reference dimensions
            
        Returns:
            landmarks_with_forearm: Extended landmarks list including forearm
        """
        # Copy original landmarks
        landmarks_with_forearm = landmarks.copy()
        
        # Get wrist position (landmark 0)
        if len(landmarks) > 0:
            wrist_id, wrist_x, wrist_y, wrist_z = landmarks[0]
            
            # Get image dimensions for scaling
            img_height, img_width, _ = img.shape
            
            # We'll use multiple reference points to make a more robust forearm estimation
            reference_points = []
            
            # Get middle finger MCP (landmark 9)
            middle_finger_mcp = None
            for lm in landmarks:
                if lm[0] == 9:  # Middle finger MCP
                    middle_finger_mcp = lm
                    reference_points.append(lm)
                    break
            
            # Get index finger MCP (landmark 5)
            index_finger_mcp = None
            for lm in landmarks:
                if lm[0] == 5:  # Index finger MCP
                    index_finger_mcp = lm
                    reference_points.append(lm)
                    break
            
            # Get pinky MCP (landmark 17)
            pinky_mcp = None
            for lm in landmarks:
                if lm[0] == 17:  # Pinky MCP
                    pinky_mcp = lm
                    reference_points.append(lm)
                    break
            
            # Calculate average direction vector from MCPs to wrist
            avg_dx, avg_dy = 0, 0
            count = 0
            
            for point in reference_points:
                if point:
                    dx = wrist_x - point[1]
                    dy = wrist_y - point[2]
                    avg_dx += dx
                    avg_dy += dy
                    count += 1
            
            if count > 0:
                avg_dx /= count
                avg_dy /= count
                
                # Normalize and scale to estimate elbow position
                magnitude = (avg_dx**2 + avg_dy**2)**0.5
                if magnitude > 0:
                    # Determine the forearm length based on hand orientation
                    # If hand is horizontal, make forearm longer
                    hand_orientation = abs(avg_dy / (avg_dx if avg_dx != 0 else 0.001))
                    forearm_length_factor = 0.5 if hand_orientation > 1 else 0.7
                    
                    # Scale the vector
                    norm_dx = avg_dx / magnitude
                    norm_dy = avg_dy / magnitude
                    scaled_dx = norm_dx * img_width * forearm_length_factor
                    scaled_dy = norm_dy * img_height * forearm_length_factor
                    
                    # Estimated elbow position
                    elbow_x = int(wrist_x + scaled_dx)
                    elbow_y = int(wrist_y + scaled_dy)
                    
                    # Estimate depth change for elbow (usually closer to camera than wrist)
                    # This creates a more natural forearm angle
                    depth_change = 0.1  # Elbow is slightly closer to camera
                    elbow_z = wrist_z - depth_change
                    
                    # Add elbow landmark (ID 21)
                    landmarks_with_forearm.append([21, elbow_x, elbow_y, elbow_z])
                    
                    # Add intermediate forearm landmarks
                    # Forearm midpoint (ID 22)
                    mid_x = int((wrist_x + elbow_x) / 2)
                    mid_y = int((wrist_y + elbow_y) / 2)
                    mid_z = wrist_z - depth_change/2
                    landmarks_with_forearm.append([22, mid_x, mid_y, mid_z])
                    
                    # Quarter point from wrist to elbow (ID 23)
                    quarter_x = int(wrist_x + scaled_dx * 0.25)
                    quarter_y = int(wrist_y + scaled_dy * 0.25)
                    quarter_z = wrist_z - depth_change/4
                    landmarks_with_forearm.append([23, quarter_x, quarter_y, quarter_z])
                    
                    # Three-quarter point from wrist to elbow (ID 24)
                    three_quarter_x = int(wrist_x + scaled_dx * 0.75)
                    three_quarter_y = int(wrist_y + scaled_dy * 0.75)
                    three_quarter_z = wrist_z - depth_change*3/4
                    landmarks_with_forearm.append([24, three_quarter_x, three_quarter_y, three_quarter_z])
                    
                    # Draw forearm on the image for debugging
                    cv2.line(img, (wrist_x, wrist_y), (elbow_x, elbow_y), (0, 255, 0), 3)
                    cv2.circle(img, (elbow_x, elbow_y), 8, (0, 255, 0), cv2.FILLED)
                    cv2.putText(img, "Elbow", (elbow_x + 10, elbow_y), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return landmarks_with_forearm

    def _send_to_unity_multi(self, hands_data):
        """
        Send multiple hands tracking data to Unity
        
        Args:
            hands_data: List of hand data dictionaries, each containing hand_type and landmarks
        """
        # Create data packet
        data = {
            "timestamp": time.time(),
            "hands": hands_data
        }
        
        # Process each hand's landmarks
        for hand in data["hands"]:
            processed_landmarks = []
            for lm in hand["landmarks"]:
                lm_id = lm[0]
                x, y, z = lm[1], lm[2], lm[3]
                
                # Get landmark name (handle forearm landmarks specially)
                if lm_id < 21:
                    name = self.tracker.get_landmark_name(lm_id)
                elif lm_id == 21:
                    name = "ELBOW"
                elif lm_id == 22:
                    name = "FOREARM_MID"
                elif lm_id == 23:
                    name = "FOREARM_QUARTER"
                elif lm_id == 24:
                    name = "FOREARM_THREE_QUARTER"
                else:
                    name = f"UNKNOWN_{lm_id}"
                
                # Add landmark to processed list
                processed_landmarks.append({
                    "id": lm_id,
                    "name": name,
                    "position": [x, y, z]
                })
            
            # Replace the original landmarks with processed ones
            hand["landmarks"] = processed_landmarks
        
        # Convert to JSON
        json_data = json.dumps(data)
        
        # Send via UDP
        try:
            self.socket.sendto(json_data.encode(), (self.unity_ip, self.unity_port))
            # Print confirmation every 30 frames to avoid console spam
            if int(time.time() * 10) % 30 == 0:
                total_landmarks = sum(len(hand["landmarks"]) for hand in data["hands"])
                print(f"Data sent to Unity at {self.unity_ip}:{self.unity_port} - {len(data['hands'])} hands, {total_landmarks} total landmarks")
        except Exception as e:
            print(f"Error sending data to Unity: {e}")
            
    def _send_to_unity(self, landmarks, hand_type):
        """
        Send hand tracking data to Unity (legacy method, use _send_to_unity_multi instead)
        
        Args:
            landmarks: List of landmarks [id, x, y, z]
            hand_type: "Left" or "Right"
        """
        # Create data packet
        data = {
            "timestamp": time.time(),
            "hand_type": hand_type,
            "landmarks": []
        }
        
        # Add landmarks
        for lm in landmarks:
            lm_id = lm[0]
            x, y, z = lm[1], lm[2], lm[3]
            
            # Add landmark to data packet
            data["landmarks"].append({
                "id": lm_id,
                "name": self.tracker.get_landmark_name(lm_id),
                "position": [x, y, z]
            })
        
        # Convert to JSON
        json_data = json.dumps(data)
        
        # Send via UDP
        try:
            self.socket.sendto(json_data.encode(), (self.unity_ip, self.unity_port))
            # Print confirmation every 30 frames to avoid console spam
            if int(time.time() * 10) % 30 == 0:
                print(f"Data sent to Unity at {self.unity_ip}:{self.unity_port} - {len(data['landmarks'])} landmarks")
        except Exception as e:
            print(f"Error sending data to Unity: {e}")
    
    def run_interactive(self):
        """
        Run the exporter in interactive mode
        """
        print("Unity Hand Tracking Exporter")
        print(f"Target: {self.unity_ip}:{self.unity_port}")
        print("Commands:")
        print("  start - Start tracking and exporting")
        print("  stop  - Stop tracking")
        print("  ip    - Change Unity IP address")
        print("  port  - Change Unity port")
        print("  exit  - Exit the program")
        
        while True:
            cmd = input("> ").strip().lower()
            
            if cmd == "start":
                self.start_tracking()
            elif cmd == "stop":
                self.stop_tracking()
            elif cmd == "ip":
                new_ip = input("Enter new Unity IP address: ").strip()
                self.unity_ip = new_ip
                print(f"Unity IP set to {self.unity_ip}")
            elif cmd == "port":
                try:
                    new_port = int(input("Enter new Unity port: ").strip())
                    self.unity_port = new_port
                    print(f"Unity port set to {self.unity_port}")
                except ValueError:
                    print("Invalid port number")
            elif cmd == "exit":
                self.stop_tracking()
                break
            else:
                print("Unknown command")


def main():
    """
    Main function to run the Unity hand exporter
    """
    # Default values
    unity_ip = "127.0.0.1"
    unity_port = 5065
    
    # Check if command line arguments are provided
    import sys
    if len(sys.argv) > 1:
        unity_ip = sys.argv[1]
    if len(sys.argv) > 2:
        unity_port = int(sys.argv[2])
    
    print(f"\nMirror Mate - Unity Hand Exporter")
    print(f"=================================")
    print(f"Target Unity application: {unity_ip}:{unity_port}")
    print(f"Make sure your Unity project is running with the HandTrackingReceiver script")
    print(f"listening on the same port ({unity_port})\n")
    
    exporter = UnityHandExporter(unity_ip=unity_ip, unity_port=unity_port)
    
    # Ask if the user wants to start tracking immediately or use interactive mode
    choice = input("Start tracking immediately? (y/n): ").strip().lower()
    if choice == 'y':
        print("Starting hand tracking. Press 'q' in the video window to stop.")
        exporter.start_tracking()
        # Wait for the tracking thread to finish
        if exporter.tracking_thread:
            exporter.tracking_thread.join()
    else:
        exporter.run_interactive()


if __name__ == "__main__":
    main()
