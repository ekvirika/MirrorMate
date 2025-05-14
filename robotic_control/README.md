# Robotic Hand Control

This component of the Mirror Mate project controls a robotic hand to mirror the detected hand movements.

## Hardware Requirements

- Servo motors (one for each joint to be controlled)
- Microcontroller (Arduino, Raspberry Pi, or similar)
- Power supply for the servos
- Robotic hand assembly (3D printed or purchased)

## Software Setup

1. **Install required libraries**
   ```bash
   pip install pyserial
   ```

2. **Arduino Setup (if using Arduino)**
   - Install the Arduino IDE
   - Install the Servo library through the Arduino Library Manager
   - Upload the provided Arduino sketch to your board

## Connection

The Python script communicates with the microcontroller via serial connection. Make sure to:
1. Set the correct serial port in the configuration
2. Match the baud rate between the Python script and the microcontroller code

## Usage

1. Run the hand tracking system
2. Start the robotic control script
3. The robotic hand should now mirror your hand movements

## Calibration

The robotic hand may need calibration to match the range of motion of your hand. Use the calibration utility to:
- Set minimum and maximum angles for each servo
- Adjust the mapping between hand tracking data and servo positions
