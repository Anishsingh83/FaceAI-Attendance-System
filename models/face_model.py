"""
models/face_model.py
Core ML logic — encoding generation, pkl persistence, and face matching.
Uses the `face_recognition` library (dlib under the hood).
"""

import os
import pickle
from typing import Optional

import cv2
import numpy as np
import face_recognition

from config.settings import (
    ENCODINGS_PKL, FACE_TOLERANCE, UNKNOWN_LABEL, FRAME_SCALE
)
from utils.helpers import log_info, log_error, log_warning
from utils.face_utils import bgr_to_rgb, scale_frame, scale_face_locations


# ─── Encoding Store ────────────────────────────────────────────────────────────
# Structure stored in the .pkl file:
# {
#   "encodings": [np.ndarray, ...],   — one 128-d vector per image
#   "user_ids":  [int, ...],          — user ID for each encoding
#   "names":     [str, ...],          — user name for each encoding
# }

def load_encodings() -> dict:
    """
    Load the face encodings from disk.
    Returns an empty structure if the file does not exist.
    """
    if not os.path.exists(ENCODINGS_PKL):
        return {"encodings": [], "user_ids": [], "names": []}
    try:
        with open(ENCODINGS_PKL, "rb") as f:
            data = pickle.load(f)
        log_info(f"Loaded {len(data['encodings'])} face encodings from disk.")
        return data
    except Exception as e:
        log_error(f"Failed to load encodings: {e}")
        return {"encodings": [], "user_ids": [], "names": []}


def save_encodings(data: dict) -> bool:
    """Persist the encodings dict to disk. Returns True on success."""
    try:
        os.makedirs(os.path.dirname(ENCODINGS_PKL), exist_ok=True)
        with open(ENCODINGS_PKL, "wb") as f:
            pickle.dump(data, f)
        log_info(f"Saved {len(data['encodings'])} face encodings to disk.")
        return True
    except Exception as e:
        log_error(f"Failed to save encodings: {e}")
        return False


def encodings_exist() -> bool:
    return os.path.exists(ENCODINGS_PKL)


# ─── Single Image Encoding ─────────────────────────────────────────────────────

def encode_face_from_image(image_path: str) -> Optional[np.ndarray]:
    """
    Load an image file and return the 128-d face encoding.
    Returns None if no face is detected or the file cannot be read.
    """
    img = cv2.imread(image_path)
    if img is None:
        log_warning(f"Cannot read image: {image_path}")
        return None

    rgb = bgr_to_rgb(img)
    locations = face_recognition.face_locations(rgb, model="hog")
    if not locations:
        log_warning(f"No face detected in: {image_path}")
        return None

    # Use only the first (most prominent) face
    encodings = face_recognition.face_encodings(rgb, [locations[0]])
    if not encodings:
        return None
    return encodings[0]


def encode_face_from_frame(frame: np.ndarray) -> Optional[np.ndarray]:
    """
    Encode a face from a live BGR OpenCV frame.
    Returns the 128-d encoding or None.
    """
    rgb = bgr_to_rgb(frame)
    locations = face_recognition.face_locations(rgb, model="hog")
    if not locations:
        return None
    encodings = face_recognition.face_encodings(rgb, [locations[0]])
    return encodings[0] if encodings else None


# ─── Batch Training ────────────────────────────────────────────────────────────

def build_encodings_from_dataset(dataset_dir: str, progress_callback=None) -> dict:
    """
    Walk the dataset directory structure (dataset/{user_id}/*.jpg)
    and build the full encodings dict.

    progress_callback(current, total, user_id, filename) is called for each image.
    """
    data = {"encodings": [], "user_ids": [], "names": []}

    # Collect all (user_id, image_path) pairs
    tasks = []
    for uid_dir in sorted(os.listdir(dataset_dir)):
        uid_path = os.path.join(dataset_dir, uid_dir)
        if not os.path.isdir(uid_path) or not uid_dir.isdigit():
            continue
        user_id = int(uid_dir)
        for fname in os.listdir(uid_path):
            if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                tasks.append((user_id, os.path.join(uid_path, fname)))

    total = len(tasks)
    log_info(f"Training on {total} images across {len(set(t[0] for t in tasks))} users.")

    # Load user names from DB (avoid circular imports — read CSV directly)
    import csv
    from config.settings import USERS_CSV
    name_map: dict[int, str] = {}
    if os.path.exists(USERS_CSV):
        with open(USERS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    name_map[int(row["user_id"])] = row["name"]
                except (ValueError, KeyError):
                    pass

    for idx, (user_id, img_path) in enumerate(tasks):
        fname = os.path.basename(img_path)
        if progress_callback:
            progress_callback(idx + 1, total, user_id, fname)

        enc = encode_face_from_image(img_path)
        if enc is not None:
            data["encodings"].append(enc)
            data["user_ids"].append(user_id)
            data["names"].append(name_map.get(user_id, f"User_{user_id}"))

    log_info(f"Training complete. {len(data['encodings'])} encodings generated.")
    return data


# ─── Recognition ───────────────────────────────────────────────────────────────

def identify_faces_in_frame(
    frame: np.ndarray,
    known_data: dict,
    tolerance: float = FACE_TOLERANCE,
) -> list[dict]:
    """
    Detect and identify all faces in a BGR OpenCV frame.

    Returns a list of dicts, one per detected face:
    {
        "user_id": int | None,
        "name":    str,
        "known":   bool,
        "top": int, "right": int, "bottom": int, "left": int,
        "distance": float,   — lower = more confident
    }
    """
    results = []
    if not known_data["encodings"]:
        return results

    # Work on a smaller frame for speed
    small = scale_frame(frame, FRAME_SCALE)
    rgb_small = bgr_to_rgb(small)

    locations_small = face_recognition.face_locations(rgb_small, model="hog")
    if not locations_small:
        return results

    encodings_in_frame = face_recognition.face_encodings(rgb_small, locations_small)
    locations_full = scale_face_locations(locations_small, FRAME_SCALE)

    known_encs = known_data["encodings"]
    known_ids  = known_data["user_ids"]
    known_names= known_data["names"]

    for (top, right, bottom, left), face_enc in zip(locations_full, encodings_in_frame):
        distances = face_recognition.face_distance(known_encs, face_enc)
        matches   = face_recognition.compare_faces(known_encs, face_enc, tolerance=tolerance)

        if True in matches:
            best_idx = int(np.argmin(distances))
            results.append({
                "user_id":  known_ids[best_idx],
                "name":     known_names[best_idx],
                "known":    True,
                "top":      top, "right": right,
                "bottom":   bottom, "left": left,
                "distance": float(distances[best_idx]),
            })
        else:
            results.append({
                "user_id":  None,
                "name":     UNKNOWN_LABEL,
                "known":    False,
                "top":      top, "right": right,
                "bottom":   bottom, "left": left,
                "distance": float(np.min(distances)) if len(distances) else 1.0,
            })
    return results


def remove_user_encodings(user_id: int) -> bool:
    """
    Remove all encodings for a specific user from the pkl file.
    Useful when a user is deleted from the system.
    """
    data = load_encodings()
    indices_to_keep = [
        i for i, uid in enumerate(data["user_ids"]) if uid != user_id
    ]
    data["encodings"] = [data["encodings"][i] for i in indices_to_keep]
    data["user_ids"]  = [data["user_ids"][i]  for i in indices_to_keep]
    data["names"]     = [data["names"][i]     for i in indices_to_keep]
    return save_encodings(data)
