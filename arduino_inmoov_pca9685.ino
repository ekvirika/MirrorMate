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
int thumbAngle = 90;
int indexAngle = 90;
int middleAngle = 90;
int ringAngle = 90;
int pinkyAngle = 90;
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

  Serial.println("💡 Make sure camera_to_arduino_pca9685.py is running!");
}

void loop() {
  // Check for incoming serial data from Python
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');

    // Parse servo angles from data like "T:45,I:67,M:23,R:89,P:12,H:134"
    if (data.startsWith("T:") && data.indexOf(",I:") != -1) {
      parseServoData(data);

      // Move servos to new positions
      setServoPositions();

      // Send confirmation back to Python
      Serial.print("ACK:");
      Serial.print(thumbAngle);
      Serial.print(",");
      Serial.print(indexAngle);
      Serial.print(",");
      Serial.print(middleAngle);
      Serial.print(",");
      Serial.print(ringAngle);
      Serial.print(",");
      Serial.print(pinkyAngle);
      Serial.print(",");
      Serial.println(handAngle);
    }
  }
}

void parseServoData(String data) {
  // Remove "T:" prefix if present
  if (data.startsWith("T:")) {
    data = data.substring(2);
  }

  // Split by commas and extract angles
  int comma1 = data.indexOf(',');
  int comma2 = data.indexOf(',', comma1 + 1);
  int comma3 = data.indexOf(',', comma2 + 1);
  int comma4 = data.indexOf(',', comma3 + 1);
  int comma5 = data.indexOf(',', comma4 + 1);

  if (comma1 != -1 && comma2 != -1 && comma3 != -1 && comma4 != -1 && comma5 != -1) {
    thumbAngle = data.substring(0, comma1).toInt();
    indexAngle = data.substring(comma1 + 1, comma2).toInt();
    middleAngle = data.substring(comma2 + 1, comma3).toInt();
    ringAngle = data.substring(comma3 + 1, comma4).toInt();
    pinkyAngle = data.substring(comma4 + 1, comma5).toInt();
    handAngle = data.substring(comma5 + 1).toInt();

    // Clamp angles to valid servo range (0-179)
    thumbAngle = constrain(thumbAngle, 0, 179);
    indexAngle = constrain(indexAngle, 0, 179);
    middleAngle = constrain(middleAngle, 0, 179);
    ringAngle = constrain(ringAngle, 0, 179);
    pinkyAngle = constrain(pinkyAngle, 0, 179);
    handAngle = constrain(handAngle, 0, 179);

    Serial.print("🎯 Received angles - T:");
    Serial.print(thumbAngle);
    Serial.print(" I:");
    Serial.print(indexAngle);
    Serial.print(" M:");
    Serial.print(middleAngle);
    Serial.print(" R:");
    Serial.print(ringAngle);
    Serial.print(" P:");
    Serial.print(pinkyAngle);
    Serial.print(" H:");
    Serial.println(handAngle);
  } else {
    Serial.println("❌ Invalid data format received");
  }
}

void setServoPositions() {
  // Set servo positions using PCA9685
  setServoAngle(THUMB_SERVO, thumbAngle);
  setServoAngle(INDEX_SERVO, indexAngle);
  setServoAngle(MIDDLE_SERVO, middleAngle);
  setServoAngle(RING_SERVO, ringAngle);
  setServoAngle(PINKY_SERVO, pinkyAngle);
  setServoAngle(HAND_SERVO, handAngle);

  // Small delay to allow servos to reach position
  delay(15);
}

void setServoAngle(int servoNum, int angle) {
  // Convert angle (0-179) to pulse length
  int pulse = map(angle, 0, 179, SERVOMIN, SERVOMAX);
  pwm.setPWM(servoNum, 0, pulse);
}
