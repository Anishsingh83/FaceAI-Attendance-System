"""
core/train.py
Encoding generation — walks the dataset folder and builds face_encodings.pkl.
Can be run standalone or triggered from the GUI after registration.
"""

from config.settings import DATASET_DIR, MIN_IMAGES_TO_TRAIN
from models.face_model import build_encodings_from_dataset, save_encodings, load_encodings
from utils.helpers import log_info, log_warning, count_images_in_dir, list_user_image_dirs


def validate_dataset() -> tuple[bool, str]:
    """
    Check that the dataset directory has enough images to train.
    Returns (ok: bool, message: str).
    """
    dirs = list_user_image_dirs(DATASET_DIR)
    if not dirs:
        return False, "No user folders found in dataset/. Register at least one user first."

    total_images = 0
    users_ready  = 0
    for d in dirs:
        n = count_images_in_dir(d)
        total_images += n
        if n >= MIN_IMAGES_TO_TRAIN:
            users_ready += 1

    if users_ready == 0:
        return (
            False,
            f"No user has {MIN_IMAGES_TO_TRAIN}+ images. "
            f"Capture more images before training.",
        )
    return True, f"{users_ready} user(s) ready. {total_images} total images."


def train(progress_callback=None) -> tuple[bool, str]:
    """
    Run the full training pipeline.

    progress_callback(current, total, user_id, filename) — optional UI hook.

    Returns (success: bool, message: str).
    """
    ok, msg = validate_dataset()
    if not ok:
        log_warning(f"Training aborted: {msg}")
        return False, msg

    log_info("Training started…")
    data = build_encodings_from_dataset(DATASET_DIR, progress_callback=progress_callback)

    if not data["encodings"]:
        return False, "Training failed — no valid face encodings could be generated."

    saved = save_encodings(data)
    if not saved:
        return False, "Training complete but failed to save encodings to disk."

    result_msg = (
        f"Training complete. "
        f"{len(data['encodings'])} encodings from "
        f"{len(set(data['user_ids']))} user(s) saved."
    )
    log_info(result_msg)
    return True, result_msg


def get_training_stats() -> dict:
    """
    Return a summary dict about the current encodings file.
    {
      "exists":       bool,
      "total":        int,   — total encodings
      "unique_users": int,
      "users":        list[dict]  — [{"user_id": int, "name": str, "count": int}]
    }
    """
    data = load_encodings()
    if not data["encodings"]:
        return {"exists": False, "total": 0, "unique_users": 0, "users": []}

    from collections import Counter
    counts = Counter(zip(data["user_ids"], data["names"]))
    users  = [
        {"user_id": uid, "name": name, "count": cnt}
        for (uid, name), cnt in sorted(counts.items())
    ]
    return {
        "exists":       True,
        "total":        len(data["encodings"]),
        "unique_users": len(users),
        "users":        users,
    }


# ─── CLI Entry Point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    def _cli_progress(current, total, user_id, filename):
        pct = int((current / total) * 100)
        print(f"\r[{pct:3d}%] {current}/{total}  user={user_id}  file={filename}", end="", flush=True)

    success, message = train(progress_callback=_cli_progress)
    print()   # newline after progress bar
    print("✓" if success else "✗", message)
