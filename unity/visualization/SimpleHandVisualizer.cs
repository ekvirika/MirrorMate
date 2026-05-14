using System;
using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using Newtonsoft.Json;

public class SimpleHandVisualizer : MonoBehaviour
{
    [Header("Network Settings")]
    [SerializeField] private int listenPort = 5065;
    [SerializeField] private bool startReceivingOnStart = true;
    [SerializeField] private bool showDebugInfo = true;

    [Header("Hand Visualization")]
    [SerializeField] private GameObject jointPrefab;
    [SerializeField] private Material leftHandMaterial;
    [SerializeField] private Material rightHandMaterial;
    [SerializeField] private Material forearmMaterial;
    [SerializeField] private float handScale = 0.01f;
    [SerializeField] private float depthScale = 10f;
    [SerializeField] private bool showForearm = true;
    [SerializeField] private bool showConnections = true;
    [SerializeField] private float lineWidth = 0.005f;
    [SerializeField] private bool smoothMotion = true;
    [SerializeField] private float smoothingSpeed = 10f;

    // UDP client
    private UdpClient udpClient;
    private Thread receiveThread;
    private bool isReceiving = false;

    // Hand data
    private MultiHandData currentMultiHandData;
    private Dictionary<string, Dictionary<int, GameObject>> handJoints = new Dictionary<string, Dictionary<int, GameObject>>();
    private Dictionary<string, Dictionary<string, LineRenderer>> handLines = new Dictionary<string, Dictionary<string, LineRenderer>>();
    
