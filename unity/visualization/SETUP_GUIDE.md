# Mirror Mate - Unity Hand Visualization Setup Guide

This guide will help you set up the enhanced hand tracking visualization in Unity.

## Prerequisites

- Unity 2020.3 LTS or newer
- Newtonsoft JSON package (com.unity.nuget.newtonsoft-json)

## Setup Steps

### 1. Create a New Unity Project

1. Open Unity Hub
2. Click "New Project"
3. Select "3D" template
4. Name your project "MirrorMate"
5. Click "Create Project"

### 2. Import Required Packages

1. In Unity, go to Window > Package Manager
2. Click the "+" button in the top-left corner
3. Choose "Add package from git URL..."
4. Enter: `com.unity.nuget.newtonsoft-json`
5. Click "Add"

### 3. Create Required Assets

#### Create a Scripts Folder
1. Right-click in the Project window
2. Select Create > Folder
3. Name it "Scripts"

#### Create Materials
1. Right-click in the Project window
2. Select Create > Folder
3. Name it "Materials"
4. Create the following materials:
   - Right-click in the Materials folder > Create > Material
   - Create "LeftHandMaterial" (set color to blue)
   - Create "RightHandMaterial" (set color to red)
   - Create "ForearmMaterial" (set color to green or purple)

#### Create Prefabs
1. Create a "Prefabs" folder
2. Create a Joint Prefab:
   - Create a sphere in the scene (GameObject > 3D Object > Sphere)
   - Rename it to "JointPrefab"
   - Scale it down to about 0.1, 0.1, 0.1
   - Drag it from the Hierarchy to the Prefabs folder
   - Delete it from the scene
3. Create a Bone Prefab:
   - Create a cylinder in the scene (GameObject > 3D Object > Cylinder)
   - Rename it to "BonePrefab"
   - Scale it to about 0.05, 1, 0.05
   - Drag it from the Hierarchy to the Prefabs folder
   - Delete it from the scene

### 4. Set Up the Scene

1. Create an empty GameObject named "HandTrackingManager"
2. Add the HandTrackingReceiver script to it:
   - With the HandTrackingManager selected, click "Add Component" in the Inspector
   - Select "New Script"
   - Name it "HandTrackingReceiver"
   - Open the script and replace its contents with our HandTrackingReceiver.cs code
3. Configure the HandTrackingReceiver component:
   - Assign the Joint Prefab to the "Joint Prefab" field
   - Assign the Bone Prefab to the "Bone Prefab" field
   - Assign the left hand material to "Left Hand Material"
   - Assign the right hand material to "Right Hand Material"
   - Assign the forearm material to "Forearm Material"
   - Set "Joint Scale" to 0.01
   - Set "Hand Scale" to 0.01
   - Set "Bone Width" to 0.005
   - Make sure "Enhanced Visualization" and "Show Forearm" are checked

### 5. Run the Application

1. Click the Play button in Unity
2. Run the Python script with:
   ```
   python hand_detection/unity_exporter.py
   ```
3. When prompted, enter 'y' to start tracking immediately
4. Place your hands in front of the camera

## Troubleshooting

### No Visualization in Unity
- Check Unity console for error messages
- Verify the Python script is running and detecting hands
- Make sure both are using the same port (default: 5065)

### Only One Hand Showing
- The updated script now supports multiple hands
- Make sure both hands are visible to the camera
- Try moving your hands to different positions

### Depth Not Working Correctly
- The Z-coordinate is now properly scaled for better depth visualization
- Try moving your hand closer/further from the camera to see the effect

### Forearm Not Showing
- Make sure "Show Forearm" is checked in the HandTrackingReceiver component
- The forearm is estimated based on wrist position, so it may not be perfectly accurate

## Customization

You can customize the visualization by adjusting:
- Joint Scale: Size of the joint spheres
- Hand Scale: Overall scale of the hand model
- Bone Width: Thickness of the connections between joints
- Enhanced Visualization: Toggle between debug lines and 3D bone models
- Show Forearm: Toggle the forearm visualization on/off
