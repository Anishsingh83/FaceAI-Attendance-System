import uuid
from datetime import datetime

import dlib
import face_recognition_models
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageOps

# ─── Config ────────────────────────────────────────────────────────────────────
TOLERANCE    = 0.50   # lower = stricter match
COOLDOWN_SEC = 10     # seconds before the same person can log again
MAX_SIDE     = 800    # downscale big photos for speed

st.set_page_config(page_title="FaceAI Attendance", page_icon="🎭", layout="wide")


# ─── Models (loaded once) ──────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading face models…")
def load_models():
    detector = dlib.get_frontal_face_detector()
    shape    = dlib.shape_predictor(
        face_recognition_models.pose_predictor_five_point_model_location()
    )
    recog    = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )
    return detector, shape, recog


# ─── Session state ─────────────────────────────────────────────────────────────
def init_state():
    ss = st.session_state
    ss.setdefault("users", {})      # {user_id: {"name": str, "encodings": [np.ndarray]}}
    ss.setdefault("logs", [])       # list of dicts
    ss.setdefault("next_id", 101)


init_state()


# ─── Image / face helpers ──────────────────────────────────────────────────────
def load_image(file) -> Image.Image:
    img = Image.open(file)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    return img


def detect_and_encode(img: Image.Image):
    """Return (rects, encodings) for every face found in a PIL image."""
    detector, shape, recog = load_models()
    arr   = np.array(img)
    rects = detector(arr, 1)
    encs  = [
        np.array(recog.compute_face_descriptor(arr, shape(arr, r), 1))
        for r in rects
    ]
    return rects, encs


def match_face(enc: np.ndarray):
    """Return (user_id | None, distance) for the closest registered user."""
    best_id, best_d = None, 9.0
    for uid, user in st.session_state.users.items():
        d = float(np.min(np.linalg.norm(np.array(user["encodings"]) - enc, axis=1)))
        if d < best_d:
            best_id, best_d = uid, d
    if best_id is not None and best_d <= TOLERANCE:
        return best_id, best_d
    return None, best_d


def draw_boxes(img: Image.Image, boxes) -> Image.Image:
    """boxes: list of (rect, label, known)"""
    out  = img.copy()
    draw = ImageDraw.Draw(out)
    for rect, label, known in boxes:
        color = (0, 200, 100) if known else (230, 60, 60)
        draw.rectangle(
            [rect.left(), rect.top(), rect.right(), rect.bottom()],
            outline=color, width=3,
        )
        draw.rectangle(
            [rect.left(), rect.bottom(), rect.right(), rect.bottom() + 20],
            fill=color,
        )
        draw.text((rect.left() + 4, rect.bottom() + 4), label, fill=(255, 255, 255))
    return out


# ─── Attendance logic ──────────────────────────────────────────────────────────
def record_attendance(uid: int):
    """Returns (logged: bool, message: str)."""
    ss   = st.session_state
    name = ss.users[uid]["name"]
    now  = datetime.now()
    mine = [l for l in ss.logs if l["user_id"] == uid]

    if mine:
        last    = mine[-1]
        elapsed = (now - last["_dt"]).total_seconds()
        if elapsed < COOLDOWN_SEC:
            return False, f"⏳ {name}: cooldown, try again in {int(COOLDOWN_SEC - elapsed)}s"
        kind = "ENTRY" if last["type"] == "EXIT" else "EXIT"
    else:
        kind = "ENTRY"

    ss.logs.append({
        "log_id":    uuid.uuid4().hex[:8].upper(),
        "user_id":   uid,
        "name":      name,
        "type":      kind,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date":      now.strftime("%Y-%m-%d"),
        "_dt":       now,
    })
    return True, f"✅ {kind} recorded for {name}"


def logs_dataframe() -> pd.DataFrame:
    cols = ["log_id", "user_id", "name", "type", "timestamp", "date"]
    if not st.session_state.logs:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(st.session_state.logs)[cols]


