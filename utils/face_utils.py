"""
utils/face_utils.py
Face-image preprocessing helpers used by capture, train, and recognize modules.
All functions operate on NumPy arrays (OpenCV BGR or RGB format).
"""

import cv2
import numpy as np
from config.settings import (
    CAMERA_WIDTH, CAMERA_HEIGHT, FRAME_SCALE,
    BBOX_COLOR_KNOWN, BBOX_COLOR_UNKNOWN, BBOX_THICKNESS
)


# ─── Frame Conversion ──────────────────────────────────────────────────────────

def bgr_to_rgb(frame: np.ndarray) -> np.ndarray:
    """Convert OpenCV BGR frame to RGB (required by face_recognition library)."""
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def rgb_to_bgr(frame: np.ndarray) -> np.ndarray:
    """Convert RGB back to BGR for display via OpenCV."""
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def scale_frame(frame: np.ndarray, scale: float = FRAME_SCALE) -> np.ndarray:
    """
    Downscale frame for faster recognition processing.
    Returns a resized copy; original is untouched.
    """
    w = int(frame.shape[1] * scale)
    h = int(frame.shape[0] * scale)
    return cv2.resize(frame, (w, h))


def resize_frame(frame: np.ndarray, width: int = CAMERA_WIDTH, height: int = CAMERA_HEIGHT) -> np.ndarray:
    """Resize a frame to the standard display resolution."""
    return cv2.resize(frame, (width, height))


# ─── Face Location Scaling ─────────────────────────────────────────────────────

def scale_face_locations(face_locations: list, scale: float = FRAME_SCALE) -> list:
    """
    Scale face bounding-box coordinates back up from the downscaled frame
    to match the original frame dimensions.

    face_recognition returns locations as (top, right, bottom, left).
    """
    factor = int(1 / scale)
    return [
        (top * factor, right * factor, bottom * factor, left * factor)
        for top, right, bottom, left in face_locations
    ]


# ─── Drawing ───────────────────────────────────────────────────────────────────

def draw_face_box(
    frame: np.ndarray,
    top: int, right: int, bottom: int, left: int,
    name: str,
    known: bool = True,
) -> np.ndarray:
    """
    Draw a labelled bounding box around a detected face.
    Green for known users, red/blue for unknown.
    Returns the frame with annotations drawn (in-place).
    """
    color = BBOX_COLOR_KNOWN if known else BBOX_COLOR_UNKNOWN

    # Bounding box
    cv2.rectangle(frame, (left, top), (right, bottom), color, BBOX_THICKNESS)

    # Label background pill
    label_y = bottom + 20
    cv2.rectangle(frame, (left, bottom), (right, label_y), color, cv2.FILLED)

    # Label text
    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    cv2.putText(
        frame, name,
        (left + 4, bottom + 14),
        font, font_scale,
        (255, 255, 255), 1, cv2.LINE_AA,
    )
    return frame


def draw_status_banner(frame: np.ndarray, text: str, color: tuple = (30, 30, 30)) -> np.ndarray:
    """
    Overlay a status text banner at the bottom of the frame.
    Useful for showing 'Scanning…', 'Entry logged', etc.
    """
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 32), (w, h), color, cv2.FILLED)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.putText(
        frame, text,
        (10, h - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55,
        (255, 255, 255), 1, cv2.LINE_AA,
    )
    return frame


# ─── Image Quality Checks ──────────────────────────────────────────────────────

def is_blurry(frame: np.ndarray, threshold: float = 80.0) -> bool:
    """
    Return True if the image is too blurry to use for training.
    Uses the variance of the Laplacian as a sharpness metric.
    Lower = blurrier. Threshold of ~80 works well for typical webcam captures.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var() < threshold


def is_too_dark(frame: np.ndarray, threshold: float = 40.0) -> bool:
    """
    Return True if the image is too dark for reliable face detection.
    Checks the mean brightness of the grayscale frame.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return gray.mean() < threshold


def frame_to_jpeg_bytes(frame: np.ndarray, quality: int = 90) -> bytes:
    """Encode an OpenCV BGR frame to JPEG bytes (for Qt display or saving)."""
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes()
