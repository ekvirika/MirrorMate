"""
Plain Hand Mirror
Opens the webcam, mirrors the frame, and overlays live MediaPipe hand
landmarks. No Arduino, Unity, or network output - just the tracking itself.

Works unmodified on macOS and Windows: the camera backend is picked
automatically based on the host OS (AVFoundation on macOS, DirectShow on
Windows, default backend everywhere else).
"""

import platform
import time

import cv2
import mediapipe as mp

CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720


def open_camera(index=CAMERA_INDEX):
    """Open the webcam with the capture backend appropriate for this OS."""
    system = platform.system()
    if system == "Darwin":
        backend = cv2.CAP_AVFOUNDATION
    elif system == "Windows":
        backend = cv2.CAP_DSHOW
    else:
        backend = cv2.CAP_ANY

    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        # Backend guess didn't work on this machine - fall back to the
        # platform default rather than failing outright.
        cap = cv2.VideoCapture(index)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


def main():
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_styles = mp.solutions.drawing_styles

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = open_camera()
    if not cap.isOpened():
        print(f"Could not open camera {CAMERA_INDEX}")
        return

    print("Plain Hand Mirror - press Q to quit")

    prev_time = time.time()

    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("Failed to read from webcam")
                break

            # Mirror the frame so movement matches what the user sees.
            frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            if results.multi_hand_landmarks:
                for landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style(),
                    )

            now = time.time()
            fps = 1 / (now - prev_time) if now > prev_time else 0
            prev_time = now

            cv2.putText(frame, f"FPS: {int(fps)}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            cv2.imshow("Plain Hand Mirror", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()


if __name__ == "__main__":
    main()
