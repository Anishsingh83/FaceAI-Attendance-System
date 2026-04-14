"""
utils/id_generator.py
Auto-generates sequential, collision-safe numeric user IDs.
IDs start at 101 and increment based on the highest existing ID in users.csv.
"""

import os
import csv
from config.settings import USERS_CSV


def _read_existing_ids() -> list[int]:
    """Read all numeric user IDs from users.csv. Returns empty list if file absent."""
    if not os.path.exists(USERS_CSV):
        return []
    ids = []
    try:
        with open(USERS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ids.append(int(row["user_id"]))
                except (ValueError, KeyError):
                    pass
    except Exception:
        pass
    return ids


def generate_user_id() -> int:
    """
    Return the next available user ID.
    Starts at 101; always one higher than the current maximum.
    """
    existing = _read_existing_ids()
    if not existing:
        return 101
    return max(existing) + 1


def is_id_taken(user_id: int) -> bool:
    """Check whether a given user ID already exists in the database."""
    return user_id in _read_existing_ids()


def format_id(user_id: int) -> str:
    """Return a zero-padded 4-digit string representation. e.g. 101 → '0101'"""
    return str(user_id).zfill(4)