    // Connections to draw
    private List<int[]> fingerConnections = new List<int[]>
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
        new int[] { 0, 17 }, new int[] { 17, 18 }, new int[] { 18, 19 }, new int[] { 19, 20 }
    };
    
    private List<int[]> palmConnections = new List<int[]>
    {
        new int[] { 0, 5 }, new int[] { 5, 9 }, new int[] { 9, 13 }, new int[] { 13, 17 }, new int[] { 17, 0 }
    };
    
    private List<int[]> forearmConnections = new List<int[]>
    {
        new int[] { 0, 23 }, new int[] { 23, 22 }, new int[] { 22, 24 }, new int[] { 24, 21 }
    };
    
    // Lock for thread safety
    private readonly object dataLock = new object();
    
    // Debug info
    private string debugText = "Waiting for hand tracking data...";

    private void Start()
    {
        if (startReceivingOnStart)
        {
            StartReceiving();
        }
    }

    public void StartReceiving()
    {
        if (isReceiving)
        {
            Debug.Log("[HandVisualizer] Already receiving data");
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

            Debug.Log($"[HandVisualizer] Started receiving on port {listenPort}");
            
            // Display connection instructions
            Debug.Log("[HandVisualizer] Connection Instructions:");
            Debug.Log($"1. Run the Python script 'unity_exporter.py' on your computer");
            Debug.Log($"2. Make sure the script is configured to send data to port {listenPort}");
            
            // Try to get the local IP address to help with configuration
            try {
                string hostName = Dns.GetHostName();
                IPAddress[] addresses = Dns.GetHostAddresses(hostName);
                Debug.Log("[HandVisualizer] Available IP addresses on this machine:");
                foreach (IPAddress address in addresses)
                {
                    if (address.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork) // IPv4 only
                    {
                        Debug.Log($"- {address}");
                    }
                }
            } catch (Exception ipEx) {
                Debug.LogWarning($"[HandVisualizer] Could not determine local IP: {ipEx.Message}");
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"[HandVisualizer] Error starting UDP receiver: {e.Message}");
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

        Debug.Log("[HandVisualizer] Stopped receiving");
    }

    private void ReceiveData()
    {
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);
        int packetCount = 0;
        long lastLogTimeMs = 0;

        UnityEngine.Debug.Log($"[HandVisualizer] Started listening for UDP packets on port {listenPort}");

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
                    UnityEngine.Debug.Log($"[HandVisualizer] Received {packetCount} packets from {remoteEndPoint.Address}:{remoteEndPoint.Port}");
                    lastLogTimeMs = currentTimeMs;
                }

                // Try to parse as multi-hand data
                try
                {
                    MultiHandData multiHandData = JsonConvert.DeserializeObject<MultiHandData>(json);
                    
                    // Add current system time to the data for timing reference
                    multiHandData.receivedTimeMs = currentTimeMs;

                    // Update hand data (thread-safe)
                    lock (dataLock)
                    {
                        currentMultiHandData = multiHandData;
                    }
                }
                catch (Exception jsonEx)
                {
                    UnityEngine.Debug.LogError($"[HandVisualizer] Error parsing JSON: {jsonEx.Message}");
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
                    UnityEngine.Debug.LogError($"[HandVisualizer] Error receiving data: {e.Message}");
                    // Short sleep to avoid flooding logs if there's a persistent error
                    System.Threading.Thread.Sleep(1000);
                }
            }
        }

        UnityEngine.Debug.Log($"[HandVisualizer] Stopped listening on port {listenPort}");
    }

    private void Update()
    {
        // Update visualization based on received data
        lock (dataLock)
        {
            if (currentMultiHandData != null)
            {
                UpdateHandVisualizations(currentMultiHandData);
                
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
        }
    }
    
    private void OnGUI()
    {
        if (showDebugInfo)
        {
            GUI.Label(new Rect(10, 10, 300, 100), debugText);
        }
    }

    private void UpdateHandVisualizations(MultiHandData multiHandData)
    {
        // Track active hand IDs
        HashSet<string> activeHandIds = new HashSet<string>();
        
        // Process each hand
        foreach (var hand in multiHandData.hands)
        {
            string handId = hand.hand_type;
            activeHandIds.Add(handId);
            
            // Get or create hand container
            if (!handJoints.ContainsKey(handId))
            {
                // Create new dictionaries for this hand
                handJoints[handId] = new Dictionary<int, GameObject>();
                handLines[handId] = new Dictionary<string, LineRenderer>();
                
                // Create a container GameObject for this hand
                GameObject handContainer = new GameObject(handId + "Hand");
                handContainer.transform.SetParent(transform);
                
                // Store the container in the first joint slot (we'll never use ID -1 for a real joint)
                GameObject containerObj = new GameObject("Container");
                containerObj.transform.SetParent(handContainer.transform);
                handJoints[handId][-1] = handContainer;
            }
            
            // Choose material based on hand type
            Material handMaterial = hand.hand_type == "Left" ? leftHandMaterial : rightHandMaterial;
            
            // Create or update joints
            foreach (var landmark in hand.landmarks)
            {
                int id = landmark.id;
                
                // Skip forearm landmarks if not showing forearm
                if (!showForearm && id >= 21)
                    continue;
                
                // Calculate position in Unity space
                Vector3 position = new Vector3(
                    landmark.position[0] * handScale,
                    -landmark.position[1] * handScale, // Flip Y axis (screen coordinates to Unity)
                    landmark.position[2] * handScale * depthScale // Scale Z for better depth visualization
                );
                
                // Create or update joint
                if (!handJoints[handId].ContainsKey(id))
                {
                    // Create joint
                    GameObject joint = Instantiate(jointPrefab, position, Quaternion.identity, handJoints[handId][-1].transform);
                    joint.name = landmark.name;
                    
                    // Scale based on joint type
                    float scale = 1.0f;
                    if (id == 0) // Wrist
                        scale = 1.5f;
                    else if (id == 21) // Elbow
                        scale = 1.8f;
                    else if (id >= 22) // Other forearm points
                        scale = 1.2f;
                    
                    joint.transform.localScale = Vector3.one * scale;
                    
                    // Set material
                    Renderer renderer = joint.GetComponent<Renderer>();
                    if (renderer != null)
                    {
                        if (id >= 21 && forearmMaterial != null) // Forearm
                            renderer.material = forearmMaterial;
                        else
                            renderer.material = handMaterial;
                    }
                    
                    handJoints[handId][id] = joint;
                }
                else if (smoothMotion)
                {
                    // Smooth motion
                    handJoints[handId][id].transform.position = Vector3.Lerp(
                        handJoints[handId][id].transform.position,
                        position,
                        Time.deltaTime * smoothingSpeed
                    );
                }
                else
                {
                    // Immediate position update
                    handJoints[handId][id].transform.position = position;
                }
            }
            
            // Update connections
            if (showConnections)
            {
                UpdateConnections(handId, hand.hand_type, fingerConnections, "finger", handMaterial);
                UpdateConnections(handId, hand.hand_type, palmConnections, "palm", handMaterial);
                
                if (showForearm)
                {
                    UpdateConnections(handId, hand.hand_type, forearmConnections, "forearm", 
                        forearmMaterial != null ? forearmMaterial : handMaterial);
                }
            }
        }
        
        // Remove any hands that are no longer active
        List<string> handsToRemove = new List<string>();
        foreach (var handId in handJoints.Keys)
        {
            if (!activeHandIds.Contains(handId))
            {
                handsToRemove.Add(handId);
            }
        }
        
        foreach (var handId in handsToRemove)
        {
            // Destroy the hand container and all its children
            if (handJoints[handId].ContainsKey(-1))
            {
                Destroy(handJoints[handId][-1]);
            }
            
            // Remove from dictionaries
            handJoints.Remove(handId);
            handLines.Remove(handId);
        }
    }
    
    private void UpdateConnections(string handId, string handType, List<int[]> connections, string connectionType, Material material)
    {
        foreach (var connection in connections)
        {
            string connectionKey = $"{connectionType}_{connection[0]}_{connection[1]}";
            
            if (handJoints[handId].ContainsKey(connection[0]) && handJoints[handId].ContainsKey(connection[1]))
            {
                Vector3 startPos = handJoints[handId][connection[0]].transform.position;
                Vector3 endPos = handJoints[handId][connection[1]].transform.position;
                
                // Create or update line renderer
                if (!handLines[handId].ContainsKey(connectionKey))
                {
                    // Create line renderer
                    GameObject lineObj = new GameObject(connectionKey);
                    lineObj.transform.SetParent(handJoints[handId][-1].transform);
                    
                    LineRenderer line = lineObj.AddComponent<LineRenderer>();
                    line.positionCount = 2;
                    line.startWidth = lineWidth;
                    line.endWidth = lineWidth;
                    line.material = material;
                    
                    // Set color based on hand type
                    if (handType == "Left")
                        line.startColor = line.endColor = Color.blue;
                    else
                        line.startColor = line.endColor = Color.red;
                    
                    handLines[handId][connectionKey] = line;
                }
                
                // Update line positions
                handLines[handId][connectionKey].SetPosition(0, startPos);
                handLines[handId][connectionKey].SetPosition(1, endPos);
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
    }

    [Serializable]
    public class LandmarkData
    {
        public int id;
        public string name;
        public float[] position;
    }
}
