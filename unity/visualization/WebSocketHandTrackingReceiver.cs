using UnityEngine;
using WebSocketSharp;
using System;
using Newtonsoft.Json;

public class WebSocketHandTrackingReceiver : MonoBehaviour
{
    [Header("WebSocket Settings")]
    [SerializeField] private string serverUrl = "ws://localhost:8765/unity";
    [SerializeField] private bool connectOnStart = true;

    private WebSocket webSocket;
    private HandTrackingReceiver handTrackingReceiver;

    private void Start()
    {
        handTrackingReceiver = GetComponent<HandTrackingReceiver>();
        
        if (connectOnStart)
        {
            ConnectToServer();
        }
    }

    public void ConnectToServer()
    {
        webSocket = new WebSocket(serverUrl);

        webSocket.OnMessage += (sender, e) =>
        {
            // Parse the received JSON data
            try
            {
                var data = JsonConvert.DeserializeObject<dynamic>(e.Data);
                if (data.type == "hand_tracking")
                {
                    // Forward the landmarks data to the HandTrackingReceiver
                    handTrackingReceiver.ProcessHandData(data.landmarks.ToString());
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"Error processing message: {ex.Message}");
            }
        };

        webSocket.OnError += (sender, e) =>
        {
            Debug.LogError($"WebSocket Error: {e.Message}");
        };

        webSocket.OnClose += (sender, e) =>
        {
            Debug.Log("WebSocket connection closed");
        };

        webSocket.Connect();
        Debug.Log("Connecting to WebSocket server...");
    }

    private void OnDestroy()
    {
        if (webSocket != null)
        {
            webSocket.Close();
        }
    }
}