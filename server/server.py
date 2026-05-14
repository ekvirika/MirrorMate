import asyncio
import json
import websockets
import cv2
import numpy as np
import base64
from PIL import Image
import io
import sys
import os

# Add hand_detection to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'hand_detection'))
from hand_tracker import HandTracker

class HandTrackingServer:
    def __init__(self):
        self.hand_tracker = HandTracker()
        self.ios_clients = set()
        self.unity_clients = set()

    async def handle_ios_client(self, websocket):
        """Handle incoming connections from iOS clients."""
        self.ios_clients.add(websocket)
        try:
            async for message in websocket:
                try:
                    print("\nReceived frame, processing...")
                    # Decode base64 image
                    img_data = base64.b64decode(message)
                    print("Image decoded from base64")
                    img = Image.open(io.BytesIO(img_data))
                    print(f"Image opened, size: {img.size}")
                    
                    # Convert PIL image to CV2 format
                    cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    print("Image converted to CV2 format")
                    
                    # Process frame with hand tracker and get visualization
                    print("Processing frame with hand tracker...")
                    results = self.hand_tracker.process_frame(cv_image)
                    print("Frame processed")
                    img_with_hands, _ = self.hand_tracker.find_hands(cv_image, draw=True)
                    print(f"Hand tracking results: {results}")
                    
                    # Show the frame with hand tracking
                    cv2.imshow('iPhone Camera Feed', img_with_hands)
                    cv2.moveWindow('iPhone Camera Feed', 100, 100)  # Position window at (100,100)
                    key = cv2.waitKey(1)  # Update window and handle events
                    print("Frame displayed")
                    
                    # Convert results to JSON
                    if results:
                        data = {
                            'type': 'hand_tracking',
                            'landmarks': results
                        }
                        
                        # Send to all Unity clients
                        if self.unity_clients:
                            await asyncio.gather(
                                *[client.send(json.dumps(data)) for client in self.unity_clients]
                            )
                
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    
        finally:
            self.ios_clients.remove(websocket)

    async def handle_unity_client(self, websocket):
        """Handle incoming connections from Unity clients."""
        self.unity_clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.unity_clients.remove(websocket)

    async def handler(self, websocket, path):
        """Route clients based on their connection path."""
        if path == "/ios":
            await self.handle_ios_client(websocket)
        elif path == "/unity":
            await self.handle_unity_client(websocket)
        else:
            await websocket.close()

async def main():
    server = HandTrackingServer()
    
    # Start server
    host = "0.0.0.0"  # Listen on all available network interfaces
    port = 8765
    
    # Print network interfaces
    import netifaces
    print("\nAvailable network interfaces:")
    for interface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                print(f"Interface {interface}: {addr['addr']}")
    
    try:
        async with websockets.serve(server.handler, host, port):
            print(f"\nServer started and listening on all interfaces, port {port}")
            print(f"Use your computer's IP address with port {port}")
            print(f"Full WebSocket URL example: ws://192.168.15.137:{port}/ios")
            print("\nWaiting for connections...")
            await asyncio.Future()  # run forever
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    asyncio.run(main())