"""
Hand to Servo Angle Mapper for InMoov Hand
Maps MediaPipe hand tracking coordinates to servo angles for the InMoov robotic hand.
"""

import numpy as np
from typing import List, Dict, Tuple

class HandToServoMapper:
    def __init__(self):
        # Define servo angle limits
        self.SERVO_MIN = 0
        self.SERVO_MAX = 180
        self.WRIST_CENTER = 90
        
        # Define finger joint indices from MediaPipe hand landmarks
        # Each finger has MCP (0), PIP (1), and DIP (2) joints
        self.FINGER_LANDMARKS = {
            'thumb': [1, 2, 3, 4],       # Thumb landmarks
            'index': [5, 6, 7, 8],       # Index finger landmarks
            'middle': [9, 10, 11, 12],   # Middle finger landmarks
            'ring': [13, 14, 15, 16],    # Ring finger landmarks
            'pinky': [17, 18, 19, 20]    # Pinky landmarks
        }
        
        # Wrist landmarks for angle calculation
        self.WRIST_LANDMARK = 0  # Wrist center point
    
    def calculate_finger_bend(self, landmarks: List[List[float]], finger: str) -> float:
        """
        Calculate how much a finger is bent (0.0 = straight, 1.0 = fully bent)
        
        Args:
            landmarks: List of [x, y, z] coordinates for each hand landmark
            finger: Name of the finger ('thumb', 'index', 'middle', 'ring', 'pinky')
            
        Returns:
            float: Bend value between 0.0 (straight) and 1.0 (fully bent)
        """
        if finger not in self.FINGER_LANDMARKS:
            raise ValueError(f"Unknown finger: {finger}")
            
        # Get the landmarks for this finger
        points = [landmarks[i] for i in self.FINGER_LANDMARKS[finger]]
        
        if not all(points):
            return 0.0
        
        # Calculate angles between finger segments
        angles = []
        for i in range(1, len(points)-1):
            v1 = np.array(points[i-1]) - np.array(points[i])
            v2 = np.array(points[i+1]) - np.array(points[i])
            
            # Normalize vectors
            v1 = v1 / np.linalg.norm(v1)
            v2 = v2 / np.linalg.norm(v2)
            
            # Calculate angle
            angle = np.arccos(np.clip(np.dot(v1, v2), -1.0, 1.0))
            angles.append(angle)
        
        # Average the angles and normalize to 0-1 range
        avg_angle = np.mean(angles)
        bend_value = avg_angle / np.pi
        
        # Adjust the range to make it more sensitive
        bend_value = np.clip(bend_value * 1.5, 0.0, 1.0)
        
        return bend_value
    
    def calculate_wrist_angle(self, landmarks: List[List[float]]) -> float:
        """
        Calculate the wrist angle (-1.0 = bent left, 0.0 = center, 1.0 = bent right)
        
        Args:
            landmarks: List of [x, y, z] coordinates for each hand landmark
            
        Returns:
            float: Angle value between -1.0 (left) and 1.0 (right)
        """
        # Get wrist and middle finger MCP landmarks
        wrist = landmarks[self.WRIST_LANDMARK]
        middle_mcp = landmarks[self.FINGER_LANDMARKS['middle'][0]]
        
        if not wrist or not middle_mcp:
            return 0.0
        
        # Calculate angle from vertical
        dx = middle_mcp[0] - wrist[0]
        dy = middle_mcp[1] - wrist[1]
        angle = np.arctan2(dx, dy)  # Using dx/dy for angle from vertical
        
        # Normalize to -1 to 1 range
        normalized_angle = angle / (np.pi/2)  # Divide by 90 degrees
        return np.clip(normalized_angle, -1.0, 1.0)
    
    def map_to_servo_angles(self, landmarks: List[List[float]]) -> Dict[str, int]:
        """
        Map hand landmarks to servo angles for all fingers and wrist
        
        Args:
            landmarks: List of [x, y, z] coordinates for each hand landmark
            
        Returns:
            dict: Servo angles for each finger and wrist
        """
        servo_angles = {}
        
        # Map fingers (straight = 0°, bent = 180°)
        for finger in ['thumb', 'index', 'middle', 'ring', 'pinky']:
            bend = self.calculate_finger_bend(landmarks, finger)
            servo_angles[finger] = int(bend * self.SERVO_MAX)
        
        # Map wrist (center = 90°, left = 180°, right = 0°)
        wrist_angle = self.calculate_wrist_angle(landmarks)
        servo_angles['wrist'] = int(self.WRIST_CENTER + (wrist_angle * 90))
        
        # Ensure all angles are within valid range
        for key in servo_angles:
            servo_angles[key] = np.clip(servo_angles[key], self.SERVO_MIN, self.SERVO_MAX)
        
        return servo_angles


# Example usage
if __name__ == "__main__":
    mapper = HandToServoMapper()
    
    # Example landmarks (this would come from the hand tracker)
    # Format: [[x, y, z], [x, y, z], ...] for each landmark
    example_landmarks = [[0, 0, 0] for _ in range(21)]  # Initialize with zeros
    
    # Get servo angles
    servo_angles = mapper.map_to_servo_angles(example_landmarks)
    print("Mapped servo angles:", servo_angles)