"""
InMoov Hand Controller
Connects hand tracking to servo control for the InMoov robotic hand.
"""

import sys
import time
import json
import socket
from typing import Dict, Any
from hand_to_servo_mapper import HandToServoMapper

class InMoovHandController:
    def __init__(self, servo_port="/dev/cu.usbserial-140", unity_port=5065):
        """
        Initialize the InMoov hand controller
        
        Args:
            servo_port: Serial port for the servo controller
            unity_port: Port to receive hand tracking data from Unity
        """
        self.unity_port = unity_port
        self.servo_port = servo_port
        self.mapper = HandToServoMapper()
        
        # Initialize UDP socket to receive hand tracking data
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", self.unity_port))
        self.socket.settimeout(1.0)  # 1 second timeout
        
        # Initialize servo controller
        try:
            self.init_servo_controller()
        except Exception as e:
            print(f"Error initializing servo controller: {e}")
            sys.exit(1)
    
    def init_servo_controller(self):
        """Initialize the servo controller board"""
        # TODO: Add your servo controller initialization code here
        # This will depend on your specific servo controller
        # For example, if using Arduino:
        # import serial
        # self.servo = serial.Serial(self.servo_port, 9600)
        pass
    
    def set_servo_angles(self, angles: Dict[str, int]):
        """
        Set the angles for all servos
        
        Args:
            angles: Dictionary of servo names and their angles
        """
        # TODO: Add your servo control code here
        # This will depend on your specific servo controller
        # For example, if using Arduino, send a command like:
        # command = f"angles,{angles['thumb']},{angles['index']},{angles['middle']},{angles['ring']},{angles['pinky']},{angles['wrist']}\n"
        # self.servo.write(command.encode())
        
        # For now, just print the angles
        print("Setting servo angles:")
        for servo, angle in angles.items():
            print(f"  {servo}: {angle}°")
    
    def process_hand_data(self, data: Dict[str, Any]) -> bool:
        """
        Process hand tracking data and control servos
        
        Args:
            data: Hand tracking data from Unity
            
        Returns:
            bool: True if processing was successful
        """
        try:
            # We expect at least one hand
            if not data.get("hands"):
                return False
            
            # Use the first detected hand
            hand = data["hands"][0]
            
            # Extract landmarks into the format expected by the mapper
            landmarks = []
            for lm in hand["landmarks"]:
                landmarks.append(lm["position"])
            
            # Map hand position to servo angles
            servo_angles = self.mapper.map_to_servo_angles(landmarks)
            
            # Set the servo angles
            self.set_servo_angles(servo_angles)
            
            return True
            
        except Exception as e:
            print(f"Error processing hand data: {e}")
            return False
    
    def run(self):
        """Main control loop"""
        print(f"InMoov Hand Controller started")
        print(f"Listening for hand tracking data on port {self.unity_port}")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                try:
                    # Receive hand tracking data
                    data, addr = self.socket.recvfrom(65535)
                    hand_data = json.loads(data.decode())
                    
                    # Process the data
                    if self.process_hand_data(hand_data):
                        print(".", end="", flush=True)  # Progress indicator
                    
                except socket.timeout:
                    continue
                except json.JSONDecodeError as e:
                    print(f"Error decoding hand data: {e}")
                    continue
                
                time.sleep(0.01)  # Small delay to prevent CPU overload
                
        except KeyboardInterrupt:
            print("\nStopping hand controller...")
        finally:
            self.socket.close()
            # TODO: Add any cleanup code for your servo controller here

def main():
    # You can specify your servo controller port here
    controller = InMoovHandController(servo_port="/dev/ttyUSB0")
    controller.run()

if __name__ == "__main__":
    main()