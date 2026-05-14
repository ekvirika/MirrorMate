"""
Hand Tracking Module using MediaPipe
This module provides real-time hand tracking capabilities with 3D landmarks.
"""

import cv2
import mediapipe as mp
import numpy as np
import time

class HandTracker:
    def __init__(self, static_mode=False, max_hands=2, detection_confidence=0.5, tracking_confidence=0.5):
        """
        Initialize the hand tracker
        
        Args:
            static_mode: If True, detection runs on every frame (slower but more accurate)
            max_hands: Maximum number of hands to detect
            detection_confidence: Minimum confidence for hand detection
            tracking_confidence: Minimum confidence for landmark tracking
        """
        self.static_mode = static_mode
        self.max_hands = max_hands
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.static_mode,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Define the 21 hand landmarks
        self.landmark_names = [
            'WRIST',
            'THUMB_CMC', 'THUMB_MCP', 'THUMB_IP', 'THUMB_TIP',
            'INDEX_FINGER_MCP', 'INDEX_FINGER_PIP', 'INDEX_FINGER_DIP', 'INDEX_FINGER_TIP',
            'MIDDLE_FINGER_MCP', 'MIDDLE_FINGER_PIP', 'MIDDLE_FINGER_DIP', 'MIDDLE_FINGER_TIP',
            'RING_FINGER_MCP', 'RING_FINGER_PIP', 'RING_FINGER_DIP', 'RING_FINGER_TIP',
            'PINKY_MCP', 'PINKY_PIP', 'PINKY_DIP', 'PINKY_TIP'
        ]
    
    def find_hands(self, img, draw=True):
        """
        Find hands in an image and optionally draw landmarks
        
        Args:
            img: Input image (BGR format)
            draw: Whether to draw landmarks on the image
            
        Returns:
            img: Processed image with landmarks drawn (if draw=True)
            results: MediaPipe hand detection results
        """
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Process the image
        self.results = self.hands.process(img_rgb)
        
        # Draw landmarks if hands are detected and draw=True
        if self.results.multi_hand_landmarks and draw:
            for hand_landmarks in self.results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    img, 
                    hand_landmarks, 
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
        
        return img, self.results
    
    def find_positions(self, img, hand_no=0):
        """
        Find the 3D positions of hand landmarks
        
        Args:
            img: Input image
            hand_no: Which hand to get positions for (if multiple hands detected)
            
        Returns:
            landmarks_3d: List of 3D landmarks [id, x, y, z]
        """
        img_height, img_width, _ = img.shape
        landmarks_3d = []
        
        if self.results.multi_hand_landmarks:
            if hand_no < len(self.results.multi_hand_landmarks):
                hand = self.results.multi_hand_landmarks[hand_no]
                
                for id, lm in enumerate(hand.landmark):
                    # Convert normalized coordinates to pixel coordinates
                    x, y = int(lm.x * img_width), int(lm.y * img_height)
                    # Include the z coordinate (depth)
                    z = lm.z
                    
                    landmarks_3d.append([id, x, y, z])
        
        return landmarks_3d
    
    def get_hand_type(self, hand_no=0):
        """
        Determine if the detected hand is left or right
        
        Args:
            hand_no: Which hand to check (if multiple hands detected)
            
        Returns:
            hand_type: "Left" or "Right"
        """
        hand_type = "Unknown"
        
        if self.results.multi_handedness:
            if hand_no < len(self.results.multi_handedness):
                hand_type = self.results.multi_handedness[hand_no].classification[0].label
        
        return hand_type
    
    def get_landmark_name(self, landmark_id):
        """
        Get the name of a landmark by its ID
        
        Args:
            landmark_id: ID of the landmark (0-20)
            
        Returns:
            name: Name of the landmark
        """
        if 0 <= landmark_id < len(self.landmark_names):
            return self.landmark_names[landmark_id]
        return "Unknown"

    def process_frame(self, img):
        """
        Process a frame and return hand tracking data in a format suitable for Unity
        
        Args:
            img: Input image (BGR format)
            
        Returns:
            List of dictionaries containing hand tracking data
        """
        img, _ = self.find_hands(img, draw=False)
        hands_data = []
        
        if self.results.multi_hand_landmarks:
            for hand_no in range(len(self.results.multi_hand_landmarks)):
                landmarks = self.find_positions(img, hand_no)
                hand_type = self.get_hand_type(hand_no)
                
                landmarks_data = []
                for lm in landmarks:
                    landmark_id = lm[0]
                    landmarks_data.append({
                        "id": landmark_id,
                        "name": self.get_landmark_name(landmark_id),
                        "position": [lm[1], lm[2], lm[3]]  # x, y, z coordinates
                    })
                
                hand_data = {
                    "hand_type": hand_type,
                    "landmarks": landmarks_data
                }
                hands_data.append(hand_data)
        
        return hands_data


