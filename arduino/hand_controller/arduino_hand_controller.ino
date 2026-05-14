#include <Servo.h>

// Servo pins
#define THUMB_SERVO_PIN 2
#define INDEX_SERVO_PIN 3
#define MIDDLE_SERVO_PIN 4
#define RING_SERVO_PIN 5
#define PINKY_SERVO_PIN 6
#define HAND_SERVO_PIN 7

// Servo objects
Servo thumbServo;
Servo indexServo;
Servo middleServo;
Servo ringServo;
Servo pinkyServo;
Servo handServo;

// Servo angles (0-179 degrees)
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

  // Attach servos to pins
  thumbServo.attach(THUMB_SERVO_PIN);
  indexServo.attach(INDEX_SERVO_PIN);
  middleServo.attach(MIDDLE_SERVO_PIN);
  ringServo.attach(RING_SERVO_PIN);
  pinkyServo.attach(PINKY_SERVO_PIN);
  handServo.attach(HAND_SERVO_PIN);

  // Initialize servos to neutral position
  thumbServo.write(thumbAngle);
  indexServo.write(indexAngle);
  middleServo.write(middleAngle);
  ringServo.write(ringAngle);
  pinkyServo.write(pinkyAngle);
  handServo.write(handAngle);

  Serial.println("Arduino Robotic Hand Controller Ready!");
  Serial.println("Waiting for Unity data...");
}

void loop() {
  // Check for incoming serial data
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');

    // Parse the received data
    if (data.startsWith("T:") && data.indexOf(",I:") != -1) {
      parseServoData(data);

      // Move servos to new positions
      moveServos();

      // Send confirmation back to Unity
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

  // Split by commas
  int comma1 = data.indexOf(',');
  int comma2 = data.indexOf(',', comma1 + 1);
  int comma3 = data.indexOf(',', comma2 + 1);
  int comma4 = data.indexOf(',', comma3 + 1);
  int comma5 = data.indexOf(',', comma4 + 1);

  if (comma1 != -1 && comma2 != -1 && comma3 != -1 && comma4 != -1 && comma5 != -1) {
    // Extract angles
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

    Serial.print("Received angles - T:");
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
    Serial.println("Invalid data format received");
  }
}

void moveServos() {
  // Move servos to target angles
  thumbServo.write(thumbAngle);
  indexServo.write(indexAngle);
  middleServo.write(middleAngle);
  ringServo.write(ringAngle);
  pinkyServo.write(pinkyAngle);
  handServo.write(handAngle);

  // Small delay to allow servos to reach position
  delay(15);
}
