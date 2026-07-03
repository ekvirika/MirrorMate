import serial
import time
import random
import sys
sys.path.insert(0, '..')

from arduino_utils import find_arduino_port, connect_arduino

BAUD_RATE = 9600
arduino = None
arduino_connected = False

def connect_to_arduino():
    """Try to connect to Arduino"""
    global arduino, arduino_connected

    port = find_arduino_port(verbose=True)
    if not port:
        print("\n❌ No Arduino port found!")
        print("\nTroubleshooting tips:")
        print("1. Check if the Arduino is properly plugged in")
        print("2. On macOS, use 'ls /dev/cu.*' to list ports")
        print("3. On Windows, check Device Manager for COM ports")
        print("4. Make sure you have permission to access the port")
        print("5. Close any other programs that might be using the port")
        return False

    arduino = connect_arduino(port, BAUD_RATE)
    if arduino:
        time.sleep(2)  # Wait for Arduino to initialize
        arduino_connected = True
        print(f"✅ Connected!")
        return True
    else:
        return False

def send_servo_command(servo_id, angle):
    """Send a single servo command to Arduino"""
    if not arduino_connected or not arduino:
        return False

    try:
        data = f"{servo_id}:{angle}!\n"
        arduino.write(data.encode())
        arduino.flush()
        print(f"Sent: {data.strip()}")
        time.sleep(0.05)  # Small delay between commands
        return True
    except Exception as e:
        print(f"Error sending servo command: {e}")
        return False

def set_hand_position(position):
    """Set the hand to a specific rock-paper-scissors position"""

    print(f"\n🎮 Making move: {position.upper()}")

    if position == "paper":
        # Paper: All fingers extended (starting position)
        # Based on the mapping in the original code:
        # - Higher input angles (closer to 180°) map to lower servo angles (0°)
        # - This represents extended fingers

        # Thumb (Servo 3) - extended
        send_servo_command(3, 120)   # Extended thumb

        # Index (Servo 1) - extended
        send_servo_command(1, 30)   # Extended finger

        # Middle (Servo 2) - extended
        send_servo_command(2, 30)   # Extended finger

        # Ring (Servo 4) - extended
        send_servo_command(4, 20)  # Extended (minimum 30° for ring finger)

        # Pinky (Servo 5) - extended
        send_servo_command(5, 20)   # Extended pinky

        # Wrist (Servo 6) - neutral
        send_servo_command(6, 90)  # Neutral wrist position

    elif position == "scissors":
        # Scissors: Index and middle fingers extended, ring and pinky folded, thumb positioned
        print("✌️  Index and middle fingers extended, others folded")

        # Thumb (Servo 3) - positioned for scissors (partially extended)
        send_servo_command(3, 170)  # Mid position for scissors

        # Index (Servo 1) - extended
        send_servo_command(1, 30)   # Extended finger

        # Middle (Servo 2) - extended
        send_servo_command(2, 30)   # Extended finger

        # Ring (Servo 4) - folded
        send_servo_command(4, 180) # Folded ring finger

        # Pinky (Servo 5) - folded
        send_servo_command(5, 175) # Folded pinky

        # Wrist (Servo 6) - neutral
        send_servo_command(6, 90)  # Neutral wrist position

    elif position == "rock":
        # Rock: All fingers folded into a fist
        print("✊ All fingers folded")

        # Thumb (Servo 3) - folded over fingers
        send_servo_command(3, 170) # Folded thumb

        # Index (Servo 1) - folded
        send_servo_command(1, 180) # Folded finger

        # Middle (Servo 2) - folded
        send_servo_command(2, 180) # Folded finger

        # Ring (Servo 4) - folded
        send_servo_command(4, 180) # Folded ring finger

        # Pinky (Servo 5) - folded
        send_servo_command(5, 175) # Folded pinky

        # Wrist (Servo 6) - neutral
        send_servo_command(6, 90)  # Neutral wrist position

def get_random_move():
    """Get a random rock-paper-scissors move"""
    moves = ["rock", "paper", "scissors"]
    return random.choice(moves)

def main():
    print("=" * 60)
    print("🤖 ARDUINO ROCK-PAPER-SCISSORS HAND")
    print("=" * 60)
    print("This script will make your robotic hand play rock-paper-scissors!")
    print("\nInstructions:")
    print("  1. Make sure your Arduino is connected")
    print("  2. Upload arduino_inmoov_pca9685.ino to your Arduino")
    print("  3. The hand will make a random move after 3 seconds")
    print("\nMoves:")
    print("  📄 Paper: All fingers extended (starting position)")
    print("  ✌️  Scissors: Index and middle extended, others folded")
    print("  ✊ Rock: All fingers folded into a fist")
    print("=" * 60)

    # Try to connect to Arduino
    if not connect_to_arduino():
        print("\n❌ Arduino connection failed!")
        print("Please check your Arduino connection and try again.")
        return

    print("\n🎯 Arduino connected successfully!")
    print("⏰ Starting rock-paper-scissors in 3 seconds...")

    # Countdown
    for i in range(3, 0, -1):
        print(f"⏳ {i}...")
        time.sleep(1)

    # Make a random move
    move = get_random_move()
    set_hand_position(move)

    print(f"\n🎉 Made move: {move.upper()}!")
    print("🤖 Your robotic hand is ready!")

    # Keep the position for a few seconds so you can see it
    print("👀 Keeping position for 5 seconds...")
    time.sleep(5)

    print("\n✅ Demo complete!")
    print("You can run the script again to see another random move.")

    # Cleanup
    if arduino_connected and arduino:
        try:
            arduino.close()
            print("🔌 Arduino connection closed")
        except:
            pass

if __name__ == "__main__":
    main()
