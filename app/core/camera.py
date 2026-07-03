"""Cross-platform camera capture (macOS / Windows / Linux)."""

import platform

import cv2

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720


def open_camera(index=0):
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
        # Backend guess failed on this machine - fall back to the default.
        cap = cv2.VideoCapture(index)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap
