"""
gui/attendance_window.py
Live attendance monitoring panel — camera feed + real-time log table + stats.
Embedded as a page inside the main window (not a dialog).
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QAbstractItemView,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from config.settings import (
    ATTENDANCE_ENTRY, ATTENDANCE_EXIT, CAMERA_DISPLAY_W, CAMERA_DISPLAY_H
)
from core.recognize import RecognitionEngine
from core.database import get_attendance_today, get_attendance_count_today, get_user_count
from gui.components.camera_frame import CameraFrame
from gui.components.buttons import PrimaryButton, DangerButton, SecondaryButton
from utils.time_utils import friendly_time
from utils.helpers import log_info


class AttendanceWindow(QWidget):
    """
    Full attendance page — left: live camera feed, right: stats + log table.
    """

    status_changed = pyqtSignal(str)   # emits status bar messages

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine   = RecognitionEngine(
            on_recognized=self._on_recognized,
            on_frame=self._on_frame,
            on_error=self._on_error,
        )
        self._running  = False
        self._log_rows = []   # list of dicts accumulated this session
        self._build_ui()
        self._refresh_stats()

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        # ── Left: camera + controls ────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(12)

        cam_label = QLabel("LIVE FEED")
        cam_label.setObjectName("section_label")
        left.addWidget(cam_label)

        self._camera_frame = CameraFrame(
            width=CAMERA_DISPLAY_W,
            height=CAMERA_DISPLAY_H,
        )
        left.addWidget(self._camera_frame)

        # Controls row
        ctrl = QHBoxLayout()
        self._btn_start = PrimaryButton("▶  Start Recognition")
        self._btn_start.clicked.connect(self._toggle_recognition)
        self._btn_reload = SecondaryButton("↺  Reload Model")
        self._btn_reload.clicked.connect(self._reload_model)
        ctrl.addWidget(self._btn_start)
        ctrl.addWidget(self._btn_reload)
        left.addLayout(ctrl)

        self._engine_status = QLabel("Engine idle. Click Start to begin.")
        self._engine_status.setStyleSheet("color: #64748B; font-size: 12px;")
        left.addWidget(self._engine_status)
        left.addStretch()
        root.addLayout(left)

        # ── Right: stats + table ───────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(16)

        # Stats cards
        stats_lbl = QLabel("TODAY'S SUMMARY")
        stats_lbl.setObjectName("section_label")
        right.addWidget(stats_lbl)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._card_total   = self._stat_card("0",  "Total Logs")
        self._card_users   = self._stat_card("0",  "Registered Users")
        self._card_entries = self._stat_card("0",  "Entries")
        self._card_exits   = self._stat_card("0",  "Exits")
        for card in (self._card_total, self._card_users,
                     self._card_entries, self._card_exits):
            stats_row.addWidget(card[2])
        right.addLayout(stats_row)

        # Live log table
        log_lbl = QLabel("LIVE LOG")
        log_lbl.setObjectName("section_label")
        right.addWidget(log_lbl)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Time", "ID", "Name", "Type", "Log ID"])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        right.addWidget(self._table)

        # Load today's existing records
        self._load_existing_logs()

        root.addLayout(right, 1)

    def _stat_card(self, value: str, label: str):
        frame = QFrame()
        frame.setStyleSheet("background-color: #1A2235; border-radius: 8px;")
        frame.setFixedHeight(72)
        vl = QVBoxLayout(frame)
        vl.setContentsMargins(12, 8, 12, 8)
        v = QLabel(value)
        v.setObjectName("stat_value")
        v.setAlignment(Qt.AlignCenter)
        v.setFont(QFont("Segoe UI", 20, QFont.Bold))
        l = QLabel(label)
        l.setObjectName("stat_label")
        l.setAlignment(Qt.AlignCenter)
        vl.addWidget(v)
        vl.addWidget(l)
        return v, l, frame

    # ── Recognition control ────────────────────────────────────────────────────

    def _toggle_recognition(self):
        if not self._running:
            self._start_recognition()
        else:
            self._stop_recognition()

    def _start_recognition(self):
        loaded = self._engine.load_model()
        if not loaded:
            self._engine_status.setText(
                "⚠ No model found. Register users and train the model first."
            )
            return

        if not self._engine.start():
            self._engine_status.setText("⚠ Camera could not be opened.")
            self._camera_frame.show_error("Camera unavailable")
            return

        self._running = True
        self._btn_start.setText("■  Stop Recognition")
        self._btn_start.setObjectName("btn_danger")
        self._btn_start.style().unpolish(self._btn_start)
        self._btn_start.style().polish(self._btn_start)
        self._engine_status.setText(
            f"Running — {self._engine.known_user_count} users loaded."
        )
        self.status_changed.emit("Recognition active")

        # Poll the engine via a QTimer
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._engine.next_frame)
        self._poll_timer.start(33)

    def _stop_recognition(self):
        if hasattr(self, "_poll_timer"):
            self._poll_timer.stop()
        self._engine.stop()
        self._running = False
        self._camera_frame.show_placeholder("Camera stopped")
        self._btn_start.setText("▶  Start Recognition")
        self._btn_start.setObjectName("btn_primary")
        self._btn_start.style().unpolish(self._btn_start)
        self._btn_start.style().polish(self._btn_start)
        self._engine_status.setText("Engine stopped.")
        self.status_changed.emit("Recognition stopped")

    def _reload_model(self):
        reloaded = self._engine.reload_model()
        msg = (
            f"Model reloaded — {self._engine.encoding_count} encodings."
            if reloaded else "Reload failed — no encodings found."
        )
        self._engine_status.setText(msg)
        self.status_changed.emit(msg)

    # ── Engine callbacks ───────────────────────────────────────────────────────

    def _on_frame(self, frame):
        """Called by the engine with each annotated frame."""
        self._camera_frame.update_frame(frame)

    def _on_recognized(self, result: dict):
        """Called when a face is matched and attendance is logged."""
        self._add_log_row(result)
        self._refresh_stats()
        self.status_changed.emit(
            f"{result['type']}: {result['name']} at {result['reason'].split('at')[-1].strip()}"
        )

    def _on_error(self, message: str):
        self._camera_frame.show_error(message)
        self._engine_status.setText(f"⚠ {message}")
        self._stop_recognition()

    # ── Table helpers ──────────────────────────────────────────────────────────

    def _load_existing_logs(self):
        """Populate the table with today's records from the CSV."""
        records = get_attendance_today()
        for rec in reversed(records):
            self._insert_table_row(
                friendly_time(rec["timestamp"]),
                rec["user_id"],
                rec["name"],
                rec["type"],
                rec["log_id"],
            )

    def _add_log_row(self, result: dict):
        """Insert a new row at the top for a freshly logged event."""
        from utils.time_utils import current_time
        self._insert_table_row(
            current_time(),
            str(result["user_id"]),
            result["name"],
            result["type"],
            result.get("log_id", "—"),
        )

    def _insert_table_row(self, time_str, uid, name, log_type, log_id):
        self._table.insertRow(0)

        is_entry = log_type == ATTENDANCE_ENTRY
        type_color  = "#6EE7B7" if is_entry else "#C4B5FD"
        type_bg     = "#064E3B" if is_entry else "#3B0764"

        items = [
            QTableWidgetItem(time_str),
            QTableWidgetItem(str(uid)),
            QTableWidgetItem(name),
            QTableWidgetItem(log_type),
            QTableWidgetItem(str(log_id)),
        ]

        for col, item in enumerate(items):
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            if col == 3:
                item.setForeground(QColor(type_color))
                item.setBackground(QColor(type_bg))
            self._table.setItem(0, col, item)

        self._table.setRowHeight(0, 38)

    # ── Stats refresh ──────────────────────────────────────────────────────────

    def _refresh_stats(self):
        today = get_attendance_today()
        entries = sum(1 for r in today if r["type"] == ATTENDANCE_ENTRY)
        exits   = sum(1 for r in today if r["type"] == ATTENDANCE_EXIT)
        self._card_total[0].setText(str(len(today)))
        self._card_users[0].setText(str(get_user_count()))
        self._card_entries[0].setText(str(entries))
        self._card_exits[0].setText(str(exits))

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def refresh(self):
        """Called by main window when this page becomes active."""
        self._refresh_stats()

    def cleanup(self):
        """Called on app close to release camera."""
        self._stop_recognition()
