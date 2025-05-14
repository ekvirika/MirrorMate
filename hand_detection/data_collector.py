"""
Hand Tracking Data Collector
Collects 3D hand landmark data for training a custom model.
"""

import cv2
import numpy as np
import os
import time
import json
from hand_tracker import HandTracker

class HandDataCollector:
    def __init__(self, output_dir="collected_data", max_samples=1000):
        """
        Initialize the hand data collector
        
        Args:
            output_dir: Directory to save collected data
            max_samples: Maximum number of samples to collect
        """
        self.output_dir = output_dir
        self.max_samples = max_samples
        self.sample_count = 0
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize hand tracker
        self.tracker = HandTracker(detection_confidence=0.7, tracking_confidence=0.7)
        
        # Data storage
        self.collected_data = []
    
    def collect_data(self, gesture_name, countdown=3):
        """
        Collect hand tracking data for a specific gesture
        
        Args:
            gesture_name: Name of the gesture to collect data for
            countdown: Countdown in seconds before starting collection
        """
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        
        # Countdown phase
        for i in range(countdown, 0, -1):
            success, img = cap.read()
            if not success:
                print("Failed to read from webcam")
                return
            
            # Display countdown
            cv2.putText(img, f"Starting in {i}...", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                        2, (0, 255, 0), 3)
            cv2.imshow("Data Collection", img)
            cv2.waitKey(1000)  # Wait 1 second
        
        # Collection phase
        start_time = time.time()
        collecting = True
        
        print(f"Collecting data for gesture: {gesture_name}")
        print(f"Press 'q' to stop collection")
        
        while collecting and self.sample_count < self.max_samples:
            # Read frame from webcam
            success, img = cap.read()
            if not success:
                print("Failed to read from webcam")
                break
            
            # Find hands and get landmarks
            img, results = self.tracker.find_hands(img)
            landmarks = self.tracker.find_positions(img)
            
            # If hand is detected, save the landmarks
            if landmarks:
                hand_type = self.tracker.get_hand_type()
                
                # Create data sample
                sample = {
                    "timestamp": time.time(),
                    "gesture": gesture_name,
                    "hand_type": hand_type,
                    "landmarks": landmarks
                }
                
                # Add to collected data
                self.collected_data.append(sample)
                self.sample_count += 1
                
                # Display collection progress
                cv2.putText(img, f"Collecting: {gesture_name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2)
                cv2.putText(img, f"Samples: {self.sample_count}/{self.max_samples}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2)
                cv2.putText(img, f"Hand: {hand_type}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2)
            else:
                # Display warning if no hand detected
                cv2.putText(img, "No hand detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 0, 255), 2)
            
            # Show the image
            cv2.imshow("Data Collection", img)
            
            # Exit on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                collecting = False
        
        # Release resources
        cap.release()
        cv2.destroyAllWindows()
        
        print(f"Collected {self.sample_count} samples for gesture: {gesture_name}")
    
    def save_data(self):
        """
        Save collected data to disk
        """
        if not self.collected_data:
            print("No data to save")
            return
        
        # Create filename with timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(self.output_dir, f"hand_data_{timestamp}.json")
        
        # Save data as JSON
        with open(filename, 'w') as f:
            json.dump(self.collected_data, f, indent=2)
        
        print(f"Saved {len(self.collected_data)} samples to {filename}")
        
        # Reset collection
        self.collected_data = []
        self.sample_count = 0


def main():
    """
    Main function to run the data collector
    """
    collector = HandDataCollector()
    
    # List of gestures to collect data for
    gestures = [
        "open_hand",
        "closed_fist",
        "pointing",
        "peace_sign",
        "thumbs_up"
    ]
    
    # Collect data for each gesture
    for gesture in gestures:
        input(f"Press Enter to start collecting data for '{gesture}'...")
        collector.collect_data(gesture)
        collector.save_data()
    
    print("Data collection complete!")


if __name__ == "__main__":
    main()
