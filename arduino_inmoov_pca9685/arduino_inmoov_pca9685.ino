#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Initialize PCA9685 servo driver
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// Servo pulse length constants
#define SERVOMIN 150  // pulse length for 0 degrees
#define SERVOMAX 550  // pulse length for 180 degrees

// Servo indices for your InMoov hand
#define THUMB_SERVO 0
#define INDEX_SERVO 1
#define MIDDLE_SERVO 2
#define RING_SERVO 3
#define PINKY_SERVO 4
#define HAND_SERVO 5

// Current servo angles (0-179 degrees)
int thumbAngle = 0;
int indexAngle = 0;
int middleAngle = 0;
int ringAngle = 0;
int pinkyAngle = 0;
int handAngle = 90;

// Serial communication
const int BAUD_RATE = 9600;

void setup() {
  Serial.begin(BAUD_RATE);

  Serial.println("🤖 Arduino InMoov Hand Controller (PCA9685) Ready!");
  Serial.println("📡 Waiting for camera data...");

  // Initialize PCA9685
  pwm.begin();
  pwm.setPWMFreq(50);  // 50Hz for analog servos
  delay(10);

  // Set all servos to neutral position
  setServoPositions();

  Serial.println("💡 Ready to receive commands!");
}

void loop() {
  // Check for incoming serial data from Python
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');
    
    // Parse servo command from data like "1:90!" (servo:angle!)
    if (data.indexOf(':') != -1 && data.endsWith("!")) {
      // Remove the trailing !
      data = data.substring(0, data.length() - 1);
      
      // Split into servo number and angle
      int colonPos = data.indexOf(':');
      int servoNum = data.substring(0, colonPos).toInt();
      int angle = data.substring(colonPos + 1).toInt();
      
      // Clamp angle to valid range
      angle = constrain(angle, 0, 179);
      
      // Update the appropriate servo
      switch(servoNum) {
        case 1: // Index finger
          indexAngle = angle;
          setServoAngle(INDEX_SERVO, angle);
          break;
        case 2: // Middle finger
          middleAngle = angle;
          setServoAngle(MIDDLE_SERVO, angle);
          break;
        case 3: // Thumb
          thumbAngle = angle;
          setServoAngle(THUMB_SERVO, angle);
          break;
        case 4: // Ring finger
          ringAngle = angle;
          setServoAngle(RING_SERVO, angle);
          break;
        case 5: // Pinky
          pinkyAngle = angle;
          setServoAngle(PINKY_SERVO, angle);
          break;
        case 6: // Hand rotation
          handAngle = angle;
          setServoAngle(HAND_SERVO, angle);
          break;
      }
      
      // Small delay to allow servo to start moving
      delay(5);
      
      // Send acknowledgment
      Serial.print("OK:");
      Serial.print(servoNum);
      Serial.print(":");
      Serial.println(angle);
    }
  }
}

void setServoPositions() {
  // Set all servos to their current angles
  setServoAngle(THUMB_SERVO, thumbAngle);
  setServoAngle(INDEX_SERVO, indexAngle);
  setServoAngle(MIDDLE_SERVO, middleAngle);
  setServoAngle(RING_SERVO, ringAngle);
  setServoAngle(PINKY_SERVO, pinkyAngle);
  setServoAngle(HAND_SERVO, handAngle);
}

void setServoAngle(int servoNum, int angle) {
  // Convert angle (0-179) to pulse length
  int pulse = map(angle, 0, 179, SERVOMIN, SERVOMAX);
  pwm.setPWM(servoNum, 0, pulse);
}