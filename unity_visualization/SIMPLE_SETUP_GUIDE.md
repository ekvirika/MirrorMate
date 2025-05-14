# Simple Hand Visualizer Setup Guide

This guide will help you quickly set up the improved hand visualization in Unity with minimal effort.

## Prerequisites

- Unity 2020.3 LTS or newer
- Newtonsoft JSON package (com.unity.nuget.newtonsoft-json)

## Quick Setup Steps

### 1. Create Basic Unity Project

1. Open Unity Hub and create a new 3D project
2. Install the Newtonsoft JSON package:
   - Window > Package Manager > "+" > "Add package from git URL..."
   - Enter: `com.unity.nuget.newtonsoft-json`

### 2. Set Up Materials

1. Create a "Materials" folder in your Project window
2. Create three materials:
   - **LeftHandMaterial**: Set color to blue (0.2, 0.4, 1.0)
   - **RightHandMaterial**: Set color to red (1.0, 0.3, 0.3)
   - **ForearmMaterial**: Set color to purple (0.5, 0.2, 0.8)

### 3. Create Joint Prefab

1. Create a sphere in your scene (GameObject > 3D Object > Sphere)
2. Scale it down to (0.1, 0.1, 0.1)
3. Create a "Prefabs" folder
4. Drag the sphere into the Prefabs folder to create a prefab
5. Delete the sphere from your scene

### 4. Set Up the Visualizer

1. Create an empty GameObject named "HandTracker" in your scene
2. With HandTracker selected, click "Add Component" in the Inspector
3. Select "New Script" and name it "SimpleHandVisualizer"
4. Open the script and replace its contents with our SimpleHandVisualizer.cs code
5. Save the script

### 5. Configure the Visualizer

In the Inspector for the HandTracker object:

1. Assign your sphere prefab to the "Joint Prefab" field
2. Assign your materials to:
   - "Left Hand Material"
   - "Right Hand Material"
   - "Forearm Material"
3. Set these recommended values:
   - Hand Scale: 0.01
   - Depth Scale: 10
   - Line Width: 0.005
   - Smoothing Speed: 10
4. Make sure these options are checked:
   - Show Forearm
   - Show Connections
   - Smooth Motion

### 6. Run the Application

1. Press Play in Unity
2. Run the Python script in a terminal:
   ```
   python hand_detection/unity_exporter.py
   ```
3. When prompted, type 'y' to start tracking immediately
4. Place your hands in front of the camera

## Troubleshooting

### No Visualization in Unity
- Check Unity console for error messages
- Make sure both applications are using the same port (default: 5065)
- Verify your camera is working and hands are being detected

### Forearm Not Showing
- Make sure "Show Forearm" is checked in the SimpleHandVisualizer component
- The forearm detection has been improved, but still requires your hand to be in a good position

### Visualization Looks Bad
- Try adjusting the "Hand Scale" and "Depth Scale" values
- Increase "Line Width" for thicker connections
- Adjust "Smoothing Speed" (higher = faster response, less smooth)

## Customization

You can easily customize the visualization by:
- Creating a more detailed joint prefab
- Using different materials with emission for a glowing effect
- Adjusting the scale parameters to match your scene size
