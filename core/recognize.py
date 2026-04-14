"""
core/recognize.py
Real-time recognition engine.
Runs face detection + identification on each webcam frame and
triggers attendance logging when a known face is confirmed.
"""

import cv2
import numpy as np
from typing import Callable, Optional

from config.settings import (
    CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS,
    FACE_TOLERANCE, UNKNOWN_LABEL,
)
from models.face_model import load_encodings, identify_faces_in_frame
from core.attendance import record_attendance
from utils.face_utils import draw_face_box, draw_status_banner
from utils.helpers import log_info, log_warning


class RecognitionEngine:
    """
    Stateful recognition engine.
    The GUI creates one instance, calls start(), then polls next_frame()
    in a QTimer loop, and calls stop() on close.

    Callbacks:
      on_recognized(result_dict)  — called every time a known face triggers attendance
      on_frame(annotated_frame)   — called with every annotated BGR frame for display
      on_error(message)           — called on camera or model errors
    """

    def __init__(
        self,
        on_recognized: Optional[Callable] = None,
        on_frame:      Optional[Callable] = None,
        on_error:      Optional[Callable] = None,
    ):
        self.on_recognized = on_recognized or (lambda r: None)
        self.on_frame      = on_frame      or (lambda f: None)
        self.on_error      = on_error      or (lambda m: None)

        self._cap:          Optional[cv2.VideoCapture] = None
        self._known_data:   dict = {"encodings": [], "user_ids": [], "names": []}
        self._running:      bool = False
        self._status_text:  str  = "Initialising…"

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def load_model(self) -> bool:
        """Load face encodings from disk. Must be called before start()."""
        self._known_data = load_encodings()
        if not self._known_data["encodings"]:
            log_warning("No encodings loaded — train the model first.")
            return False
        log_info(f"Recognition engine: {len(self._known_data['encodings'])} encodings loaded.")
        return True

    def reload_model(self) -> bool:
        """Hot-reload encodings without restarting the camera."""
        return self.load_model()

    def start(self) -> bool:
        """Open the camera and begin recognition."""
        self._cap = cv2.VideoCapture(CAMERA_INDEX)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS,          CAMERA_FPS)

        if not self._cap.isOpened():
            self.on_error("Could not open camera. Check CAMERA_INDEX in settings.")
            return False

        self._running      = True
        self._status_text  = "Scanning…"
        log_info("Recognition engine started.")
        return True

    def stop(self) -> None:
        """Release camera resources."""
        self._running = False
        if self._cap and self._cap.isOpened():
            self._cap.release()
        log_info("Recognition engine stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Frame Processing ───────────────────────────────────────────────────────

    def next_frame(self) -> Optional[np.ndarray]:
        """
        Read the next camera frame, run face recognition, annotate, and
        fire callbacks. Returns the annotated BGR frame (or None on failure).

        Call this method from a QTimer (e.g., every 33 ms = 30 fps).
        """
        if not self._running or self._cap is None:
            return None

        ret, frame = self._cap.read()
        if not ret:
            self.on_error("Camera read failed.")
            return None

        frame = self._process(frame)
        self.on_frame(frame)
        return frame

    def _process(self, frame: np.ndarray) -> np.ndarray:
        """Run recognition on a frame and annotate it. Returns annotated frame."""
        if not self._known_data["encodings"]:
            draw_status_banner(frame, "No model loaded — please train first.", (30, 30, 120))
            return frame

        results = identify_faces_in_frame(frame, self._known_data, FACE_TOLERANCE)

        for r in results:
            draw_face_box(
                frame,
                r["top"], r["right"], r["bottom"], r["left"],
                r["name"],
                known=r["known"],
            )
            if r["known"] and r["user_id"] is not None:
                result = record_attendance(r["user_id"], r["name"])
                if result["logged"]:
                    self.on_recognized(result)
                    self._status_text = f"{result['type']}: {r['name']}"

        draw_status_banner(frame, self._status_text)
        return frame

    # ── Statistics ─────────────────────────────────────────────────────────────

    @property
    def known_user_count(self) -> int:
        return len(set(self._known_data["user_ids"]))

    @property
    def encoding_count(self) -> int:
        return len(self._known_data["encodings"])
