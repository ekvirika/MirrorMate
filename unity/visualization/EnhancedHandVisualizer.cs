using System;
using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using Newtonsoft.Json;

public class EnhancedHandVisualizer : MonoBehaviour
{
    [Header("Network Settings")]
    [SerializeField] private int listenPort = 5065;
    [SerializeField] private bool startReceivingOnStart = true;
    [SerializeField] private bool showDebugInfo = true;

    [Header("Hand Visualization")]
    [SerializeField] private GameObject fingerJointPrefab;
    [SerializeField] private GameObject wristJointPrefab;
    [SerializeField] private GameObject elbowJointPrefab;
    [SerializeField] private GameObject fingerBonePrefab;
    [SerializeField] private GameObject palmPrefab;
    [SerializeField] private Material leftHandMaterial;
    [SerializeField] private Material rightHandMaterial;
    [SerializeField] private Material forearmMaterial;
    [SerializeField] private float handScale = 0.01f;
    [SerializeField] private float depthScale = 10f;
    [SerializeField] private bool showForearm = true;
    [SerializeField] private bool smoothMotion = true;
    [SerializeField] private float smoothingSpeed = 15f;

    [Header("Visual Effects")]
    [SerializeField] private bool useParticleEffects = false;
    [SerializeField] private GameObject fingerTipEffectPrefab;
    [SerializeField] private float effectIntensity = 1f;
    [SerializeField] private Color leftHandColor = new Color(0.2f, 0.4f, 1f);
    [SerializeField] private Color rightHandColor = new Color(1f, 0.3f, 0.3f);

    // UDP client
    private UdpClient udpClient;
    private Thread receiveThread;
    private bool isReceiving = false;

    // Hand data
    private MultiHandData currentMultiHandData;
    private Dictionary<string, HandVisualizer> handVisualizers = new Dictionary<string, HandVisualizer>();
    
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
            
            // Get or create hand visualizer
            if (!handVisualizers.ContainsKey(handId))
            {
                // Create new hand visualizer
                GameObject handObj = new GameObject($"{hand.hand_type}Hand");
                handObj.transform.SetParent(transform);
                
                HandVisualizer visualizer = handObj.AddComponent<HandVisualizer>();
                visualizer.Initialize(
                    fingerJointPrefab,
                    wristJointPrefab,
                    elbowJointPrefab,
                    fingerBonePrefab,
                    palmPrefab,
                    hand.hand_type == "Left" ? leftHandMaterial : rightHandMaterial,
                    forearmMaterial,
                    hand.hand_type == "Left" ? leftHandColor : rightHandColor,
                    handScale,
                    depthScale,
                    smoothMotion,
                    smoothingSpeed,
                    useParticleEffects ? fingerTipEffectPrefab : null,
                    effectIntensity,
                    showForearm
                );
                
                handVisualizers.Add(handId, visualizer);
            }
            
