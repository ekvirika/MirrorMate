import UIKit
import AVFoundation

class WebSocketManager {
    private var webSocket: URLSessionWebSocketTask?
    private let serverURL = URL(string: "ws://192.168.15.137:8765/ios")!
    
    init() {
        connect()
    }
    
    private func connect() {
        print("Attempting to connect to: \(serverURL)")
        
        let session = URLSession(configuration: .default)
        webSocket = session.webSocketTask(with: serverURL)
        
        webSocket?.resume()
        
        // Add connection state handler
        DispatchQueue.global().async { [weak self] in
            guard let self = self else { return }
            do {
                try ping()
                print("Successfully connected to server")
                self.receiveMessage()
            } catch {
                print("Connection failed: \(error.localizedDescription)")
                // Try to reconnect after delay
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    self.connect()
                }
            }
        }
    }
    
    private func ping() throws {
        let semaphore = DispatchSemaphore(value: 0)
        var pingError: Error?
        
        webSocket?.sendPing { error in
            pingError = error
            semaphore.signal()
        }
        
        _ = semaphore.wait(timeout: .now() + 5)
        if let error = pingError {
            throw error
        }
    }
    
    func sendFrame(_ imageData: Data) {
        let base64String = imageData.base64EncodedString()
        let message = URLSessionWebSocketTask.Message.string(base64String)
        webSocket?.send(message) { error in
            if let error = error {
                print("Error sending frame: \(error)")
            }
        }
    }
    
    private func receiveMessage() {
        webSocket?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    print("Received: \(text)")
                case .data(let data):
                    print("Received data: \(data)")
                @unknown default:
                    break
                }
                self?.receiveMessage()
            case .failure(let error):
                print("Error receiving message: \(error)")
                // Try to reconnect
                DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                    self?.connect()
                }
            }
        }
    }
}