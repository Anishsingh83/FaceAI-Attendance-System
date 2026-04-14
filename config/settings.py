"""
config/settings.py
Central configuration — all paths, thresholds, and constants live here.
Import this module anywhere in the project instead of hardcoding values.
"""

import os

# ─── Base Directory ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── Data Paths ────────────────────────────────────────────────────────────────
DATA_DIR        = os.path.join(BASE_DIR, "data")
DATASET_DIR     = os.path.join(BASE_DIR, "dataset")
ENCODINGS_DIR   = os.path.join(BASE_DIR, "encodings")
ASSETS_DIR      = os.path.join(BASE_DIR, "assets")
STYLES_DIR      = os.path.join(ASSETS_DIR, "styles")

USERS_CSV       = os.path.join(DATA_DIR, "users.csv")
ATTENDANCE_CSV  = os.path.join(DATA_DIR, "attendance.csv")
LOGS_TXT        = os.path.join(DATA_DIR, "logs.txt")
ENCODINGS_PKL   = os.path.join(ENCODINGS_DIR, "face_encodings.pkl")
STYLE_QSS       = os.path.join(STYLES_DIR, "style.qss")

# ─── CSV Column Definitions ────────────────────────────────────────────────────
USERS_COLUMNS      = ["user_id", "name", "image_path", "registered_at"]
ATTENDANCE_COLUMNS = ["log_id", "user_id", "name", "type", "timestamp", "date"]

# ─── Camera Settings ───────────────────────────────────────────────────────────
CAMERA_INDEX        = 0          # 0 = default webcam; change for external cameras
CAMERA_WIDTH        = 640
CAMERA_HEIGHT       = 480
CAMERA_FPS          = 30
FRAME_SCALE         = 0.5        # Scale factor for faster recognition (0.25–1.0)

# ─── Face Recognition Thresholds ──────────────────────────────────────────────
FACE_TOLERANCE      = 0.50       # Lower = stricter match (0.4–0.6 recommended)
MIN_FACE_CONFIDENCE = 0.90       # Minimum confidence to accept a recognition
UNKNOWN_LABEL       = "Unknown"

# ─── Dataset & Training ───────────────────────────────────────────────────────
IMAGES_PER_USER     = 20         # How many images to capture per user during registration
CAPTURE_DELAY_MS    = 300        # Milliseconds between auto-captures
MIN_IMAGES_TO_TRAIN = 5          # Minimum images required before training

# ─── Attendance Logic ─────────────────────────────────────────────────────────
ENTRY_COOLDOWN_SEC  = 30         # Seconds before the same person can log again
ATTENDANCE_ENTRY    = "ENTRY"
ATTENDANCE_EXIT     = "EXIT"

# ─── UI Settings ──────────────────────────────────────────────────────────────
APP_NAME            = "FaceAI Attendance"
APP_VERSION         = "1.0.0"
WINDOW_MIN_WIDTH    = 1100
WINDOW_MIN_HEIGHT   = 700
CAMERA_DISPLAY_W    = 640
CAMERA_DISPLAY_H    = 480
BBOX_COLOR_KNOWN    = (0, 220, 100)    # Green bounding box for recognised faces
BBOX_COLOR_UNKNOWN  = (0, 80, 255)     # Red bounding box for unknown faces
BBOX_THICKNESS      = 2

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_DATE_FORMAT     = "%Y-%m-%d"
LOG_TIME_FORMAT     = "%H:%M:%S"
LOG_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# ─── Ensure all directories exist on import ────────────────────────────────────
for _dir in (DATA_DIR, DATASET_DIR, ENCODINGS_DIR, ASSETS_DIR, STYLES_DIR):
    os.makedirs(_dir, exist_ok=True)
