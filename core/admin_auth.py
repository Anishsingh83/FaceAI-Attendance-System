"""
core/admin_auth.py
Admin authentication and session management.
"""

import hashlib
import time
from config.admin_settings import (
    ADMIN_USERNAME, ADMIN_PASSWORD,
    ADMIN_DISPLAY_NAME, SESSION_TIMEOUT_MIN
)
from utils.helpers import log_info, log_warning


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# Pre-hash the configured password for comparison
_ADMIN_PASSWORD_HASH = _hash(ADMIN_PASSWORD)


class AdminSession:
    """Singleton session state for the logged-in admin."""
    _logged_in:    bool  = False
    _login_time:   float = 0.0
    _last_active:  float = 0.0
    _username:     str   = ""

    @classmethod
    def login(cls, username: str, password: str) -> dict:
        """
        Attempt login. Returns:
        { "success": bool, "message": str }
        """
        if username.strip() != ADMIN_USERNAME:
            log_warning(f"Failed login attempt for username: '{username}'")
            return {"success": False, "message": "Invalid username or password."}

        if _hash(password) != _ADMIN_PASSWORD_HASH:
            log_warning(f"Wrong password for username: '{username}'")
            return {"success": False, "message": "Invalid username or password."}

        cls._logged_in   = True
        cls._login_time  = time.time()
        cls._last_active = time.time()
        cls._username    = username
        log_info(f"Admin logged in: {username}")
        return {"success": True, "message": f"Welcome, {ADMIN_DISPLAY_NAME}!"}

    @classmethod
    def logout(cls) -> None:
        log_info(f"Admin logged out: {cls._username}")
        cls._logged_in   = False
        cls._login_time  = 0.0
        cls._last_active = 0.0
        cls._username    = ""

    @classmethod
    def is_logged_in(cls) -> bool:
        if not cls._logged_in:
            return False
        # Check session timeout
        elapsed_min = (time.time() - cls._last_active) / 60
        if elapsed_min > SESSION_TIMEOUT_MIN:
            log_info("Admin session timed out.")
            cls.logout()
            return False
        return True

    @classmethod
    def touch(cls) -> None:
        """Refresh last-active timestamp to prevent timeout."""
        cls._last_active = time.time()

    @classmethod
    def get_username(cls) -> str:
        return cls._username

    @classmethod
    def session_duration_str(cls) -> str:
        if not cls._logged_in:
            return "—"
        secs = int(time.time() - cls._login_time)
        m, s = divmod(secs, 60)
        return f"{m}m {s}s"
