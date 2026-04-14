"""
core/attendance.py
Entry/Exit attendance logic with per-user cooldown enforcement.
Wraps core/database.py with the business rules.
"""

from config.settings import (
    ENTRY_COOLDOWN_SEC,
    ATTENDANCE_ENTRY, ATTENDANCE_EXIT,
)
from core.database import log_attendance, get_last_log
from utils.time_utils import seconds_since, current_timestamp
from utils.helpers import log_info


# In-memory cooldown cache to avoid repeated CSV reads during live recognition.
# { user_id: last_log_timestamp_str }
_cooldown_cache: dict[int, str] = {}


def _is_on_cooldown(user_id: int) -> bool:
    """
    Return True if the user logged attendance within the last ENTRY_COOLDOWN_SEC.
    Checks the in-memory cache first; falls back to the CSV for first-time checks.
    """
    ts = _cooldown_cache.get(user_id)
    if ts is None:
        last = get_last_log(user_id)
        if last is None:
            return False
        ts = last["timestamp"]
        _cooldown_cache[user_id] = ts

    return seconds_since(ts) < ENTRY_COOLDOWN_SEC


def _determine_type(user_id: int) -> str:
    """
    Determine whether the next log for this user should be ENTRY or EXIT.
    Alternates based on the last recorded type.
    """
    last = get_last_log(user_id)
    if last is None or last["type"] == ATTENDANCE_EXIT:
        return ATTENDANCE_ENTRY
    return ATTENDANCE_EXIT


def record_attendance(user_id: int, name: str) -> dict:
    """
    Main attendance recording function called by the recognizer.

    Returns a result dict:
    {
      "logged":    bool,
      "type":      str | None,   — "ENTRY" or "EXIT"
      "log_id":    str | None,
      "reason":    str,          — human-readable outcome
      "user_id":   int,
      "name":      str,
    }
    """
    if _is_on_cooldown(user_id):
        secs = int(ENTRY_COOLDOWN_SEC - seconds_since(_cooldown_cache.get(user_id, "2000-01-01 00:00:00")))
        return {
            "logged":  False,
            "type":    None,
            "log_id":  None,
            "reason":  f"Cooldown active — {max(secs, 0)}s remaining",
            "user_id": user_id,
            "name":    name,
        }

    entry_type = _determine_type(user_id)
    log_id     = log_attendance(user_id, name, entry_type)
    ts         = current_timestamp()

    # Update cache
    _cooldown_cache[user_id] = ts

    log_info(f"Attendance: {entry_type} — {name} (ID {user_id})")
    return {
        "logged":  True,
        "type":    entry_type,
        "log_id":  log_id,
        "reason":  f"{entry_type} recorded at {ts}",
        "user_id": user_id,
        "name":    name,
    }


def reset_cooldown(user_id: int) -> None:
    """Manually clear a user's cooldown. Useful for testing."""
    _cooldown_cache.pop(user_id, None)


def get_cooldown_remaining(user_id: int) -> float:
    """Return seconds remaining in cooldown, or 0.0 if not on cooldown."""
    ts = _cooldown_cache.get(user_id)
    if ts is None:
        last = get_last_log(user_id)
        if last is None:
            return 0.0
        ts = last["timestamp"]
    elapsed = seconds_since(ts)
    return max(0.0, ENTRY_COOLDOWN_SEC - elapsed)
