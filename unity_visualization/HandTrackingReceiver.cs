using System;
using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using Newtonsoft.Json;

public class HandTrackingReceiver : MonoBehaviour
{
    [Header("Network Settings")]
    [SerializeField] private int listenPort = 5065;
    [SerializeField] private bool startReceivingOnStart = true;
    [SerializeField] private bool showDebugInfo = true;

    [Header("Hand Visualization")]
    [SerializeField] private GameObject handModelPrefab;
    [SerializeField] private GameObject jointPrefab;
    [SerializeField] private GameObject bonePrefab;
    [SerializeField] private Material leftHandMaterial;
    [SerializeField] private Material rightHandMaterial;
    [SerializeField] private Material forearmMaterial;
    [SerializeField] private float jointScale = 0.01f;
    [SerializeField] private float handScale = 0.01f;
    [SerializeField] private float boneWidth = 0.005f;
    [SerializeField] private bool enhancedVisualization = true;
    [SerializeField] private bool showForearm = true;

    // UDP client
    private UdpClient udpClient;
    private Thread receiveThread;
    private bool isReceiving = false;

    // Hand data
    private MultiHandData currentMultiHandData;
    private Dictionary<string, Dictionary<int, GameObject>> handJointObjects = new Dictionary<string, Dictionary<int, GameObject>>();
    private Dictionary<string, List<GameObject>> handBoneObjects = new Dictionary<string, List<GameObject>>();
    private Dictionary<string, List<int[]>> connections = new Dictionary<string, List<int[]>>();
    
    // For backward compatibility
    private HandData currentHandData;
    private Dictionary<int, GameObject> jointObjects = new Dictionary<int, GameObject>();

    // Lock for thread safety
    private readonly object dataLock = new object();

    private void Start()
    {
        // Define hand connections (which joints should be connected)
        InitializeHandConnections();

        if (startReceivingOnStart)
        {
            StartReceiving();
        }
    }

    private void InitializeHandConnections()
    {
        // Define connections between landmarks for visualization
        // Format: pairs of landmark indices that should be connected by lines
        List<int[]> fingerConnections = new List<int[]>
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

        connections["fingers"] = fingerConnections;
        
        // Forearm connections
        List<int[]> forearmConnections = new List<int[]>
        {
            // Wrist to forearm points
            new int[] { 0, 23 }, // Wrist to quarter point
            new int[] { 23, 22 }, // Quarter to midpoint
            new int[] { 22, 24 }, // Midpoint to three-quarter point
            new int[] { 24, 21 } // Three-quarter to elbow
        };
        
        connections["forearm"] = forearmConnections;
    }

    public void StartReceiving()
    {
        if (isReceiving)
        {
            Debug.Log("[HandTrackingReceiver] Already receiving data");
            return;
        }

        try
        {
            // Initialize UDP client
            udpClient = new UdpClient(listenPort);
            isReceiving = true;

            // Start receive thread
            receiveThread = new Thread(new ThreadStart(ReceiveData));
            receiveThread.IsBackground = true;
            receiveThread.Start();

            Debug.Log($"[HandTrackingReceiver] Started receiving on port {listenPort}");
            
            // Display connection instructions
            Debug.Log("[HandTrackingReceiver] Connection Instructions:");
            Debug.Log($"1. Run the Python script 'unity_exporter.py' on your computer");
            Debug.Log($"2. Make sure the script is configured to send data to port {listenPort}");
            Debug.Log($"3. If running on a different machine, use this machine's IP address");
            
            // Try to get the local IP address to help with configuration
            try {
                string hostName = Dns.GetHostName();
                IPAddress[] addresses = Dns.GetHostAddresses(hostName);
                Debug.Log("[HandTrackingReceiver] Available IP addresses on this machine:");
                foreach (IPAddress address in addresses)
                {
                    if (address.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork) // IPv4 only
                    {
                        Debug.Log($"- {address}");
                    }
                }
            } catch (Exception ipEx) {
                Debug.LogWarning($"[HandTrackingReceiver] Could not determine local IP: {ipEx.Message}");
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"[HandTrackingReceiver] Error starting UDP receiver: {e.Message}");
        }
    }

    public void StopReceiving()
    {
        if (!isReceiving)
            return;

        isReceiving = false;

        if (udpClient != null)
        {
            udpClient.Close();
            udpClient = null;
        }

        if (receiveThread != null)
        {
            receiveThread.Abort();
            receiveThread = null;
        }

        Debug.Log("Stopped receiving");
    }

