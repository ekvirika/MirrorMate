# Catch the Falling Balls Game Setup Guide

This guide will help you set up the falling balls game where you can catch balls with your hands.

## Setup Instructions

### 1. Create Game Objects

1. Create an empty GameObject named "GameManager" and add the GameManager script
2. Create an empty GameObject named "BallSpawner" and add the BallController script

### 2. Create Ball Prefab

1. Create a sphere (GameObject > 3D Object > Sphere)
2. Scale it down to about (0.5, 0.5, 0.5)
3. Add a material with a bright color (like red or blue)
4. Add a Rigidbody component
5. Add a SphereCollider component
6. Add an AudioSource component (for catch sound)
7. Create a new audio clip for the catch sound (optional)
8. Drag the sphere to your Prefabs folder to create a prefab
9. Delete the sphere from the scene

### 3. Configure GameManager

1. Select the GameManager object
2. In the Inspector:
   - Drag your ball prefab into the "Ball Prefab" field
   - Adjust "Spawn Interval" (default: 1)
   - Adjust "Min Spawn Interval" (default: 0.5)
   - Adjust "Spawn Interval Decrease" (default: 0.05)
   - Set "Time To Start" (default: 3)
   - Drag your score text UI element into "Score Text"
   - Drag your countdown text UI element into "Countdown Text"

### 4. Configure BallController

1. Select the BallSpawner object
2. In the Inspector:
   - Adjust "Fall Speed" (default: 3)
   - Adjust "Min/Max Spawn X" (default: -5 to 5)
   - Adjust "Spawn Y" (default: 10)
   - Adjust "Min/Max Size" (default: 0.5 to 1.5)
   - Adjust "Destroy Y" (default: -5)
   - Set "Points Per Catch" (default: 10)

### 5. Add UI Elements

1. Create a Canvas (GameObject > UI > Canvas)
2. Add a TextMeshPro text object for the score display
3. Add a TextMeshPro text object for the countdown
4. Position these elements appropriately in your scene

### 6. Configure Hand Models

1. For each hand model in your scene:
   - Add the HandCollider script
   - Adjust "Collider Radius" if needed
   - Set "Hand Layer" if you want to use a specific layer

### 7. Add Sound Effects

1. Create a folder "Sounds" in your Assets
2. Add a catch sound effect (wav or mp3 format)
3. Drag the sound into the BallController's AudioSource component

## How to Play

1. Press Play in Unity
2. Wait for the countdown to finish
3. Balls will start falling from the top of the screen
4. Move your hands to catch the falling balls
5. Each ball caught adds 10 points to your score
6. The game gets progressively harder as time goes on
7. Balls that hit the ground are lost

## Tips

- The game gets harder over time with faster falling balls
- Try to catch as many balls as possible
- Experiment with different spawn intervals and ball speeds
- Add more sound effects for different events (game start, game over, etc.)
