# Unity Hand Visualization

This component of the Mirror Mate project visualizes the hand tracking data in Unity 3D.

## Setup Instructions

1. **Create a new Unity project**
   - Download and install Unity Hub from [unity.com](https://unity.com/download)
   - Create a new 3D project (Unity 2020.3 LTS or newer recommended)

2. **Import required packages**
   - In Unity, go to Window > Package Manager
   - Add the following packages:
     - Newtonsoft JSON (com.unity.nuget.newtonsoft-json)

3. **Set up the scene**
   - Create a new empty GameObject and name it "HandTrackingManager"
   - Add the HandTrackingReceiver.cs script to this GameObject
   - Create the following assets:
     - Joint Prefab: A small sphere to represent hand joints
     - Left Hand Material: A blue material for the left hand
     - Right Hand Material: A red material for the right hand
   - Assign these assets to the HandTrackingReceiver component in the Inspector

4. **Configure network settings**
   - Make sure the port in HandTrackingReceiver matches the port used in the Python unity_exporter.py script (default: 5065)
   - If running on different machines, update the IP address in the Python script to point to your Unity machine

5. **Run the visualization**
   - Start the Unity project
   - Run the Python unity_exporter.py script
   - The hand tracking data should now be visualized in Unity

## Customization

You can customize the visualization by adjusting the following parameters in the HandTrackingReceiver component:
- Joint Scale: Size of the joint spheres
- Hand Scale: Overall scale of the hand model
- Materials: Change the appearance of the hand joints

## Troubleshooting

- If no data is received, check that the port is not blocked by a firewall
- Verify that the Python script is running and successfully tracking hands
- Check the Unity console for any error messages
