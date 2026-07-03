"""
Arduino port detection utility.
Auto-detects available serial ports and lets you pick one if multiple exist.
Works on macOS (cu.* and tty.*), Windows (COM*), and Linux (/dev/ttyUSB*, /dev/ttyACM*).
"""

import serial.tools.list_ports
import sys


def list_available_ports():
    """Return list of (port, description) tuples for all available serial devices."""
    ports = []
    for port_info in serial.tools.list_ports.comports():
        ports.append((port_info.device, port_info.description or "Unknown"))
    return ports


def find_arduino_port(verbose=True):
    """
    Auto-detect Arduino port.

    If one port exists, use it.
    If multiple exist, prompt user to choose.
    If none, return None.

    Args:
        verbose: Print debug info

    Returns:
        str: Arduino port name (e.g. "/dev/cu.usbserial-140", "COM3")
        None: No port found
    """
    ports = list_available_ports()

    if not ports:
        if verbose:
            print("❌ No serial ports found.")
            print("   Check that your Arduino is plugged in.")
        return None

    if len(ports) == 1:
        port, desc = ports[0]
        if verbose:
            print(f"✅ Found Arduino: {port}")
            print(f"   {desc}")
        return port

    # Multiple ports — let user pick
    if verbose:
        print(f"\n🔍 Found {len(ports)} serial port(s):")
        for i, (port, desc) in enumerate(ports, 1):
            print(f"   {i}. {port}")
            print(f"      {desc}")
        print()

    while True:
        try:
            choice = input("Pick a port (enter number): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(ports):
                port, desc = ports[idx]
                if verbose:
                    print(f"✅ Using: {port}\n")
                return port
            else:
                print(f"❌ Pick a number between 1 and {len(ports)}")
        except (ValueError, KeyboardInterrupt):
            print("❌ Cancelled")
            return None


def connect_arduino(port, baud_rate=9600, timeout=1):
    """
    Connect to Arduino on the given port.

    Args:
        port: Serial port name
        baud_rate: Baud rate (default 9600)
        timeout: Read timeout

    Returns:
        serial.Serial or None if connection failed
    """
    try:
        arduino = serial.Serial(port, baud_rate, timeout=timeout)
        return arduino
    except Exception as e:
        print(f"❌ Failed to connect to {port}: {e}")
        return None