    private void ReceiveData()
    {
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);
        int packetCount = 0;
        long lastLogTimeMs = 0;

        // Use UnityEngine.Debug.Log with a string to avoid thread issues
        UnityEngine.Debug.Log($"[HandTrackingReceiver] Started listening for UDP packets on port {listenPort}");

        while (isReceiving)
        {
            try
            {
                // Receive data
                byte[] data = udpClient.Receive(ref remoteEndPoint);
                string json = Encoding.UTF8.GetString(data);
                packetCount++;

                // Log reception periodically (using DateTime instead of Time.time for thread safety)
                long currentTimeMs = System.DateTime.Now.Ticks / TimeSpan.TicksPerMillisecond;
                if (showDebugInfo && currentTimeMs - lastLogTimeMs > 5000) // 5 seconds
                {
                    UnityEngine.Debug.Log($"[HandTrackingReceiver] Received {packetCount} packets from {remoteEndPoint.Address}:{remoteEndPoint.Port}");
                    lastLogTimeMs = currentTimeMs;
                }

                // Try to parse as multi-hand data first
                try
                {
                    MultiHandData multiHandData = JsonConvert.DeserializeObject<MultiHandData>(json);
                    
                    // Add current system time to the data for timing reference
                    multiHandData.receivedTimeMs = currentTimeMs;

                    // Update hand data (thread-safe)
                    lock (dataLock)
                    {
                        currentMultiHandData = multiHandData;
                        currentHandData = null; // Clear single-hand data
                    }
                }
                catch
                {
                    // Fall back to single-hand data format
                    try
                    {
                        HandData handData = JsonConvert.DeserializeObject<HandData>(json);
                        
                        // Add current system time to the data for timing reference
                        handData.receivedTimeMs = currentTimeMs;

                        // Update hand data (thread-safe)
                        lock (dataLock)
                        {
                            currentHandData = handData;
                            currentMultiHandData = null; // Clear multi-hand data
                        }
                    }
                    catch (Exception jsonEx)
                    {
                        UnityEngine.Debug.LogError($"[HandTrackingReceiver] Error parsing JSON: {jsonEx.Message}");
                    }
                }
            }
            catch (ThreadAbortException)
            {
                // Thread is being aborted, exit gracefully
                break;
            }
            catch (Exception e)
            {
                if (isReceiving) // Only log if we're still supposed to be receiving
                {
                    UnityEngine.Debug.LogError($"[HandTrackingReceiver] Error receiving data: {e.Message}");
                    // Short sleep to avoid flooding logs if there's a persistent error
                    System.Threading.Thread.Sleep(1000);
                }
            }
        }

