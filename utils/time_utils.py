"""
utils/time_utils.py
Date and time formatting utilities used across the entire project.
"""

from datetime import datetime
from config.settings import LOG_DATE_FORMAT, LOG_TIME_FORMAT, LOG_DATETIME_FORMAT


def now() -> datetime:
    """Return the current datetime."""
    return datetime.now()


def current_timestamp() -> str:
    """Return current date+time as a formatted string. e.g. '2024-08-15 09:30:45'"""
    return now().strftime(LOG_DATETIME_FORMAT)


def current_date() -> str:
    """Return current date string. e.g. '2024-08-15'"""
    return now().strftime(LOG_DATE_FORMAT)


def current_time() -> str:
    """Return current time string. e.g. '09:30:45'"""
    return now().strftime(LOG_TIME_FORMAT)


def format_timestamp(dt: datetime) -> str:
    """Format a datetime object to the standard timestamp string."""
    return dt.strftime(LOG_DATETIME_FORMAT)


def parse_timestamp(ts: str) -> datetime:
    """Parse a standard timestamp string back into a datetime object."""
    return datetime.strptime(ts, LOG_DATETIME_FORMAT)


def seconds_since(ts_str: str) -> float:
    """
    Return how many seconds have elapsed since the given timestamp string.
    Returns a large number if parsing fails (safe default).
    """
    try:
        past = parse_timestamp(ts_str)
        return (now() - past).total_seconds()
    except (ValueError, TypeError):
        return float("inf")


def friendly_time(ts_str: str) -> str:
    """
    Convert a timestamp string to a human-friendly relative label.
    e.g. 'Just now', '5 min ago', '2 hours ago', 'Yesterday', or the date.
    """
    try:
        past = parse_timestamp(ts_str)
        delta = now() - past
        secs  = int(delta.total_seconds())

        if secs < 60:
            return "Just now"
        elif secs < 3600:
            m = secs // 60
            return f"{m} min ago"
        elif secs < 86400:
            h = secs // 3600
            return f"{h} hour{'s' if h > 1 else ''} ago"
        elif secs < 172800:
            return "Yesterday"
        else:
            return past.strftime(LOG_DATE_FORMAT)
    except (ValueError, TypeError):
        return ts_str