# ─── Pages ─────────────────────────────────────────────────────────────────────
def page_home():
    st.title("🎭 FaceAI Attendance System")
    st.caption("Live web demo — real-time face recognition with automatic ENTRY / EXIT logging")

    users = st.session_state.users
    df    = logs_dataframe()
    c1, c2, c3 = st.columns(3)
    c1.metric("Registered users", len(users))
    c2.metric("Total logs", len(df))
    c3.metric("Entries", int((df["type"] == "ENTRY").sum()) if len(df) else 0)

    st.subheader("How to try it")
    st.markdown(
        """
1. Open **Register** → enter a name and add a few clear face photos.
2. Open **Attendance** → take a photo with your camera.
3. First scan = **ENTRY**, next scan = **EXIT** (10 second cooldown).
4. Open **Reports** to see the log and download it as CSV.
        """
    )
    st.info(
        "🔒 **Privacy:** photos and face data live only in your browser session "
        "and are never saved on the server. Refreshing the page clears everything."
    )
    st.markdown(
        "🖥️ Want the full desktop version (admin login, multi-camera, email reports, "
        "attendance %)? → [GitHub repo](https://github.com/Anishsingh83/FaceAI-Attendance-System)"
    )


def page_register():
    st.header("➕ Register a new user")
    name = st.text_input("Full name", placeholder="e.g. Anish Singh")
    uploads = st.file_uploader(
        "Upload 3–5 clear photos of the face (good lighting, one person per photo)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )
    cam = st.camera_input("…or take a photo with your camera")

    if st.button("Register", type="primary"):
        clean = " ".join(name.split()).title()
        if len(clean) < 2:
            st.error("Please enter a valid name.")
            return

        files = list(uploads or []) + ([cam] if cam else [])
        if not files:
            st.error("Add at least one photo.")
            return

        encodings, skipped = [], 0
        with st.spinner("Encoding faces…"):
            for f in files:
                _, encs = detect_and_encode(load_image(f))
                if len(encs) == 1:
                    encodings.append(encs[0])
                else:
                    skipped += 1

        if not encodings:
            st.error("No usable photo found. Each photo must contain exactly one clear face.")
            return

        uid = st.session_state.next_id
        st.session_state.next_id += 1
        st.session_state.users[uid] = {"name": clean, "encodings": encodings}

        st.success(f"Registered **{clean}** (ID {uid}) with {len(encodings)} photo(s).")
        if skipped:
            st.warning(f"{skipped} photo(s) skipped (no face or more than one face).")
        if len(encodings) < 3:
            st.info("Tip: 3–5 photos give noticeably better recognition.")

    if st.session_state.users:
        st.subheader("Registered users")
        st.dataframe(
            pd.DataFrame(
                [
                    {"ID": uid, "Name": u["name"], "Photos": len(u["encodings"])}
                    for uid, u in st.session_state.users.items()
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )


def page_attendance():
    st.header("📷 Take attendance")
    if not st.session_state.users:
        st.warning("No users registered yet. Go to **Register** first.")
        return

    cam = st.camera_input("Look at the camera and take a photo")
    if not cam:
        return

    img = load_image(cam)
    with st.spinner("Recognising…"):
        rects, encs = detect_and_encode(img)

    if not rects:
        st.error("No face detected. Try better lighting and face the camera.")
        return

    boxes, messages = [], []
    for rect, enc in zip(rects, encs):
        uid, dist = match_face(enc)
        if uid is None:
            boxes.append((rect, "Unknown", False))
            messages.append(("warning", "❓ Unknown face (not registered)"))
        else:
            name = st.session_state.users[uid]["name"]
            boxes.append((rect, name, True))
            logged, msg = record_attendance(uid)
            messages.append(("success" if logged else "info", msg))

    st.image(draw_boxes(img, boxes), use_container_width=True)
    for kind, msg in messages:
        getattr(st, kind)(msg)


def page_reports():
    st.header("📊 Reports")
    df = logs_dataframe()
    if df.empty:
        st.info("No attendance recorded yet.")
        return

    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

    summary = (
        df.pivot_table(index="name", columns="type", values="log_id", aggfunc="count", fill_value=0)
        .reset_index()
    )
    st.subheader("Summary per user")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="attendance.csv",
        mime="text/csv",
    )


# ─── Navigation ────────────────────────────────────────────────────────────────
PAGES = {
    "🏠 Home": page_home,
    "➕ Register": page_register,
    "📷 Attendance": page_attendance,
    "📊 Reports": page_reports,
}

st.sidebar.title("🎭 FaceAI")
choice = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")
st.sidebar.divider()
if st.sidebar.button("🗑️ Clear all my data"):
    for k in ("users", "logs", "next_id"):
        st.session_state.pop(k, None)
    init_state()
    st.rerun()
st.sidebar.caption("Demo only — data is not stored on the server.")

PAGES[choice]()