        UnityEngine.Debug.Log($"[HandTrackingReceiver] Stopped listening on port {listenPort}");
    }

    private void Update()
    {
        // Update visualization based on received data
        lock (dataLock)
        {
            if (currentMultiHandData != null)
            {
                // Multi-hand data available
                UpdateMultiHandVisualization(currentMultiHandData);
                
                // Display debug info on screen if enabled
                if (showDebugInfo)
                {
                    int handCount = currentMultiHandData.hands.Count;
                    int totalLandmarks = 0;
                    foreach (var hand in currentMultiHandData.hands)
                    {
                        totalLandmarks += hand.landmarks.Count;
                    }
                    
                    // Calculate time since last update using the receivedTimeMs we added
                    long currentTimeMs = System.DateTime.Now.Ticks / TimeSpan.TicksPerMillisecond;
                    float timeSinceUpdateMs = (float)(currentTimeMs - currentMultiHandData.receivedTimeMs) / 1000f;
                    
                    // Schedule GUI updates for OnGUI
                    debugText = $"Hands: {handCount}\nTotal Landmarks: {totalLandmarks}\nLast update: {timeSinceUpdateMs:F2}s ago\nReceiving on port: {listenPort}";
                }
            }
            else if (currentHandData != null)
            {
                // Single-hand data available (legacy format)
                UpdateHandVisualization(currentHandData);
                
                // Display debug info on screen if enabled
                if (showDebugInfo)
                {
                    string handType = currentHandData.hand_type;
                    int landmarkCount = currentHandData.landmarks.Count;
                    
                    // Calculate time since last update using the receivedTimeMs we added
                    long currentTimeMs = System.DateTime.Now.Ticks / TimeSpan.TicksPerMillisecond;
                    float timeSinceUpdateMs = (float)(currentTimeMs - currentHandData.receivedTimeMs) / 1000f;
                    
                    // Schedule GUI updates for OnGUI
                    debugText = $"Hand: {handType}\nLandmarks: {landmarkCount}\nLast update: {timeSinceUpdateMs:F2}s ago\nReceiving on port: {listenPort}";
                }
            }
        }
    }
    
    private string debugText = "Waiting for hand tracking data...";
    
    private void OnGUI()
    {
        if (showDebugInfo)
        {
            GUI.Label(new Rect(10, 10, 300, 100), debugText);
        }
    }

    private void UpdateMultiHandVisualization(MultiHandData multiHandData)
    {
        // Process each hand
        HashSet<string> activeHandIds = new HashSet<string>();
        
        foreach (var hand in multiHandData.hands)
        {
            string handId = hand.hand_type + System.Guid.NewGuid().ToString().Substring(0, 8);
            activeHandIds.Add(handId);
            
            // Choose material based on hand type
            Material handMaterial = hand.hand_type == "Left" ? leftHandMaterial : rightHandMaterial;
            
            // Make sure we have a dictionary for this hand
            if (!handJointObjects.ContainsKey(handId))
            {
                handJointObjects[handId] = new Dictionary<int, GameObject>();
                handBoneObjects[handId] = new List<GameObject>();
            }
            
            // Create or update joint objects
            foreach (var landmark in hand.landmarks)
            {
                int id = landmark.id;
                Vector3 position = new Vector3(
                    landmark.position[0] * handScale,
                    -landmark.position[1] * handScale, // Flip Y axis (screen coordinates to Unity)
                    landmark.position[2] * handScale * 10 // Scale Z for better depth visualization
                );
                
                // Determine material based on landmark type
                Material landmarkMaterial = handMaterial;
                if (id >= 21) // Forearm landmarks
                {
                    landmarkMaterial = forearmMaterial != null ? forearmMaterial : handMaterial;
                }
                
                // Create or update joint object
                if (!handJointObjects[handId].ContainsKey(id))
                {
                    GameObject jointObj = Instantiate(jointPrefab, position, Quaternion.identity, transform);
                    jointObj.name = $"{hand.hand_type}_Joint_{landmark.name}";
                    
                    // Scale joint based on its type
                    float scale = jointScale;
                    if (id == 0) // Wrist is larger
                        scale *= 1.5f;
                    else if (id == 21) // Elbow is larger
                        scale *= 1.8f;
                    else if (id >= 22) // Other forearm points are medium
                        scale *= 1.2f;
                    
                    jointObj.transform.localScale = Vector3.one * scale;
                    
                    // Set material
                    Renderer renderer = jointObj.GetComponent<Renderer>();
                    if (renderer != null)
                    {
                        renderer.material = landmarkMaterial;
                    }
                    
                    handJointObjects[handId][id] = jointObj;
                }
                else
                {
                    handJointObjects[handId][id].transform.position = position;
                }
            }
            
            // Create bone connections if enhanced visualization is enabled
            if (enhancedVisualization)
            {
                // Clear previous bones
                foreach (var bone in handBoneObjects[handId])
                {
                    Destroy(bone);
                }
                handBoneObjects[handId].Clear();
                
                // Create new bones
                foreach (var connectionGroup in connections)
                {
                    // Skip forearm connections if not showing forearm
                    if (!showForearm && connectionGroup.Key == "forearm")
                        continue;
                        
                    foreach (var connection in connectionGroup.Value)
                    {
                        if (handJointObjects[handId].ContainsKey(connection[0]) && handJointObjects[handId].ContainsKey(connection[1]))
                        {
                            Vector3 startPos = handJointObjects[handId][connection[0]].transform.position;
                            Vector3 endPos = handJointObjects[handId][connection[1]].transform.position;
                            
                            // Create bone object
                            GameObject bone = CreateBone(startPos, endPos, hand.hand_type, connectionGroup.Key == "forearm");
                            handBoneObjects[handId].Add(bone);
                        }
                    }
                }
            }
            else
            {
                // Just draw debug lines
                foreach (var connectionGroup in connections)
                {
                    // Skip forearm connections if not showing forearm
                    if (!showForearm && connectionGroup.Key == "forearm")
                        continue;
                        
                    foreach (var connection in connectionGroup.Value)
                    {
                        if (handJointObjects[handId].ContainsKey(connection[0]) && handJointObjects[handId].ContainsKey(connection[1]))
                        {
                            Debug.DrawLine(
                                handJointObjects[handId][connection[0]].transform.position,
                                handJointObjects[handId][connection[1]].transform.position,
                                hand.hand_type == "Left" ? Color.blue : Color.red,
                                Time.deltaTime
                            );
                        }
                    }
                }
            }
        }
        
        // Remove any hands that are no longer active
        List<string> handsToRemove = new List<string>();
        foreach (var handId in handJointObjects.Keys)
        {
            if (!activeHandIds.Contains(handId))
            {
                handsToRemove.Add(handId);
            }
        }
        
        foreach (var handId in handsToRemove)
        {
            // Destroy all joint objects
            foreach (var joint in handJointObjects[handId].Values)
            {
                Destroy(joint);
            }
            
            // Destroy all bone objects
            foreach (var bone in handBoneObjects[handId])
            {
                Destroy(bone);
            }
            
            // Remove from dictionaries
            handJointObjects.Remove(handId);
            handBoneObjects.Remove(handId);
        }
    }
    
    private GameObject CreateBone(Vector3 startPos, Vector3 endPos, string handType, bool isForearm)
    {
        // Calculate bone position and rotation
        Vector3 direction = endPos - startPos;
        Vector3 midpoint = (startPos + endPos) / 2;
        float length = direction.magnitude;
        
        // Create bone object
        GameObject bone = Instantiate(bonePrefab != null ? bonePrefab : jointPrefab, midpoint, Quaternion.identity, transform);
        bone.name = $"{handType}_Bone";
        
        // Scale and rotate to match the connection
        if (bonePrefab != null)
        {
            // If using a custom bone prefab
            bone.transform.up = direction.normalized;
            bone.transform.localScale = new Vector3(boneWidth, length / 2, boneWidth);
        }
        else
        {
            // If using joint prefab as fallback
            bone.transform.localScale = new Vector3(boneWidth, length, boneWidth);
        }
        
        // Set material
        Renderer renderer = bone.GetComponent<Renderer>();
        if (renderer != null)
        {
            if (isForearm && forearmMaterial != null)
            {
                renderer.material = forearmMaterial;
            }
            else
            {
                renderer.material = handType == "Left" ? leftHandMaterial : rightHandMaterial;
            }
        }
        
        return bone;
    }
    
    private void UpdateHandVisualization(HandData handData)
    {
        // Legacy method for backward compatibility
        // Choose material based on hand type
        Material handMaterial = handData.hand_type == "Left" ? leftHandMaterial : rightHandMaterial;

        // Create or update joint objects
        foreach (var landmark in handData.landmarks)
        {
            int id = landmark.id;
            Vector3 position = new Vector3(
                landmark.position[0] * handScale,
                -landmark.position[1] * handScale, // Flip Y axis (screen coordinates to Unity)
                landmark.position[2] * handScale * 10 // Scale Z for better depth visualization
            );

            // Create or update joint object
            if (!jointObjects.ContainsKey(id))
            {
                GameObject jointObj = Instantiate(jointPrefab, position, Quaternion.identity, transform);
                jointObj.name = $"Joint_{landmark.name}";
                jointObj.transform.localScale = Vector3.one * jointScale;

                // Set material
                Renderer renderer = jointObj.GetComponent<Renderer>();
                if (renderer != null)
                {
                    renderer.material = handMaterial;
                }

                jointObjects[id] = jointObj;
            }
            else
            {
                jointObjects[id].transform.position = position;
            }
        }

        // Draw connections between joints
        foreach (var connectionGroup in connections)
        {
            foreach (var connection in connectionGroup.Value)
            {
                if (jointObjects.ContainsKey(connection[0]) && jointObjects.ContainsKey(connection[1]))
                {
                    Debug.DrawLine(
                        jointObjects[connection[0]].transform.position,
                        jointObjects[connection[1]].transform.position,
                        handData.hand_type == "Left" ? Color.blue : Color.red,
                        Time.deltaTime
                    );
                }
            }
        }
    }

    private void OnDestroy()
    {
        StopReceiving();
    }

    private void OnApplicationQuit()
    {
        StopReceiving();
    }

    // Data structures for JSON deserialization
    [Serializable]
    public class MultiHandData
    {
        public double timestamp;
        public List<HandData> hands;
        
        // Not serialized, used internally for timing
        [JsonIgnore]
        public long receivedTimeMs;
    }
    
    [Serializable]
    public class HandData
    {
        public double timestamp;
        public string hand_type;
        public List<LandmarkData> landmarks;
        
        // Not serialized, used internally for timing
        [JsonIgnore]
        public long receivedTimeMs;
    }

    [Serializable]
    public class LandmarkData
    {
        public int id;
        public string name;
        public float[] position;
    }
}
