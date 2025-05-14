# Mirror Mate Robot

A senior project for electrical and computer engineering that creates a robot capable of mirroring human hand movements.

## Project Components

1. **Hand Detection Sensor (3D)**
   - Train a model to detect hand movements in 3D space
   - Deploy the model on Jetson Nano

2. **Unity Visualization**
   - Visualize detected hand movements in Unity 3D

3. **Robotic Hand Control**
   - Control a robotic hand to mirror the detected hand movements

## Setup

Each component has its own directory with specific setup instructions.

### Hand Detection

```bash
cd hand_detection
pip install -r requirements.txt
```

### Unity Visualization

See the README in the unity_visualization directory.

### Robotic Control

See the README in the robotic_control directory.
