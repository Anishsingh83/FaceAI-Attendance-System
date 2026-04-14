# FaceAI Attendance System

A real-time face-recognition attendance system built with Python, OpenCV, `face_recognition`, and PyQt5.

---

## Features

- **Live face recognition** via webcam with bounding-box overlays
- **ENTRY / EXIT** toggling with per-user cooldown enforcement
- **User registration wizard** with auto image capture (20 images per user)
- **Model training** from the GUI or CLI
- **Dark-themed PyQt5 GUI** — dashboard, attendance scanner, user management, reports
- **CSV-backed storage** — no database server required
- **Export** attendance to CSV

---

## Project Structure

```
FaceAI_Attendance_System/
├── main.py                    # Entry point
├── requirements.txt
├── config/settings.py         # All paths, thresholds, constants
├── data/                      # users.csv, attendance.csv, logs.txt
├── dataset/                   # Per-user image folders (101/, 102/, …)
├── encodings/face_encodings.pkl
├── models/face_model.py       # Encoding + recognition ML logic
├── core/
│   ├── register.py            # Registration flow
│   ├── capture.py             # Webcam image capture
│   ├── train.py               # Encoding generation
│   ├── recognize.py           # Real-time recognition engine
│   ├── attendance.py          # ENTRY/EXIT logic + cooldown
│   └── database.py            # CSV read/write
├── gui/
│   ├── main_window.py         # Shell with sidebar navigation
│   ├── register_window.py     # Registration dialog
│   ├── attendance_window.py   # Live attendance page
│   └── components/
│       ├── buttons.py
│       └── camera_frame.py
├── utils/
│   ├── helpers.py
│   ├── id_generator.py
│   ├── time_utils.py
│   └── face_utils.py
├── assets/styles/style.qss    # Dark theme
└── tests/
    ├── test_database.py
    └── test_recognition.py
```

---

## Installation

### 1. Clone / extract the project

```bash
cd FaceAI_Attendance_System
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `face_recognition` requires `dlib`. On Windows, install the pre-built wheel:
> ```
> pip install dlib‑19.24.1‑cp311‑cp311‑win_amd64.whl
> ```
> On macOS/Linux, dlib compiles automatically (requires CMake and a C++ compiler).

---

## Running the App

```bash
python main.py
```

---

## Workflow

### Step 1 — Register a user
1. Click **Register** in the sidebar (or **Quick Actions → Register New User**).
2. Enter the person's full name and click **Start Capture**.
3. The webcam opens and auto-captures 20 face images.
4. Click **Finish & Train Model** — the model retrains automatically.

### Step 2 — Take attendance
1. Click **Attendance** in the sidebar.
2. Click **Start Recognition**.
3. The system detects faces and logs ENTRY/EXIT events automatically.

### Step 3 — View reports
- **Dashboard** — live stats and recent activity.
- **Reports** — full attendance history; export to CSV.
- **Users** — manage registered users; delete with model cleanup.

---

## Configuration

All constants live in `config/settings.py`:

| Setting | Default | Description |
|---|---|---|
| `CAMERA_INDEX` | `0` | Webcam index (change for external cameras) |
| `FACE_TOLERANCE` | `0.50` | Recognition strictness (lower = stricter) |
| `IMAGES_PER_USER` | `20` | Images captured per registration |
| `ENTRY_COOLDOWN_SEC` | `30` | Seconds between repeated logs for same user |
| `FRAME_SCALE` | `0.5` | Frame downscale ratio for faster recognition |

---

## Running Tests

```bash
python -m pytest tests/ -v
# or
python tests/test_database.py
python tests/test_recognition.py
```

---

## Troubleshooting

**Camera not opening** — Check `CAMERA_INDEX` in `config/settings.py`. Try `1` or `2` for external cameras.

**`dlib` build fails on Windows** — Download a pre-built `.whl` from [pypi.org](https://pypi.org/project/dlib/#files) matching your Python version.

**Recognition is slow** — Lower `FRAME_SCALE` (e.g. `0.25`) or reduce `IMAGES_PER_USER` before training.

**Unknown faces** — Increase `IMAGES_PER_USER`, ensure good lighting during registration, or decrease `FACE_TOLERANCE` to `0.45`.

---

## License

MIT — free to use and modify.
