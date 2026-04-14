"""
gui/register_window.py
User registration dialog — name entry, live webcam capture, and model training trigger.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QProgressBar, QFrame, QMessageBox,
    QSizePolicy, QSpacerItem,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

import cv2

from config.settings import IMAGES_PER_USER, CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT
from core.register import register_user, complete_registration
from core.capture import CaptureSession
from gui.components.camera_frame import CameraFrame
from gui.components.buttons import PrimaryButton, SuccessButton, SecondaryButton, DangerButton
from utils.helpers import log_info


class RegisterWindow(QDialog):
    """
    Modal dialog for registering a new user.
    Emits user_registered(user_id, name) when registration + capture are done.
    """

    user_registered = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Register New User")
        self.setMinimumSize(900, 580)
        self.setModal(True)

        self._cap:     cv2.VideoCapture = None
        self._session: CaptureSession   = None
        self._timer:   QTimer           = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._elapsed_ms = 0

        self._phase = "form"  # "form" | "capture" | "done"

        self._build_ui()

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left panel: camera ─────────────────────────────────────────────────
        left = QFrame()
        left.setStyleSheet("background-color: #080C14;")
        left.setFixedWidth(520)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setAlignment(Qt.AlignCenter)

        self._camera_frame = CameraFrame(width=480, height=400)
        left_layout.addWidget(self._camera_frame, 0, Qt.AlignCenter)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, IMAGES_PER_USER)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        left_layout.addSpacing(12)
        left_layout.addWidget(self._progress_bar)

        self._capture_status = QLabel("Position your face in the frame and click Start Capture.")
        self._capture_status.setAlignment(Qt.AlignCenter)
        self._capture_status.setStyleSheet("color: #64748B; font-size: 12px;")
        self._capture_status.setWordWrap(True)
        left_layout.addSpacing(6)
        left_layout.addWidget(self._capture_status)

        root.addWidget(left)

        # ── Right panel: form ──────────────────────────────────────────────────
        right = QFrame()
        right.setStyleSheet("background-color: #0F1117;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(36, 36, 36, 36)
        right_layout.setSpacing(0)

        # Header
        title = QLabel("New User")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        right_layout.addWidget(title)

        subtitle = QLabel("Fill in the details below, then capture face images.")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px; margin-bottom: 28px;")
        subtitle.setWordWrap(True)
        right_layout.addWidget(subtitle)
        right_layout.addSpacing(24)

        # Name field
        name_lbl = QLabel("FULL NAME")
        name_lbl.setObjectName("section_label")
        right_layout.addWidget(name_lbl)
        right_layout.addSpacing(6)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("e.g. Aarav Sharma")
        self._name_input.setMinimumHeight(42)
        self._name_input.returnPressed.connect(self._on_start_clicked)
        right_layout.addWidget(self._name_input)
        right_layout.addSpacing(24)

        # Auto-ID display
        id_lbl = QLabel("USER ID  (auto-assigned)")
        id_lbl.setObjectName("section_label")
        right_layout.addWidget(id_lbl)
        right_layout.addSpacing(6)

        self._id_display = QLineEdit()
        self._id_display.setReadOnly(True)
        self._id_display.setPlaceholderText("Assigned after clicking Start")
        self._id_display.setMinimumHeight(42)
        self._id_display.setStyleSheet("color: #38BDF8;")
        right_layout.addWidget(self._id_display)
        right_layout.addSpacing(32)

        # Capture stats
        stats_row = QHBoxLayout()
        self._stat_captured = self._make_stat("0", "Captured")
        self._stat_target   = self._make_stat(str(IMAGES_PER_USER), "Target")
        stats_row.addWidget(self._stat_captured[2])
        stats_row.addWidget(self._stat_target[2])
        right_layout.addLayout(stats_row)
        right_layout.addSpacing(32)

        right_layout.addStretch()

        # Action buttons
        self._btn_start = PrimaryButton("▶  Start Capture")
        self._btn_start.clicked.connect(self._on_start_clicked)
        right_layout.addWidget(self._btn_start)
        right_layout.addSpacing(10)

        self._btn_finish = SuccessButton("✓  Finish & Train Model")
        self._btn_finish.setEnabled(False)
        self._btn_finish.clicked.connect(self._on_finish_clicked)
        right_layout.addWidget(self._btn_finish)
        right_layout.addSpacing(10)

        self._btn_cancel = SecondaryButton("Cancel")
        self._btn_cancel.clicked.connect(self.reject)
        right_layout.addWidget(self._btn_cancel)

        root.addWidget(right)

    def _make_stat(self, value: str, label: str):
        """Helper to create a mini stat card. Returns (value_lbl, label_lbl, frame)."""
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: #1A2235; border-radius: 8px;"
        )
        frame.setFixedHeight(72)
        vl = QVBoxLayout(frame)
        vl.setContentsMargins(16, 8, 16, 8)
        v = QLabel(value)
        v.setObjectName("stat_value")
        v.setAlignment(Qt.AlignCenter)
        l = QLabel(label)
        l.setObjectName("stat_label")
        l.setAlignment(Qt.AlignCenter)
        vl.addWidget(v)
        vl.addWidget(l)
        return v, l, frame

    # ── Phase: Form → Capture ──────────────────────────────────────────────────

    def _on_start_clicked(self):
        name = self._name_input.text().strip()
        if not name:
            self._name_input.setFocus()
            self._shake_input()
            return

        result = register_user(name)
        if not result["success"]:
            QMessageBox.warning(self, "Registration Error", result["message"])
            return

        self._user_id   = result["user_id"]
        self._user_name = result["name"]
        self._id_display.setText(str(self._user_id))

        # Lock form
        self._name_input.setEnabled(False)
        self._btn_start.setEnabled(False)

        # Start camera
        self._cap = cv2.VideoCapture(CAMERA_INDEX)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        if not self._cap.isOpened():
            QMessageBox.critical(self, "Camera Error",
                                 "Could not open the camera. Check your settings.")
            self._btn_start.setEnabled(True)
            return

        self._session    = CaptureSession(self._user_id, IMAGES_PER_USER)
        self._elapsed_ms = 0
        self._phase      = "capture"
        self._timer.start(33)  # ~30 fps
        self._capture_status.setText("Auto-capturing… keep your face in the frame.")
        log_info(f"Capture session started for user {self._user_id}.")

    # ── Camera tick ────────────────────────────────────────────────────────────

    def _tick(self):
        if self._cap is None or not self._cap.isOpened():
            return

        ret, frame = self._cap.read()
        if not ret:
            return

        self._elapsed_ms += 33

        status = self._session.feed_frame(frame, 33)

        # Overlay feedback on the frame
        from utils.face_utils import draw_status_banner
        color = (10, 120, 50) if status["has_face"] else (30, 30, 80)
        msg   = (
            f"Capturing {status['captured']}/{status['target']}…"
            if status["has_face"]
            else "No face detected — adjust position"
        )
        draw_status_banner(frame, msg, color)
        self._camera_frame.update_frame(frame)

        # Update stats
        self._stat_captured[0].setText(str(status["captured"]))
        self._progress_bar.setValue(status["captured"])

        if status["complete"]:
            self._on_capture_complete()

    # ── Phase: Capture done ────────────────────────────────────────────────────

    def _on_capture_complete(self):
        self._timer.stop()
        if self._cap:
            self._cap.release()
            self._cap = None

        self._phase = "done"
        self._camera_frame.show_placeholder("Capture complete ✓")
        self._capture_status.setText(
            f"✓ {IMAGES_PER_USER} images captured for {self._user_name}. "
            "Click 'Finish & Train Model' to save."
        )
        self._btn_finish.setEnabled(True)
        log_info(f"Capture complete for user {self._user_id}.")

    # ── Phase: Finish & Train ──────────────────────────────────────────────────

    def _on_finish_clicked(self):
        self._btn_finish.setEnabled(False)
        self._btn_finish.setText("Training…")
        self._capture_status.setText("Training the model — this may take a moment…")

        # Run in the same thread (fast enough for <500 images; use QThread for large datasets)
        result = complete_registration(self._user_id, auto_train=True)

        if result.get("train_success"):
            self._capture_status.setText("✓ Model trained successfully!")
        else:
            self._capture_status.setText(
                "Registration saved. Training failed — retrain manually."
            )

        self.user_registered.emit(self._user_id, self._user_name)
        QMessageBox.information(
            self, "Registration Complete",
            f"User '{self._user_name}' (ID {self._user_id}) has been registered.\n\n"
            + result.get("train_message", ""),
        )
        self.accept()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _shake_input(self):
        """Brief visual feedback that the name field needs attention."""
        original = self._name_input.styleSheet()
        self._name_input.setStyleSheet(
            original + "border-color: #EF4444; background-color: #1F1010;"
        )
        QTimer.singleShot(
            600,
            lambda: self._name_input.setStyleSheet(original),
        )

    def closeEvent(self, event):
        self._timer.stop()
        if self._cap and self._cap.isOpened():
            self._cap.release()
        super().closeEvent(event)

    def reject(self):
        self._timer.stop()
        if self._cap and self._cap.isOpened():
            self._cap.release()
        super().reject()
