"""
core/register.py
New user registration — ties together ID generation, DB insertion,
dataset directory creation, and post-registration training trigger.
"""

import os
from config.settings import DATASET_DIR, IMAGES_PER_USER
from core.database import add_user, user_exists, get_user
from core.capture import get_user_dataset_dir
from utils.id_generator import generate_user_id
from utils.helpers import sanitize_name, is_valid_name, log_info, log_error, ensure_dir


def register_user(name: str, user_id: int = None) -> dict:
    """
    Register a new user.

    Steps:
      1. Validate and sanitise the name.
      2. Generate (or validate a supplied) user ID.
      3. Create the dataset directory for this user.
      4. Insert the user into users.csv.

    Returns a result dict:
    {
      "success":  bool,
      "user_id":  int | None,
      "name":     str | None,
      "message":  str,
      "dataset_dir": str | None,
    }
    """
    # Validate name
    if not is_valid_name(name):
        return {
            "success": False, "user_id": None, "name": None,
            "message": "Invalid name. Must be at least 2 alphabetic characters.",
            "dataset_dir": None,
        }
    clean_name = sanitize_name(name)

    # Determine user ID
    if user_id is None:
        user_id = generate_user_id()
    elif user_exists(user_id):
        return {
            "success": False, "user_id": user_id, "name": clean_name,
            "message": f"User ID {user_id} is already registered.",
            "dataset_dir": None,
        }

    # Create dataset directory
    dataset_dir = get_user_dataset_dir(user_id)
    ensure_dir(dataset_dir)

    # Placeholder image path (first captured image will be set here)
    image_path = dataset_dir

    # Insert into DB
    ok = add_user(user_id, clean_name, image_path)
    if not ok:
        return {
            "success": False, "user_id": user_id, "name": clean_name,
            "message": f"Database error — could not add user {user_id}.",
            "dataset_dir": None,
        }

    log_info(f"Registered new user: {clean_name} (ID {user_id})")
    return {
        "success":     True,
        "user_id":     user_id,
        "name":        clean_name,
        "message":     f"User '{clean_name}' registered with ID {user_id}.",
        "dataset_dir": dataset_dir,
    }


def complete_registration(user_id: int, auto_train: bool = False) -> dict:
    """
    Called after image capture is complete.
    Optionally triggers model training.

    Returns a status dict.
    """
    user = get_user(user_id)
    if user is None:
        return {"success": False, "message": f"User {user_id} not found in database."}

    result = {"success": True, "message": f"Registration complete for {user['name']}."}

    if auto_train:
        from core.train import train
        ok, msg = train()
        result["train_success"] = ok
        result["train_message"] = msg
        if ok:
            result["message"] += f" Model retrained: {msg}"
        else:
            result["message"] += f" Training failed: {msg}"

    return result


def get_registration_status(user_id: int) -> dict:
    """
    Return a summary of registration completeness for a given user.
    Useful for the GUI progress indicator.
    """
    from utils.helpers import count_images_in_dir

    user = get_user(user_id)
    if user is None:
        return {"registered": False, "images": 0, "target": IMAGES_PER_USER, "ready": False}

    dataset_dir = get_user_dataset_dir(user_id)
    images      = count_images_in_dir(dataset_dir)
    return {
        "registered": True,
        "images":     images,
        "target":     IMAGES_PER_USER,
        "ready":      images >= IMAGES_PER_USER,
        "name":       user["name"],
    }
