"""
utils/helpers.py
General-purpose helper functions shared across the project.
"""

import os
import re
import logging
from config.settings import LOGS_TXT

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_TXT, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("FaceAI")


def log_info(msg: str) -> None:
    logger.info(msg)


def log_warning(msg: str) -> None:
    logger.warning(msg)


def log_error(msg: str) -> None:
    logger.error(msg)


# ─── String Utilities ──────────────────────────────────────────────────────────

def sanitize_name(name: str) -> str:
    """
    Strip leading/trailing whitespace, collapse internal spaces,
    and title-case the name. Removes non-alphabetic characters except spaces.
    e.g. '  john  doe ' → 'John Doe'
    """
    name = name.strip()
    name = re.sub(r"[^a-zA-Z\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.title()


def is_valid_name(name: str) -> bool:
    """Return True if the name is non-empty and contains at least 2 characters."""
    cleaned = sanitize_name(name)
    return len(cleaned) >= 2


# ─── File / Directory Utilities ────────────────────────────────────────────────

def ensure_dir(path: str) -> str:
    """Create directory (and parents) if it doesn't exist. Returns the path."""
    os.makedirs(path, exist_ok=True)
    return path


def file_exists(path: str) -> bool:
    return os.path.isfile(path)


def count_images_in_dir(directory: str) -> int:
    """Count how many image files (.jpg, .jpeg, .png) exist in a directory."""
    if not os.path.isdir(directory):
        return 0
    exts = {".jpg", ".jpeg", ".png"}
    return sum(
        1 for f in os.listdir(directory)
        if os.path.splitext(f)[1].lower() in exts
    )


def list_user_image_dirs(dataset_dir: str) -> list[str]:
    """
    Return a list of subdirectory paths inside dataset_dir
    where each subdir name is a numeric user ID.
    """
    dirs = []
    if not os.path.isdir(dataset_dir):
        return dirs
    for name in os.listdir(dataset_dir):
        full = os.path.join(dataset_dir, name)
        if os.path.isdir(full) and name.isdigit():
            dirs.append(full)
    return dirs


# ─── Numeric Utilities ─────────────────────────────────────────────────────────

def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi."""
    return max(lo, min(hi, value))


def percentage(part: int, total: int) -> float:
    """Safe percentage calculation. Returns 0.0 if total is 0."""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 1)
