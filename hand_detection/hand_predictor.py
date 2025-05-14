"""
Hand Gesture Predictor
Uses the trained model to predict hand gestures in real-time.
"""

import cv2
import numpy as np
import tensorflow as tf
import os
from hand_tracker import HandTracker

class HandGesturePredictor:
    def __init__(self, model_dir="trained_models", model_name=None):
        """
        Initialize the hand gesture predictor
        
        Args:
            model_dir: Directory containing trained models
            model_name: Name of the model to load (if None, will use the latest model)
        """
        self.model_dir = model_dir
        
        # Initialize hand tracker
        self.tracker = HandTracker(detection_confidence=0.7, tracking_confidence=0.7)
        
        # Load model
        self.model, self.classes = self.load_model(model_name)
    
    def load_model(self, model_name=None):
        """
        Load the trained model and class labels
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            model: Loaded TensorFlow model
            classes: Class labels
        """
        # Find the latest model if model_name is not provided
        if model_name is None:
            model_dirs = [d for d in os.listdir(self.model_dir) 
                         if os.path.isdir(os.path.join(self.model_dir, d)) and 
                         d.startswith("hand_gesture_model")]
            
            if not model_dirs:
                raise FileNotFoundError(f"No models found in {self.model_dir}")
            
            # Sort by modification time (newest first)
            model_dirs.sort(key=lambda d: os.path.getmtime(os.path.join(self.model_dir, d)), reverse=True)
            model_name = model_dirs[0]
        
        # Load model
        model_path = os.path.join(self.model_dir, model_name)
        model = tf.keras.models.load_model(model_path)
        
        # Load class labels
        classes_path = os.path.join(self.model_dir, f"{model_name}_classes.npy")
        classes = np.load(classes_path, allow_pickle=True)
        
        print(f"Loaded model from {model_path}")
        print(f"Available gesture classes: {classes}")
        
        return model, classes
    
    def preprocess_landmarks(self, landmarks):
        """
        Preprocess landmarks for model input
        
        Args:
            landmarks: List of landmarks [id, x, y, z]
            
        Returns:
            features: Preprocessed feature vector
        """
        # Extract x, y, z coordinates
        features = []
        for lm in landmarks:
            features.extend(lm[1:])  # Skip the ID, only use x, y, z
        
        # Convert to numpy array
        features = np.array(features, dtype=np.float32)
        
        # Normalize features (simple min-max scaling based on typical hand values)
        # Note: In a real application, you should use the same normalization as during training
        features = features / 640.0  # Approximate normalization
        
        # Reshape for model input
        features = features.reshape(1, -1)
        
        return features
    
    def predict_gesture(self, landmarks):
        """
        Predict the gesture from hand landmarks
        
        Args:
            landmarks: List of landmarks [id, x, y, z]
            
        Returns:
            gesture: Predicted gesture
            confidence: Prediction confidence
        """
        if not landmarks or self.model is None:
            return "Unknown", 0.0
        
        # Preprocess landmarks
        features = self.preprocess_landmarks(landmarks)
        
        # Make prediction
        predictions = self.model.predict(features, verbose=0)[0]
        
        # Get the predicted class and confidence
        predicted_class_idx = np.argmax(predictions)
        confidence = predictions[predicted_class_idx]
        
        # Get the class name
        gesture = self.classes[predicted_class_idx]
        
        return gesture, confidence
    
    def run_prediction(self):
        """
        Run real-time hand gesture prediction using webcam
        """
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        
        print("Starting real-time hand gesture prediction...")
        print("Press 'q' to quit")
        
        while True:
            # Read frame from webcam
            success, img = cap.read()
            if not success:
                print("Failed to read from webcam")
                break
            
            # Find hands and get landmarks
            img, results = self.tracker.find_hands(img)
            landmarks = self.tracker.find_positions(img)
            
            # If hand is detected, predict gesture
            if landmarks:
                hand_type = self.tracker.get_hand_type()
                gesture, confidence = self.predict_gesture(landmarks)
                
                # Display prediction
                cv2.putText(img, f"Hand: {hand_type}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2)
                cv2.putText(img, f"Gesture: {gesture}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2)
                cv2.putText(img, f"Confidence: {confidence:.2f}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2)
                
                # Highlight the wrist position (for 3D visualization)
                wrist_x, wrist_y = landmarks[0][1], landmarks[0][2]
                wrist_z = landmarks[0][3]
                cv2.circle(img, (wrist_x, wrist_y), 10, (0, 0, 255), cv2.FILLED)
                cv2.putText(img, f"Depth: {wrist_z:.3f}", (wrist_x + 10, wrist_y), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Show the image
            cv2.imshow("Hand Gesture Prediction", img)
            
            # Exit on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Release resources
        cap.release()
        cv2.destroyAllWindows()
    
    def export_for_unity(self, output_file="hand_model_unity.tflite"):
        """
        Export the model in TFLite format for Unity
        
        Args:
            output_file: Path to save the TFLite model
        """
        if self.model is None:
            print("No model loaded")
            return
        
        # Convert model to TFLite format
        converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
        tflite_model = converter.convert()
        
        # Save the model
        with open(os.path.join(self.model_dir, output_file), 'wb') as f:
            f.write(tflite_model)
        
        # Save class labels in a text format for Unity
        with open(os.path.join(self.model_dir, "gesture_classes.txt"), 'w') as f:
            for cls in self.classes:
                f.write(f"{cls}\n")
        
        print(f"Model exported for Unity to {os.path.join(self.model_dir, output_file)}")
        print(f"Classes exported to {os.path.join(self.model_dir, 'gesture_classes.txt')}")


def main():
    """
    Main function to run the hand gesture predictor
    """
    try:
        predictor = HandGesturePredictor()
        
        # Export model for Unity
        predictor.export_for_unity()
        
        # Run real-time prediction
        predictor.run_prediction()
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please train a model first using model_trainer.py")


if __name__ == "__main__":
    main()