            // Update hand visualizer with new data
            handVisualizers[handId].UpdateVisualization(hand.landmarks);
        }
        
        // Remove any hands that are no longer active
        List<string> handsToRemove = new List<string>();
        foreach (var handId in handVisualizers.Keys)
        {
            if (!activeHandIds.Contains(handId))
            {
                handsToRemove.Add(handId);
            }
        }
        
        foreach (var handId in handsToRemove)
        {
            Destroy(handVisualizers[handId].gameObject);
            handVisualizers.Remove(handId);
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

// Separate class for visualizing a single hand
public class HandVisualizer : MonoBehaviour
{
    // Prefabs and materials
    private GameObject fingerJointPrefab;
    private GameObject wristJointPrefab;
    private GameObject elbowJointPrefab;
    private GameObject fingerBonePrefab;
    private GameObject palmPrefab;
    private Material handMaterial;
    private Material forearmMaterial;
    private Color handColor;
    
    // Visualization parameters
    private float handScale;
    private float depthScale;
    private bool smoothMotion;
    private float smoothingSpeed;
    private GameObject fingerTipEffectPrefab;
    private float effectIntensity;
    private bool showForearm;
    
    // Visualization objects
    private Dictionary<int, GameObject> joints = new Dictionary<int, GameObject>();
    private Dictionary<int, GameObject> bones = new Dictionary<int, GameObject>();
    private GameObject palmObject;
    private Dictionary<int, GameObject> effects = new Dictionary<int, GameObject>();
    
    // Target positions for smooth motion
    private Dictionary<int, Vector3> targetPositions = new Dictionary<int, Vector3>();
    
    // Finger connections
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
    
    // Palm connections
    private List<int[]> palmConnections = new List<int[]>
    {
        new int[] { 0, 5 }, new int[] { 5, 9 }, new int[] { 9, 13 }, new int[] { 13, 17 }, new int[] { 17, 0 }
    };
    
    // Forearm connections
    private List<int[]> forearmConnections = new List<int[]>
    {
        new int[] { 0, 23 }, new int[] { 23, 22 }, new int[] { 22, 24 }, new int[] { 24, 21 }
    };
    
    // Finger tip IDs
    private int[] fingerTipIds = { 4, 8, 12, 16, 20 };
    
    public void Initialize(
        GameObject fingerJointPrefab,
        GameObject wristJointPrefab,
        GameObject elbowJointPrefab,
        GameObject fingerBonePrefab,
        GameObject palmPrefab,
        Material handMaterial,
        Material forearmMaterial,
        Color handColor,
        float handScale,
        float depthScale,
        bool smoothMotion,
        float smoothingSpeed,
        GameObject fingerTipEffectPrefab,
        float effectIntensity,
        bool showForearm)
    {
        this.fingerJointPrefab = fingerJointPrefab;
        this.wristJointPrefab = wristJointPrefab;
        this.elbowJointPrefab = elbowJointPrefab;
        this.fingerBonePrefab = fingerBonePrefab;
        this.palmPrefab = palmPrefab;
        this.handMaterial = handMaterial;
        this.forearmMaterial = forearmMaterial;
        this.handColor = handColor;
        this.handScale = handScale;
        this.depthScale = depthScale;
        this.smoothMotion = smoothMotion;
        this.smoothingSpeed = smoothingSpeed;
        this.fingerTipEffectPrefab = fingerTipEffectPrefab;
        this.effectIntensity = effectIntensity;
        this.showForearm = showForearm;
    }
    
    public void UpdateVisualization(List<LandmarkData> landmarks)
    {
        // Process each landmark
        foreach (var landmark in landmarks)
        {
            int id = landmark.id;
            
            // Calculate position in Unity space
            Vector3 position = new Vector3(
                landmark.position[0] * handScale,
                -landmark.position[1] * handScale, // Flip Y axis (screen coordinates to Unity)
                landmark.position[2] * handScale * depthScale // Scale Z for better depth visualization
            );
            
            // Store target position for smooth motion
            if (smoothMotion)
            {
                targetPositions[id] = position;
            }
            
            // Create or update joint
            if (!joints.ContainsKey(id))
            {
                // Determine which prefab to use
                GameObject prefab = fingerJointPrefab;
                if (id == 0) // Wrist
                    prefab = wristJointPrefab != null ? wristJointPrefab : fingerJointPrefab;
                else if (id == 21) // Elbow
                    prefab = elbowJointPrefab != null ? elbowJointPrefab : fingerJointPrefab;
                
                // Create joint
                GameObject joint = Instantiate(prefab, smoothMotion ? transform.position : position, Quaternion.identity, transform);
                joint.name = $"Joint_{landmark.name}";
                
                // Set material
                Renderer renderer = joint.GetComponent<Renderer>();
                if (renderer != null)
                {
                    if (id >= 21 && forearmMaterial != null) // Forearm
                        renderer.material = forearmMaterial;
                    else
                        renderer.material = handMaterial;
                    
                    // Set color if using standard shader
                    if (renderer.material.HasProperty("_Color"))
                    {
                        if (id >= 21 && forearmMaterial != null)
                            renderer.material.color = handColor * 0.8f; // Slightly darker for forearm
                        else
                            renderer.material.color = handColor;
                    }
                }
                
                joints[id] = joint;
                
                // Create effect for finger tips
                if (fingerTipEffectPrefab != null && System.Array.IndexOf(fingerTipIds, id) >= 0)
                {
                    GameObject effect = Instantiate(fingerTipEffectPrefab, position, Quaternion.identity, joint.transform);
                    effect.name = $"Effect_{landmark.name}";
                    
                    // Set effect color if it has a particle system
                    ParticleSystem ps = effect.GetComponent<ParticleSystem>();
                    if (ps != null)
                    {
                        var main = ps.main;
                        main.startColor = handColor;
                        
                        // Scale effect size
                        main.startSize = main.startSize.constant * effectIntensity;
                    }
                    
                    effects[id] = effect;
                }
            }
            else if (!smoothMotion)
            {
                // Update joint position immediately
                joints[id].transform.position = position;
            }
        }
        
        // Create or update bones and palm
        UpdateBones(landmarks);
        
        // Hide forearm if not showing
        if (!showForearm)
        {
            foreach (var landmark in landmarks)
            {
                if (landmark.id >= 21 && joints.ContainsKey(landmark.id))
                {
                    joints[landmark.id].SetActive(false);
                }
            }
            
            // Hide forearm bones
            foreach (var connection in forearmConnections)
            {
                int boneId = connection[0] * 100 + connection[1];
                if (bones.ContainsKey(boneId))
                {
                    bones[boneId].SetActive(false);
                }
            }
        }
    }
    
    private void UpdateBones(List<LandmarkData> landmarks)
    {
        // Create dictionary for quick landmark lookup
        Dictionary<int, Vector3> landmarkPositions = new Dictionary<int, Vector3>();
        foreach (var landmark in landmarks)
        {
            Vector3 position = new Vector3(
                landmark.position[0] * handScale,
                -landmark.position[1] * handScale,
                landmark.position[2] * handScale * depthScale
            );
            landmarkPositions[landmark.id] = position;
        }
        
        // Update finger bones
        UpdateConnectionBones(fingerConnections, landmarkPositions, false);
        
        // Update forearm bones if showing
        if (showForearm)
        {
            UpdateConnectionBones(forearmConnections, landmarkPositions, true);
        }
        
        // Update palm
        if (landmarkPositions.ContainsKey(0) && landmarkPositions.ContainsKey(5) && 
            landmarkPositions.ContainsKey(9) && landmarkPositions.ContainsKey(13) && 
            landmarkPositions.ContainsKey(17))
        {
            Vector3 wrist = landmarkPositions[0];
            Vector3 indexBase = landmarkPositions[5];
            Vector3 middleBase = landmarkPositions[9];
            Vector3 ringBase = landmarkPositions[13];
            Vector3 pinkyBase = landmarkPositions[17];
            
            // Calculate palm center
            Vector3 palmCenter = (wrist + indexBase + middleBase + ringBase + pinkyBase) / 5f;
            
            if (palmObject == null && palmPrefab != null)
            {
                // Create palm object
                palmObject = Instantiate(palmPrefab, palmCenter, Quaternion.identity, transform);
                palmObject.name = "Palm";
                
                // Set material
                Renderer renderer = palmObject.GetComponent<Renderer>();
                if (renderer != null)
                {
                    renderer.material = handMaterial;
                    
                    // Set color if using standard shader
                    if (renderer.material.HasProperty("_Color"))
                    {
                        renderer.material.color = handColor;
                    }
                }
            }
            else if (palmObject != null)
            {
                // Calculate palm orientation
                Vector3 palmNormal = Vector3.Cross(indexBase - wrist, pinkyBase - wrist).normalized;
                Vector3 palmForward = (middleBase - wrist).normalized;
                
                // Calculate palm size
                float palmWidth = Vector3.Distance(indexBase, pinkyBase);
                float palmHeight = Vector3.Distance(wrist, middleBase);
                
                // Update palm transform
                if (smoothMotion)
                {
                    palmObject.transform.position = Vector3.Lerp(palmObject.transform.position, palmCenter, Time.deltaTime * smoothingSpeed);
                    palmObject.transform.rotation = Quaternion.Slerp(
                        palmObject.transform.rotation,
                        Quaternion.LookRotation(palmForward, palmNormal),
                        Time.deltaTime * smoothingSpeed
                    );
                    palmObject.transform.localScale = Vector3.Lerp(
                        palmObject.transform.localScale,
                        new Vector3(palmWidth, 0.01f, palmHeight),
                        Time.deltaTime * smoothingSpeed
                    );
                }
                else
                {
                    palmObject.transform.position = palmCenter;
                    palmObject.transform.rotation = Quaternion.LookRotation(palmForward, palmNormal);
                    palmObject.transform.localScale = new Vector3(palmWidth, 0.01f, palmHeight);
                }
            }
        }
    }
    
    private void UpdateConnectionBones(List<int[]> connections, Dictionary<int, Vector3> landmarkPositions, bool isForearm)
    {
        foreach (var connection in connections)
        {
            if (landmarkPositions.ContainsKey(connection[0]) && landmarkPositions.ContainsKey(connection[1]))
            {
                Vector3 startPos = landmarkPositions[connection[0]];
                Vector3 endPos = landmarkPositions[connection[1]];
                
                // Create unique ID for this bone
                int boneId = connection[0] * 100 + connection[1];
                
                if (!bones.ContainsKey(boneId))
                {
                    // Create bone
                    GameObject bone = Instantiate(fingerBonePrefab, transform.position, Quaternion.identity, transform);
                    bone.name = $"Bone_{connection[0]}_{connection[1]}";
                    
                    // Set material
                    Renderer renderer = bone.GetComponent<Renderer>();
                    if (renderer != null)
                    {
                        if (isForearm && forearmMaterial != null)
                            renderer.material = forearmMaterial;
                        else
                            renderer.material = handMaterial;
                        
                        // Set color if using standard shader
                        if (renderer.material.HasProperty("_Color"))
                        {
                            if (isForearm)
                                renderer.material.color = handColor * 0.8f; // Slightly darker for forearm
                            else
                                renderer.material.color = handColor;
                        }
                    }
                    
                    bones[boneId] = bone;
                }
                
                // Update bone transform
                GameObject boneObj = bones[boneId];
                Vector3 direction = endPos - startPos;
                Vector3 midpoint = (startPos + endPos) / 2;
                float length = direction.magnitude;
                
                if (smoothMotion)
                {
                    boneObj.transform.position = Vector3.Lerp(boneObj.transform.position, midpoint, Time.deltaTime * smoothingSpeed);
                    boneObj.transform.rotation = Quaternion.Slerp(
                        boneObj.transform.rotation,
                        Quaternion.FromToRotation(Vector3.up, direction),
                        Time.deltaTime * smoothingSpeed
                    );
                    boneObj.transform.localScale = Vector3.Lerp(
                        boneObj.transform.localScale,
                        new Vector3(0.005f, length / 2, 0.005f),
                        Time.deltaTime * smoothingSpeed
                    );
                }
                else
                {
                    boneObj.transform.position = midpoint;
                    boneObj.transform.rotation = Quaternion.FromToRotation(Vector3.up, direction);
                    boneObj.transform.localScale = new Vector3(0.005f, length / 2, 0.005f);
                }
            }
        }
    }
    
    private void Update()
    {
        // Update joint positions with smooth motion
        if (smoothMotion)
        {
            foreach (var kvp in targetPositions)
            {
                int id = kvp.Key;
                Vector3 targetPos = kvp.Value;
                
                if (joints.ContainsKey(id))
                {
                    joints[id].transform.position = Vector3.Lerp(
                        joints[id].transform.position,
                        targetPos,
                        Time.deltaTime * smoothingSpeed
                    );
                }
            }
        }
    }
}
