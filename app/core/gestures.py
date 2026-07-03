"""Gesture and finger-state detection from MediaPipe hand landmarks."""

import math

# Landmark indices: (mcp, pip, dip, tip) per finger
FINGER_JOINTS = {
    "thumb":  (1, 2, 3, 4),
    "index":  (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring":   (13, 14, 15, 16),
    "pinky":  (17, 18, 19, 20),
}

WRIST = 0


def fingers_extended(lm):
    """Return {'index': bool, ...} for the four long fingers (tip above pip)."""
    p = lm.landmark
    return {
        "index":  p[8].y < p[6].y,
        "middle": p[12].y < p[10].y,
        "ring":   p[16].y < p[14].y,
        "pinky":  p[20].y < p[18].y,
    }


def detect_gesture(lm):
    """Classify rock / paper / scissors (or None)."""
    if lm is None:
        return None
    ext = fingers_extended(lm)
    count = sum(ext.values())
    if count == 0:
        return "rock"
    if count >= 4:
        return "paper"
    if count == 2 and ext["index"] and ext["middle"]:
        return "scissors"
    return None


def count_extended(lm):
    """How many fingers (including thumb) are held up, 0-5."""
    curls = finger_curls(lm)
    return sum(1 for c in curls.values() if c < 0.45)


def is_middle_finger(lm):
    """Middle finger up, everything else folded."""
    if lm is None:
        return False
    ext = fingers_extended(lm)
    return ext["middle"] and not ext["index"] and not ext["ring"] and not ext["pinky"]


def is_open_palm_close(lm, frame_h):
    """Open palm held large in frame (i.e. close to camera) - high-five pose."""
    if detect_gesture(lm) != "paper":
        return False
    p = lm.landmark
    hand_h = abs(p[12].y - p[0].y) * frame_h
    return hand_h > frame_h * 0.22


def hand_center(lm, w, h):
    xs = [p.x for p in lm.landmark]
    ys = [p.y for p in lm.landmark]
    return int(sum(xs) / len(xs) * w), int(sum(ys) / len(ys) * h)


def _dist(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def _thumb_curl(p):
    """
    Thumb curl from the distance between the thumb tip and the pinky base,
    normalized by palm size (wrist to middle MCP).

    The thumb folds by sweeping across the palm rather than bending its
    joints, so joint angles barely change - distance is far more reliable.
    Extended/spread thumb: reach ~1.1+; tucked across the palm: ~0.4.
    """
    palm = _dist(p[WRIST], p[9]) or 1e-9
    reach = _dist(p[4], p[17]) / palm
    curl = (1.15 - reach) / 0.7
    return max(0.0, min(1.0, curl))


def _angle_at(p_prev, p_mid, p_next):
    """Angle (radians) of the bend at p_mid, in 3D."""
    v1 = (p_prev.x - p_mid.x, p_prev.y - p_mid.y, p_prev.z - p_mid.z)
    v2 = (p_next.x - p_mid.x, p_next.y - p_mid.y, p_next.z - p_mid.z)
    n1 = math.sqrt(sum(c * c for c in v1)) or 1e-9
    n2 = math.sqrt(sum(c * c for c in v2)) or 1e-9
    dot = sum(a * b for a, b in zip(v1, v2)) / (n1 * n2)
    return math.acos(max(-1.0, min(1.0, dot)))


def finger_curls(lm):
    """
    Per-finger curl amount for live mirroring.

    Returns {'thumb': 0.0-1.0, ...} where 0 = straight, 1 = fully curled.
    Uses the interior joint angles: a straight finger has ~180deg joints
    (pi), a curled one much less.
    """
    p = lm.landmark
    curls = {"thumb": _thumb_curl(p)}
    for finger, (mcp, pip, dip, tip) in FINGER_JOINTS.items():
        if finger == "thumb":
            continue  # joint angles are useless for the thumb, handled above
        a1 = _angle_at(p[mcp], p[pip], p[dip])
        a2 = _angle_at(p[pip], p[dip], p[tip])
        avg = (a1 + a2) / 2  # pi = straight, smaller = curled
        curl = 1.0 - (avg / math.pi)
        # MediaPipe's depth noise makes bends read shallower than reality,
        # so saturate well before the geometric maximum: a real on-camera
        # fist lands around raw 0.30-0.35.
        curl = (curl - 0.04) / 0.28
        curls[finger] = max(0.0, min(1.0, curl))
    return curls
