"""
core/camera_manager.py
Detect available cameras and allow switching between them at runtime.
"""

import cv2
from config.admin_settings import AVAILABLE_CAMERAS, DEFAULT_CAMERA
from utils.helpers import log_info, log_warning


def detect_available_cameras(max_check: int = 5) -> list[dict]:
    """
    Probe camera indices 0..max_check-1 and return a list of available ones.
    Each entry: { "index": int, "label": str }
    This takes ~1-2 seconds as each camera is briefly opened.
    """
    available = []
    for idx in range(max_check):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)  # CAP_DSHOW faster on Windows
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append({
                    "index": idx,
                    "label": f"Camera {idx}" + (" (Default)" if idx == DEFAULT_CAMERA else ""),
                })
                log_info(f"Camera detected at index {idx}")
            cap.release()
    if not available:
        log_warning("No cameras detected.")
    return available


class CameraManager:
    """
    Manages the active camera for the recognition engine.
    Allows hot-switching between cameras without restarting the engine.
    """

    def __init__(self):
        self._current_index = DEFAULT_CAMERA
        self._cap: cv2.VideoCapture = None
        self._available: list[dict] = []

    def scan(self) -> list[dict]:
        """Scan for available cameras. Returns list of camera dicts."""
        self._available = detect_available_cameras()
        return self._available

    @property
    def available(self) -> list[dict]:
        return self._available

    @property
    def current_index(self) -> int:
        return self._current_index

    def open(self, index: int = None) -> bool:
        """Open a camera by index. Closes current camera first."""
        if index is None:
            index = self._current_index
        self.close()
        self._cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        from config.settings import CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS,          CAMERA_FPS)
        if self._cap.isOpened():
            self._current_index = index
            log_info(f"Camera {index} opened.")
            return True
        log_warning(f"Failed to open camera {index}.")
        return False

    def switch(self, index: int) -> bool:
        """Switch to a different camera index."""
        if index == self._current_index and self._cap and self._cap.isOpened():
            return True
        return self.open(index)

    def read(self):
        """Read next frame. Returns (ret, frame)."""
        if self._cap and self._cap.isOpened():
            return self._cap.read()
        return False, None

    def close(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def get_labels(self) -> list[str]:
        """Return labels for the camera selector dropdown."""
        if not self._available:
            return [f"Camera {DEFAULT_CAMERA}"]
        return [c["label"] for c in self._available]

    def get_indices(self) -> list[int]:
        return [c["index"] for c in self._available]
