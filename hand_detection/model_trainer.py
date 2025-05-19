"""
Hand Tracking Model Trainer
Trains a machine learning model on collected hand landmark data.
"""

import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

class HandModelTrainer:
    def __init__(self, data_dir="collected_data", model_dir="trained_models"):
        """
        Initialize the hand model trainer
        
        Args:
            data_dir: Directory containing collected data
            model_dir: Directory to save trained models
        """
        self.data_dir = data_dir
        self.model_dir = model_dir
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize data structures
        self.X = []  # Features (hand landmarks)
        self.y = []  # Labels (gestures)
        self.label_encoder = LabelEncoder()
        self.model = None
    
    def load_data(self):
        """
        Load collected data from JSON files
        """
        print("Loading data...")
        
        # Get all JSON files in the data directory
        json_files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
        
        if not json_files:
            print(f"No data files found in {self.data_dir}")
            return False
        
        # Process each JSON file
        for json_file in json_files:
            file_path = os.path.join(self.data_dir, json_file)
            print(f"Processing {file_path}")
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract features and labels from each sample
            for sample in data:
                gesture = sample['gesture']
                landmarks = sample['landmarks']
                
                # Convert landmarks to flat feature vector
                # We'll use x, y, z coordinates of all 21 landmarks
                features = []
                for lm in landmarks:
                    features.extend(lm[1:])  # Skip the ID, only use x, y, z
                
                # Add to dataset
                self.X.append(features)
                self.y.append(gesture)
        
        # Convert to numpy arrays
        self.X = np.array(self.X, dtype=np.float32)
        
        # Normalize features
        self.X = self.normalize_features(self.X)
        
        # Encode labels
        self.y = self.label_encoder.fit_transform(self.y)
        
        print(f"Loaded {len(self.X)} samples with {len(np.unique(self.y))} gesture classes")
        return True
    
    def normalize_features(self, features):
        """
        Normalize features to range [0, 1]
        
        Args:
            features: Feature array
            
        Returns:
            normalized_features: Normalized feature array
        """
        # Find min and max values for each feature
        min_vals = np.min(features, axis=0)
        max_vals = np.max(features, axis=0)
        
        # Avoid division by zero
        range_vals = max_vals - min_vals
        range_vals[range_vals == 0] = 1
        
        # Normalize
        normalized_features = (features - min_vals) / range_vals
        
        return normalized_features
    
    def build_model(self, input_shape, num_classes):
        """
        Build a neural network model for hand gesture classification
        
        Args:
            input_shape: Shape of input features
            num_classes: Number of gesture classes
            
        Returns:
            model: Compiled Keras model
        """
        model = models.Sequential([
            layers.Dense(128, activation='relu', input_shape=(input_shape,)),
            layers.Dropout(0.3),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(32, activation='relu'),
            layers.Dense(num_classes, activation='softmax')
        ])
        
        # Compile model
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def train_model(self, epochs=50, batch_size=32, validation_split=0.2):
        """
        Train the model on the loaded data
        
        Args:
            epochs: Number of training epochs
            batch_size: Batch size for training
            validation_split: Fraction of data to use for validation
            
        Returns:
            history: Training history
        """
        if len(self.X) == 0:
            print("No data loaded. Call load_data() first.")
            return None
        
        # Split data into training and validation sets
        X_train, X_val, y_train, y_val = train_test_split(
            self.X, self.y, test_size=validation_split, random_state=42, stratify=self.y
        )
        
        # Build model
        input_shape = self.X.shape[1]
        num_classes = len(np.unique(self.y))
        self.model = self.build_model(input_shape, num_classes)
        
        # Print model summary
        self.model.summary()
        
        # Train model
        print(f"Training model with {len(X_train)} samples...")
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_val, y_val),
            verbose=1
        )
        
        # Evaluate model
        val_loss, val_acc = self.model.evaluate(X_val, y_val, verbose=0)
        print(f"Validation accuracy: {val_acc:.4f}")
        
        return history
    
    def save_model(self, model_name=None, export_path=None):
        """
        Save the trained model in Keras format
        
        Args:
            model_name: Name for the saved model
            export_path: Path to export the model files
        """
        if self.model is None:
            print("No model to save. Train a model first.")
            return
        
        # Generate model name if not provided
        if model_name is None:
            model_name = f"hand_gesture_model_{len(np.unique(self.y))}_classes"
        
        # Create export path if not provided
        if export_path is None:
            export_path = os.path.join(self.model_dir, "export")
            os.makedirs(export_path, exist_ok=True)
        
        # Save model in Keras .h5 format
        model_h5_path = os.path.join(export_path, f"{model_name}.h5")
        self.model.save(model_h5_path)
        
        # Save label encoder classes
        classes_path = os.path.join(export_path, f"{model_name}_classes.npy")
        np.save(classes_path, self.label_encoder.classes_)
        
        # Save model architecture as JSON
        model_json_path = os.path.join(export_path, f"{model_name}_architecture.json")
        with open(model_json_path, "w") as json_file:
            json_file.write(self.model.to_json())
        
        print(f"Model saved to {model_h5_path}")
        print(f"Model architecture saved to {model_json_path}")
        print(f"Classes saved to {classes_path}")
        print(f"Export path: {export_path}")
    
    def plot_training_history(self, history):
        """
        Plot training and validation accuracy/loss
        
        Args:
            history: Training history from model.fit()
        """
        # Plot accuracy
        plt.figure(figsize=(12, 4))
        
        plt.subplot(1, 2, 1)
        plt.plot(history.history['accuracy'])
        plt.plot(history.history['val_accuracy'])
        plt.title('Model Accuracy')
        plt.ylabel('Accuracy')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Validation'], loc='upper left')
        
        # Plot loss
        plt.subplot(1, 2, 2)
        plt.plot(history.history['loss'])
        plt.plot(history.history['val_loss'])
        plt.title('Model Loss')
        plt.ylabel('Loss')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Validation'], loc='upper left')
        
        plt.tight_layout()
        
        # Save the plot
        plt.savefig(os.path.join(self.model_dir, 'training_history.png'))
        plt.show()


def main():
    """
    Main function to run the model trainer
    """
    trainer = HandModelTrainer()
    
    # Load data
    if trainer.load_data():
        # Train model
        history = trainer.train_model(epochs=50)
        
        if history:
            # Save model
            trainer.save_model()
            
            # Plot training history
            trainer.plot_training_history(history)
    
    print("Model training complete!")


if __name__ == "__main__":
    main()
