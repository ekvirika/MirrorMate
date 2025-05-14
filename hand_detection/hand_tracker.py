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


def main():
    """
    Demo function to test the hand tracker
    """
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    # Initialize hand tracker
    tracker = HandTracker()
    
    # FPS calculation variables
    prev_time = 0
    curr_time = 0
    
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
        
        # Display FPS
        cv2.putText(img, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (0, 255, 0), 2)
        
        # Display hand type if detected
        if landmarks:
            hand_type = tracker.get_hand_type()
            cv2.putText(img, f"Hand: {hand_type}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                        1, (0, 255, 0), 2)
            
            # Display the z-coordinate (depth) of the wrist
            wrist_z = landmarks[0][3]
            cv2.putText(img, f"Depth: {wrist_z:.3f}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 
                        1, (0, 255, 0), 2)
        
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