def calculate_finger_angles(landmarks):
    """
    Calculate angles between finger segments
    """
    angles = {}
    
    # Define finger bases (MCP joints)
    finger_bases = {
        'thumb': 1,    # THUMB_CMC
        'index': 5,    # INDEX_FINGER_MCP
        'middle': 9,   # MIDDLE_FINGER_MCP
        'ring': 13,    # RING_FINGER_MCP
        'pinky': 17    # PINKY_MCP
    }
    
    for finger, base_id in finger_bases.items():
        if len(landmarks) >= base_id + 3:  # Ensure we have all points for the finger
            # Get points for angle calculation
            p1 = np.array([landmarks[base_id][1], landmarks[base_id][2]])      # MCP
            p2 = np.array([landmarks[base_id + 1][1], landmarks[base_id + 1][2]])  # PIP
            p3 = np.array([landmarks[base_id + 2][1], landmarks[base_id + 2][2]])  # DIP
            
            # Calculate vectors
            v1 = p2 - p1
            v2 = p3 - p2
            
            # Calculate angle
            angle = np.degrees(np.arctan2(np.cross(v1, v2), np.dot(v1, v2)))
            angles[finger] = abs(angle)
    
    return angles

def detect_gesture(angles):
    """
    Detect hand gesture based on finger angles
    """
    if not angles:
        return "Unknown"
    
    # Example gesture detection rules (can be refined)
    if all(angle < 30 for angle in angles.values()):
        return "Open Hand"
    elif all(angle > 60 for angle in angles.values()):
        return "Fist"
    elif angles.get('index', 90) < 30 and all(angles.get(f, 90) > 60 for f in ['middle', 'ring', 'pinky']):
        return "Pointing"
    return "Other"

def main():
    """
    Enhanced demo function to test the hand tracker with gesture recognition
    """
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    # Initialize hand tracker with higher confidence thresholds for stability
    tracker = HandTracker(detection_confidence=0.7, tracking_confidence=0.7)
    
    # FPS calculation variables
    prev_time = 0
    curr_time = 0
    
    # Create named window and set it to a reasonable size
    cv2.namedWindow("Hand Tracking", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Hand Tracking", 1280, 720)
    
    while True:
        # Read frame from webcam
        success, img = cap.read()
        if not success:
            print("Failed to read from webcam")
            break
        
        # Find hands and get landmarks
        img, results = tracker.find_hands(img)
        landmarks = tracker.find_positions(img)
        
        # Calculate FPS
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
        prev_time = curr_time
        
        # Create a semi-transparent overlay for text
        overlay = img.copy()
        
        # Display information if hands are detected
        if landmarks:
            # Get hand information
            hand_type = tracker.get_hand_type()
            wrist_z = landmarks[0][3]
            
            # Calculate finger angles and detect gesture
            angles = calculate_finger_angles(landmarks)
            gesture = detect_gesture(angles)
            
            # Draw finger angles
            y_pos = 70
            cv2.putText(overlay, f"Hand: {hand_type}", (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            y_pos += 40
            
            cv2.putText(overlay, f"Gesture: {gesture}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            y_pos += 40
            
            cv2.putText(overlay, f"Depth: {wrist_z:.3f}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            y_pos += 40
            
            # Display finger angles
            for finger, angle in angles.items():
                cv2.putText(overlay, f"{finger}: {angle:.1f}°", (10, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                y_pos += 30
        
        # Always display FPS
        cv2.putText(overlay, f"FPS: {int(fps)}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Blend the overlay with the original image
        alpha = 0.7
        img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
        
        # Show the image
        cv2.imshow("Hand Tracking", img)
        
        # Exit on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
