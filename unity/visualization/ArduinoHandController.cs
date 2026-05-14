using System;
using System.Collections;
using System.Collections.Generic;
using System.IO.Ports;
using System.Linq;
using UnityEngine;
using Newtonsoft.Json;

public class ArduinoHandController : MonoBehaviour
{
    [Header("Arduino Communication")]
    [SerializeField] private string portName = "COM3"; // Change to your Arduino port
    [SerializeField] private int baudRate = 9600;
    [SerializeField] private bool autoConnect = true;

    [Header("Servo Mapping")]
    [SerializeField] private float thumbAngle = 0f;
    [SerializeField] private float indexAngle = 0f;
    [SerializeField] private float middleAngle = 0f;
    [SerializeField] private float ringAngle = 0f;
    [SerializeField] private float pinkyAngle = 0f;
    [SerializeField] private float handAngle = 0f;

    [Header("Hand Tracking Reference")]
    [SerializeField] private HandTrackingReceiver handTracker;

    private SerialPort serialPort;
    private bool isConnected = false;

    // Hand landmark indices for finger tips and MCP joints
    private int[] fingerTips = { 4, 8, 12, 16, 20 }; // Thumb, Index, Middle, Ring, Pinky tips
    private int[] fingerMCPs = { 2, 5, 9, 13, 17 };  // Thumb, Index, Middle, Ring, Pinky MCPs

    void Start()
    {
        if (autoConnect)
        {
            ConnectToArduino();
        }

        if (handTracker == null)
        {
            handTracker = FindObjectOfType<HandTrackingReceiver>();
            if (handTracker == null)
            {
                Debug.LogError("[ArduinoHandController] HandTrackingReceiver not found!");
            }
        }
    }

    void Update()
    {
        if (isConnected && handTracker != null)
        {
            // Get current hand data from HandTrackingReceiver
            var multiHandData = handTracker.GetCurrentMultiHandData();
            if (multiHandData != null && multiHandData.hands.Count > 0)
            {
                ProcessHandData(multiHandData.hands[0]);
            }
        }
    }

    public void ConnectToArduino()
    {
        try
        {
            serialPort = new SerialPort(portName, baudRate);
            serialPort.Open();
            isConnected = true;
            Debug.Log($"[ArduinoHandController] Connected to Arduino on {portName}");
        }
        catch (Exception e)
        {
            Debug.LogError($"[ArduinoHandController] Failed to connect to Arduino: {e.Message}");
            isConnected = false;
        }
    }

    public void DisconnectArduino()
    {
        if (serialPort != null && serialPort.IsOpen)
        {
            serialPort.Close();
            isConnected = false;
            Debug.Log("[ArduinoHandController] Disconnected from Arduino");
        }
    }

    private void ProcessHandData(HandData handData)
    {
        if (handData.landmarks.Count < 21)
            return;

        // Calculate finger angles based on hand landmarks
        CalculateFingerAngles(handData);

        // Send servo angles to Arduino
        SendServoAngles();
    }

    private void CalculateFingerAngles(HandData handData)
    {
        // Get landmark positions
        var landmarks = handData.landmarks;

        // Calculate angles for each finger (0-179 degrees)
        thumbAngle = CalculateFingerAngle(landmarks, 0, 1, 2, 3, 4);  // Thumb
        indexAngle = CalculateFingerAngle(landmarks, 0, 5, 6, 7, 8);  // Index
        middleAngle = CalculateFingerAngle(landmarks, 0, 9, 10, 11, 12); // Middle
        ringAngle = CalculateFingerAngle(landmarks, 0, 13, 14, 15, 16); // Ring
        pinkyAngle = CalculateFingerAngle(landmarks, 0, 17, 18, 19, 20); // Pinky

        // Calculate hand rotation/movement
        handAngle = CalculateHandRotation(landmarks);
    }

    private float CalculateFingerAngle(List<LandmarkData> landmarks, int palmIdx, int mcpIdx, int pipIdx, int dipIdx, int tipIdx)
    {
        // Get positions
        Vector3 palm = GetLandmarkPosition(landmarks[palmIdx]);
        Vector3 mcp = GetLandmarkPosition(landmarks[mcpIdx]);
        Vector3 pip = GetLandmarkPosition(landmarks[pipIdx]);
        Vector3 dip = GetLandmarkPosition(landmarks[dipIdx]);
        Vector3 tip = GetLandmarkPosition(landmarks[tipIdx]);

        // Calculate vectors
        Vector3 mcpToPip = pip - mcp;
        Vector3 pipToDip = dip - pip;
        Vector3 dipToTip = tip - dip;

        // Calculate angle at PIP joint (main finger joint)
        float angle = Vector3.Angle(mcpToPip, pipToDip);

        // Normalize to 0-179 degrees
        angle = Mathf.Clamp(angle, 0f, 179f);

        return angle;
    }

    private float CalculateHandRotation(List<LandmarkData> landmarks)
    {
        // Get wrist and middle finger MCP to determine hand orientation
        Vector3 wrist = GetLandmarkPosition(landmarks[0]);
        Vector3 middleMCP = GetLandmarkPosition(landmarks[9]);

        // Calculate hand direction vector
        Vector3 handDirection = middleMCP - wrist;

        // Calculate rotation angle (simplified - you can make this more sophisticated)
        float rotation = Mathf.Atan2(handDirection.x, handDirection.z) * Mathf.Rad2Deg;

        // Normalize to 0-179 degrees
        rotation = Mathf.Clamp((rotation + 180f) / 2f, 0f, 179f);

        return rotation;
    }

    private Vector3 GetLandmarkPosition(LandmarkData landmark)
    {
        return new Vector3(
            landmark.position[0],
            landmark.position[1],
            landmark.position[2]
        );
    }

    private void SendServoAngles()
    {
        if (!isConnected || serialPort == null || !serialPort.IsOpen)
            return;

        // Format: "T:thumb,I:index,M:middle,R:ring,P:pinky,H:hand\n"
        string data = string.Format("T:{0:F0},I:{1:F0},M:{2:F0},R:{3:F0},P:{4:F0},H:{5:F0}\n",
            thumbAngle, indexAngle, middleAngle, ringAngle, pinkyAngle, handAngle);

        try
        {
            serialPort.Write(data);
            Debug.Log($"[ArduinoHandController] Sent: {data.Trim()}");
        }
        catch (Exception e)
        {
            Debug.LogError($"[ArduinoHandController] Error sending data: {e.Message}");
        }
    }

    void OnDestroy()
    {
        DisconnectArduino();
    }

    void OnApplicationQuit()
    {
        DisconnectArduino();
    }
}

// Add this method to HandTrackingReceiver.cs to expose hand data
public partial class HandTrackingReceiver
{
    public MultiHandData GetCurrentMultiHandData()
    {
        return currentMultiHandData;
    }
}
