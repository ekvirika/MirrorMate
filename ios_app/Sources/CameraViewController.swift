import UIKit
import AVFoundation

class CameraViewController: UIViewController {
    private let captureSession = AVCaptureSession()
    private var previewLayer: AVCaptureVideoPreviewLayer?
    private let webSocketManager = WebSocketManager()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        // Configure camera session in the background
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.setupCamera()
        }
    }
    
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        // Start capture session on background thread
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.captureSession.startRunning()
        }
    }
    
    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        // Stop capture session on background thread
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.captureSession.stopRunning()
        }
    }
    
    private func setupCamera() {
        // Configure camera on background thread
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            
            // Set up capture session
            self.captureSession.sessionPreset = .medium
            
            guard let captureDevice = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front),
                  let input = try? AVCaptureDeviceInput(device: captureDevice) else {
                return
            }
            
            // Add input to session
            if self.captureSession.canAddInput(input) {
                self.captureSession.addInput(input)
            }
            
            // Setup video output
            let videoOutput = AVCaptureVideoDataOutput()
            videoOutput.setSampleBufferDelegate(self, queue: DispatchQueue(label: "videoQueue"))
            if self.captureSession.canAddOutput(videoOutput) {
                self.captureSession.addOutput(videoOutput)
            }
            
            // Configure preview layer on main thread
            DispatchQueue.main.async {
                // Setup preview layer
                self.previewLayer = AVCaptureVideoPreviewLayer(session: self.captureSession)
                self.previewLayer?.videoGravity = .resizeAspectFill
                if let previewLayer = self.previewLayer {
                    self.view.layer.addSublayer(previewLayer)
                    previewLayer.frame = self.view.bounds
                }
            }
        }
    }
    
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        previewLayer?.frame = view.bounds
    }
}

extension CameraViewController: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let imageBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        let ciImage = CIImage(cvPixelBuffer: imageBuffer)
        let context = CIContext()
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else { return }
        
        let image = UIImage(cgImage: cgImage)
        if let imageData = image.jpegData(compressionQuality: 0.5) {
            webSocketManager.sendFrame(imageData)
        }
    }
}