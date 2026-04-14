"""
core/capture.py
Webcam image capture for building the face dataset during user registration.
Can be used standalone (CLI) or called from the GUI registration window.
"""

import os
import cv2

from config.settings import (
    DATASET_DIR, CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT,
    IMAGES_PER_USER, CAPTURE_DELAY_MS,
)
from utils.helpers import log_info, log_warning, ensure_dir, count_images_in_dir
from utils.face_utils import draw_status_banner, is_blurry, is_too_dark
import face_recognition
from utils.face_utils import bgr_to_rgb


def get_user_dataset_dir(user_id: int) -> str:
    """Return (and create) the dataset directory for a given user ID."""
    path = os.path.join(DATASET_DIR, str(user_id))
    ensure_dir(path)
    return path


def save_face_image(frame: "cv2.Mat", user_id: int, index: int) -> str:
    """
    Save a single BGR frame as a JPEG into the user's dataset folder.
    Returns the saved file path.
    """
    user_dir = get_user_dataset_dir(user_id)
    filename = f"img_{index:04d}.jpg"
    filepath = os.path.join(user_dir, filename)
    cv2.imwrite(filepath, frame)
    return filepath


def capture_images_cli(user_id: int, target: int = IMAGES_PER_USER) -> int:
    """
    Open the webcam and interactively capture `target` face images.
    Designed for CLI / debug use. The GUI uses frame-by-frame callbacks instead.

    Controls:
      SPACE — capture a frame manually
      Q     — quit early

    Returns the number of images successfully saved.
    """
    user_dir = get_user_dataset_dir(user_id)
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    if not cap.isOpened():
        log_warning("Cannot open camera.")
        return 0

    saved      = count_images_in_dir(user_dir)
    start_idx  = saved  # Continue numbering from where we left off
    log_info(f"Starting capture for user {user_id}. Target: {target} images.")

    while saved - start_idx < target:
        ret, frame = cap.read()
        if not ret:
            break

        count = saved - start_idx
        banner = f"Captured {count}/{target} — SPACE to capture, Q to quit"
        draw_status_banner(frame, banner)
        cv2.imshow(f"Capture — User {user_id}", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" "):
            if is_blurry(frame):
                draw_status_banner(frame, "Too blurry — try again", (0, 60, 180))
                cv2.imshow(f"Capture — User {user_id}", frame)
                cv2.waitKey(400)
                continue
            if is_too_dark(frame):
                draw_status_banner(frame, "Too dark — improve lighting", (0, 60, 180))
                cv2.imshow(f"Capture — User {user_id}", frame)
                cv2.waitKey(400)
                continue

            filepath = save_face_image(frame, user_id, saved)
            saved += 1
            log_info(f"Saved: {filepath}")

    cap.release()
    cv2.destroyAllWindows()
    total = saved - start_idx
    log_info(f"Capture complete. {total} images saved for user {user_id}.")
    return total


# ─── Frame-by-frame API (used by GUI) ─────────────────────────────────────────

class CaptureSession:
    """
    Stateful capture helper used by the GUI registration window.
    The GUI calls feed_frame() on every new webcam frame; this class
    decides whether to auto-save and signals when the target is reached.
    """

    def __init__(self, user_id: int, target: int = IMAGES_PER_USER):
        self.user_id  = user_id
        self.target   = target
        self._saved   = count_images_in_dir(get_user_dataset_dir(user_id))
        self._start   = self._saved
        self._timer   = 0   # ms since last save (for auto-capture throttle)

    @property
    def captured(self) -> int:
        return self._saved - self._start

    @property
    def is_complete(self) -> bool:
        return self.captured >= self.target

    def feed_frame(self, frame: "cv2.Mat", elapsed_ms: int) -> dict:
        """
        Process one frame. Auto-saves if a face is detected and enough time
        has passed since the last save.

        Returns a status dict:
        {
          "saved":    bool,       — True if this frame was saved
          "captured": int,        — total captured so far this session
          "target":   int,
          "complete": bool,
          "has_face": bool,
        }
        """
        self._timer += elapsed_ms
        status = {
            "saved":    False,
            "captured": self.captured,
            "target":   self.target,
            "complete": self.is_complete,
            "has_face": False,
        }

        if self.is_complete:
            return status

        # Detect face presence quickly
        rgb = bgr_to_rgb(frame)
        locations = face_recognition.face_locations(rgb, model="hog")
        has_face = len(locations) > 0
        status["has_face"] = has_face

        if has_face and self._timer >= CAPTURE_DELAY_MS:
            if not is_blurry(frame) and not is_too_dark(frame):
                save_face_image(frame, self.user_id, self._saved)
                self._saved += 1
                self._timer = 0
                status["saved"]    = True
                status["captured"] = self.captured
                status["complete"] = self.is_complete

        return status
