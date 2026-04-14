"""
config/admin_settings.py
Admin credentials, email configuration, and security settings.
"""

import os

# ─── Admin Credentials ─────────────────────────────────────────────────────────
# Change these before deploying!
ADMIN_USERNAME     = "admin"
ADMIN_PASSWORD     = "faceai@123"   # In production, use hashed passwords
ADMIN_DISPLAY_NAME = "Administrator"
SESSION_TIMEOUT_MIN = 30            # Auto-logout after N minutes of inactivity

# ─── Email Settings (Gmail SMTP) ───────────────────────────────────────────────
EMAIL_ENABLED       = False         # Set True after configuring below
EMAIL_SENDER        = "your_email@gmail.com"
EMAIL_PASSWORD      = "your_app_password"   # Gmail App Password (not login password)
EMAIL_RECEIVER      = "receiver@gmail.com"  # Who gets the reports
EMAIL_SMTP_HOST     = "smtp.gmail.com"
EMAIL_SMTP_PORT     = 587
EMAIL_SUBJECT_PREFIX= "[FaceAI Attendance]"

# ─── Camera Settings ───────────────────────────────────────────────────────────
# Add multiple camera indices here
AVAILABLE_CAMERAS   = [0, 1, 2]    # Will auto-detect which ones are available
DEFAULT_CAMERA      = 0
