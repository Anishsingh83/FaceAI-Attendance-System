"""
core/attendance_stats.py
Attendance percentage calculations per user, per date range.
"""

from datetime import datetime, timedelta
from collections import defaultdict
from core.database import get_all_attendance, get_all_users
from config.settings import ATTENDANCE_ENTRY, LOG_DATE_FORMAT


def _parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, LOG_DATE_FORMAT)
    except ValueError:
        return None


def get_working_days(from_date: str, to_date: str) -> list[str]:
    """
    Return list of working day date strings (Mon–Sat) between two dates inclusive.
    """
    start = _parse_date(from_date)
    end   = _parse_date(to_date)
    if not start or not end or start > end:
        return []
    days = []
    current = start
    while current <= end:
        if current.weekday() < 6:   # Mon=0 … Sat=5, skip Sun=6
            days.append(current.strftime(LOG_DATE_FORMAT))
        current += timedelta(days=1)
    return days


def calculate_attendance_percentage(
    from_date: str,
    to_date:   str,
) -> list[dict]:
    """
    Calculate attendance percentage for every registered user
    between from_date and to_date.

    Returns list of dicts sorted by percentage descending:
    [
      {
        "user_id":    int,
        "name":       str,
        "present":    int,   — days with at least one ENTRY
        "total":      int,   — total working days
        "percentage": float,
        "status":     str,   — "Good" / "Average" / "Low"
        "absent_days": list[str],
      },
      ...
    ]
    """
    working_days   = get_working_days(from_date, to_date)
    total_days     = len(working_days)
    working_days_set = set(working_days)

    all_records = get_all_attendance()
    all_users   = get_all_users()

    # Build set of (user_id, date) for days with an ENTRY
    present_map: dict[str, set] = defaultdict(set)
    for rec in all_records:
        if rec["type"] == ATTENDANCE_ENTRY and rec["date"] in working_days_set:
            present_map[str(rec["user_id"])].add(rec["date"])

    results = []
    for user in all_users:
        uid        = str(user["user_id"])
        present    = present_map.get(uid, set())
        present_days = len(present)
        pct        = round((present_days / total_days * 100), 1) if total_days > 0 else 0.0
        absent_days = sorted(working_days_set - present)

        if pct >= 75:
            status = "Good"
        elif pct >= 50:
            status = "Average"
        else:
            status = "Low"

        results.append({
            "user_id":     int(uid),
            "name":        user["name"],
            "present":     present_days,
            "total":       total_days,
            "percentage":  pct,
            "status":      status,
            "absent_days": absent_days,
        })

    return sorted(results, key=lambda x: x["percentage"], reverse=True)


def get_daily_summary(date_str: str) -> dict:
    """
    Return a summary for a specific date:
    {
      "date":         str,
      "total_users":  int,
      "present":      int,
      "absent":       int,
      "percentage":   float,
      "entries":      int,
      "exits":        int,
    }
    """
    all_records = get_all_attendance()
    all_users   = get_all_users()
    total_users = len(all_users)

    day_records = [r for r in all_records if r["date"] == date_str]
    entries = sum(1 for r in day_records if r["type"] == ATTENDANCE_ENTRY)
    exits   = sum(1 for r in day_records if r["type"] != ATTENDANCE_ENTRY)

    present_ids = {r["user_id"] for r in day_records if r["type"] == ATTENDANCE_ENTRY}
    present     = len(present_ids)
    absent      = total_users - present
    pct         = round(present / total_users * 100, 1) if total_users > 0 else 0.0

    return {
        "date":        date_str,
        "total_users": total_users,
        "present":     present,
        "absent":      max(absent, 0),
        "percentage":  pct,
        "entries":     entries,
        "exits":       exits,
    }


def get_user_streak(user_id: int) -> dict:
    """
    Return the current consecutive present-day streak for a user.
    """
    all_records = get_all_attendance()
    present_dates = sorted({
        r["date"] for r in all_records
        if str(r["user_id"]) == str(user_id) and r["type"] == ATTENDANCE_ENTRY
    }, reverse=True)

    if not present_dates:
        return {"streak": 0, "last_present": None}

    streak = 1
    prev   = _parse_date(present_dates[0])
    for d in present_dates[1:]:
        curr = _parse_date(d)
        diff = (prev - curr).days
        if diff == 1:
            streak += 1
            prev = curr
        elif diff > 1:
            break

    return {"streak": streak, "last_present": present_dates[0]}
