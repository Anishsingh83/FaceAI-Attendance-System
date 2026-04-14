"""
core/database.py
All CSV read/write operations for users and attendance logs.
Every function is atomic — it reads the full file, mutates in memory, writes back.
"""

import os
import csv
import uuid
from typing import Optional

import pandas as pd

from config.settings import (
    USERS_CSV, ATTENDANCE_CSV,
    USERS_COLUMNS, ATTENDANCE_COLUMNS,
)
from utils.helpers import log_info, log_error
from utils.time_utils import current_timestamp, current_date


# ─── Initialisation ────────────────────────────────────────────────────────────

def _ensure_users_csv() -> None:
    if not os.path.exists(USERS_CSV):
        pd.DataFrame(columns=USERS_COLUMNS).to_csv(USERS_CSV, index=False)


def _ensure_attendance_csv() -> None:
    if not os.path.exists(ATTENDANCE_CSV):
        pd.DataFrame(columns=ATTENDANCE_COLUMNS).to_csv(ATTENDANCE_CSV, index=False)


def initialise_db() -> None:
    """Create CSV files with headers if they do not already exist."""
    _ensure_users_csv()
    _ensure_attendance_csv()
    log_info("Database initialised.")


# ─── Users ─────────────────────────────────────────────────────────────────────

def add_user(user_id: int, name: str, image_path: str) -> bool:
    """
    Insert a new user row.
    Returns False (and logs) if the user_id already exists.
    """
    _ensure_users_csv()
    df = pd.read_csv(USERS_CSV, dtype=str)

    if str(user_id) in df["user_id"].astype(str).values:
        log_error(f"User ID {user_id} already exists.")
        return False

    new_row = {
        "user_id":       str(user_id),
        "name":          name,
        "image_path":    image_path,
        "registered_at": current_timestamp(),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(USERS_CSV, index=False)
    log_info(f"User added: {user_id} — {name}")
    return True


def get_user(user_id: int) -> Optional[dict]:
    """Return a user dict by ID, or None if not found."""
    _ensure_users_csv()
    df = pd.read_csv(USERS_CSV, dtype=str)
    match = df[df["user_id"] == str(user_id)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def get_all_users() -> list[dict]:
    """Return all users as a list of dicts."""
    _ensure_users_csv()
    df = pd.read_csv(USERS_CSV, dtype=str)
    return df.to_dict(orient="records")


def delete_user(user_id: int) -> bool:
    """Remove a user by ID. Returns True if the user was found and deleted."""
    _ensure_users_csv()
    df = pd.read_csv(USERS_CSV, dtype=str)
    original_len = len(df)
    df = df[df["user_id"] != str(user_id)]
    if len(df) == original_len:
        log_error(f"Delete failed — user {user_id} not found.")
        return False
    df.to_csv(USERS_CSV, index=False)
    log_info(f"User deleted: {user_id}")
    return True


def user_exists(user_id: int) -> bool:
    return get_user(user_id) is not None


def get_user_count() -> int:
    _ensure_users_csv()
    df = pd.read_csv(USERS_CSV, dtype=str)
    return len(df)


# ─── Attendance ────────────────────────────────────────────────────────────────

def log_attendance(user_id: int, name: str, entry_type: str) -> str:
    """
    Append an attendance row (ENTRY or EXIT).
    Returns the generated log_id.
    """
    _ensure_attendance_csv()
    log_id = str(uuid.uuid4())[:8].upper()
    ts     = current_timestamp()
    date   = current_date()

    new_row = {
        "log_id":    log_id,
        "user_id":   str(user_id),
        "name":      name,
        "type":      entry_type,
        "timestamp": ts,
        "date":      date,
    }
    df = pd.read_csv(ATTENDANCE_CSV, dtype=str)
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(ATTENDANCE_CSV, index=False)
    log_info(f"Attendance logged: {entry_type} — {name} ({user_id}) at {ts}")
    return log_id


def get_last_log(user_id: int) -> Optional[dict]:
    """Return the most recent attendance row for a given user, or None."""
    _ensure_attendance_csv()
    df = pd.read_csv(ATTENDANCE_CSV, dtype=str)
    user_logs = df[df["user_id"] == str(user_id)]
    if user_logs.empty:
        return None
    return user_logs.iloc[-1].to_dict()


def get_attendance_today() -> list[dict]:
    """Return all attendance records for today."""
    _ensure_attendance_csv()
    df = pd.read_csv(ATTENDANCE_CSV, dtype=str)
    today = current_date()
    return df[df["date"] == today].to_dict(orient="records")


def get_all_attendance() -> list[dict]:
    """Return all attendance records."""
    _ensure_attendance_csv()
    df = pd.read_csv(ATTENDANCE_CSV, dtype=str)
    return df.to_dict(orient="records")


def get_attendance_by_date(date_str: str) -> list[dict]:
    """Return attendance records for a specific date string (YYYY-MM-DD)."""
    _ensure_attendance_csv()
    df = pd.read_csv(ATTENDANCE_CSV, dtype=str)
    return df[df["date"] == date_str].to_dict(orient="records")


def get_attendance_count_today() -> int:
    return len(get_attendance_today())
