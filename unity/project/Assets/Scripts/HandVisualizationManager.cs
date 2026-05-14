using UnityEngine;
using WebSocketSharp;
using Newtonsoft.Json;
using System.Collections.Generic;

public class HandVisualizationManager : MonoBehaviour
{
    [Header("WebSocket Settings")]
    [SerializeField] private string serverUrl = "ws://localhost:8765/unity";
    
    [Header("Visualization Settings")]
    [SerializeField] private GameObject jointPrefab;
    [SerializeField] private GameObject bonePrefab;
    [SerializeField] private Material leftHandMaterial;
    [SerializeField] private Material rightHandMaterial;
    [SerializeField] private float jointScale = 0.01f;
    [SerializeField] private float depthScale = 1.0f;
    
    [Header("Camera Transform Settings")]
    [SerializeField] private float cameraAngle = 45f; // Angle of the camera from horizontal
    [SerializeField] private Vector3 cameraPosition = new Vector3(0, -0.5f, 0); // Camera position relative to hand space
    
    private WebSocket webSocket;
    private Dictionary<string, Dictionary<int, GameObject>> handJoints = new Dictionary<string, Dictionary<int, GameObject>>();
    private Dictionary<string, List<GameObject>> handBones = new Dictionary<string, List<GameObject>>();

    private void Start()
    {
        ConnectToServer();
    }

    private void ConnectToServer()
    {
        webSocket = new WebSocket(serverUrl);

        webSocket.OnMessage += (sender, e) =>
        {
            ProcessHandData(e.Data);
        };

        webSocket.OnOpen += (sender, e) =>
        {
            Debug.Log("Connected to server");
        };

        webSocket.OnError += (sender, e) =>
        {
            Debug.LogError($"WebSocket Error: {e.Message}");
        };

        webSocket.OnClose += (sender, e) =>
        {
            Debug.Log("Disconnected from server");
            // Attempt to reconnect after a delay
            Invoke("ConnectToServer", 5f);
        };

        webSocket.Connect();
    }

    private void ProcessHandData(string jsonData)
    {
        try
        {
            var data = JsonConvert.DeserializeObject<HandTrackingData>(jsonData);
            if (data.type == "hand_tracking")
            {
                foreach (var hand in data.landmarks)
                {
                    UpdateHandVisualization(hand);
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError($"Error processing hand data: {e.Message}");
        }
    }

    private void UpdateHandVisualization(HandData hand)
    {
        string handId = hand.hand_type;
        
        // Initialize dictionaries for this hand if they don't exist
        if (!handJoints.ContainsKey(handId))
        {
            handJoints[handId] = new Dictionary<int, GameObject>();
            handBones[handId] = new List<GameObject>();
        }

        // Process landmarks
        foreach (var landmark in hand.landmarks)
        {
            // Transform coordinates from camera space to world space
            Vector3 position = TransformPointFromCameraSpace(
                new Vector3(landmark.position[0], landmark.position[1], landmark.position[2])
            );

            // Create or update joint
            if (!handJoints[handId].ContainsKey(landmark.id))
            {
                GameObject joint = Instantiate(jointPrefab, position, Quaternion.identity, transform);
                joint.name = $"{handId}_Joint_{landmark.name}";
                joint.transform.localScale = Vector3.one * jointScale;
                
                // Set material based on hand type
                Renderer renderer = joint.GetComponent<Renderer>();
                if (renderer != null)
                {
                    renderer.material = hand.hand_type == "Left" ? leftHandMaterial : rightHandMaterial;
                }
                
                handJoints[handId][landmark.id] = joint;
            }
            else
            {
                handJoints[handId][landmark.id].transform.position = position;
            }
        }

        // Update bones
        UpdateHandBones(hand, handId);
    }

    private Vector3 TransformPointFromCameraSpace(Vector3 point)
    {
        // Create rotation matrix for camera angle
        Quaternion cameraRotation = Quaternion.Euler(-cameraAngle, 0, 0);
        
        // Apply depth scaling to Z coordinate
        point.z *= depthScale;
        
        // Transform point
        Vector3 transformedPoint = cameraRotation * point;
        transformedPoint += cameraPosition;
        
        return transformedPoint;
    }

    private void UpdateHandBones(HandData hand, string handId)
    {
        // Clear existing bones
        foreach (var bone in handBones[handId])
        {
            Destroy(bone);
        }
        handBones[handId].Clear();

        // Define finger connections
        int[][] connections = new int[][]
        {
            // Thumb
            new int[] { 0, 1 }, new int[] { 1, 2 }, new int[] { 2, 3 }, new int[] { 3, 4 },
            // Index finger
            new int[] { 0, 5 }, new int[] { 5, 6 }, new int[] { 6, 7 }, new int[] { 7, 8 },
            // Middle finger
            new int[] { 0, 9 }, new int[] { 9, 10 }, new int[] { 10, 11 }, new int[] { 11, 12 },
            // Ring finger
            new int[] { 0, 13 }, new int[] { 13, 14 }, new int[] { 14, 15 }, new int[] { 15, 16 },
            // Pinky
            new int[] { 0, 17 }, new int[] { 17, 18 }, new int[] { 18, 19 }, new int[] { 19, 20 },
            // Palm
            new int[] { 5, 9 }, new int[] { 9, 13 }, new int[] { 13, 17 }
        };

        // Create bones
        foreach (var connection in connections)
        {
            if (handJoints[handId].ContainsKey(connection[0]) && handJoints[handId].ContainsKey(connection[1]))
            {
                CreateBone(
                    handJoints[handId][connection[0]].transform.position,
                    handJoints[handId][connection[1]].transform.position,
                    handId,
                    hand.hand_type == "Left" ? leftHandMaterial : rightHandMaterial
                );
            }
        }
    }

    private void CreateBone(Vector3 start, Vector3 end, string handId, Material material)
    {
        Vector3 direction = end - start;
        Vector3 center = (start + end) / 2;
        float length = direction.magnitude;

        GameObject bone = Instantiate(bonePrefab, center, Quaternion.identity, transform);
        bone.name = $"{handId}_Bone";
        bone.transform.up = direction.normalized;
        bone.transform.localScale = new Vector3(jointScale, length, jointScale);

        Renderer renderer = bone.GetComponent<Renderer>();
        if (renderer != null)
        {
            renderer.material = material;
        }

        handBones[handId].Add(bone);
    }

    private void OnDestroy()
    {
        if (webSocket != null)
        {
            webSocket.Close();
        }
    }
}

[System.Serializable]
public class HandTrackingData
{
    public string type;
    public List<HandData> landmarks;
}

[System.Serializable]
public class HandData
{
    public string hand_type;
    public List<LandmarkData> landmarks;
}

[System.Serializable]
public class LandmarkData
{
    public int id;
    public string name;
    public float[] position;
}