"""
gui/main_window.py
Main application window — sidebar navigation, page stack, global status bar.
Now includes: Stats, Camera selector, Email reports, Admin logout.
"""

import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStackedWidget, QFrame, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QStatusBar,
    QComboBox,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont, QColor

from config.settings import APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from core.database import (
    initialise_db, get_all_users, get_user_count,
    get_attendance_today, get_all_attendance, delete_user,
)
from core.train import train, get_training_stats
from core.admin_auth import AdminSession
from gui.components.buttons import (
    PrimaryButton, SuccessButton, DangerButton,
    SecondaryButton, SidebarButton,
)
from utils.time_utils import friendly_time, current_date
from utils.helpers import log_info


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        initialise_db()

        self._page_buttons: list[SidebarButton] = []
        self._build_ui()
        self._navigate(0)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(60_000)
        self._update_clock()

        # Touch session every 5 minutes
        self._session_timer = QTimer(self)
        self._session_timer.timeout.connect(AdminSession.touch)
        self._session_timer.start(300_000)

    # ══════════════════════════════════════════════════════════════════════════
    # UI Construction
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self._status_bar = QStatusBar()
        self._status_bar.showMessage("Ready")
        self.setStatusBar(self._status_bar)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content_area(), 1)

    # ── Sidebar ────────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(
            "background-color: #090D14; border-right: 1px solid #1E293B;"
        )
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 24, 12, 16)
        layout.setSpacing(4)

        logo = QLabel(f"⬡  {APP_NAME}")
        logo.setFont(QFont("Segoe UI", 13, QFont.Bold))
        logo.setStyleSheet("color: #38BDF8; padding: 0 8px 4px 8px;")
        layout.addWidget(logo)

        admin_lbl = QLabel(f"👤 {AdminSession.get_username()}")
        admin_lbl.setStyleSheet("color: #475569; font-size: 11px; padding: 0 8px 16px 8px;")
        layout.addWidget(admin_lbl)

        self._clock_label = QLabel()
        self._clock_label.setStyleSheet(
            "color: #334155; font-size: 11px; padding: 0 8px 20px 8px;"
        )
        layout.addWidget(self._clock_label)

        pages = [
            ("⊞  Dashboard",    0),
            ("◉  Attendance",   1),
            ("＋  Register",    2),
            ("⊙  Users",        3),
            ("⊛  Reports",      4),
            ("📊  Statistics",   5),
            ("⚙  Settings",     6),
        ]
        for label, idx in pages:
            btn = SidebarButton(label)
            btn.clicked.connect(lambda checked, i=idx: self._navigate(i))
            self._page_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Logout button
        btn_logout = DangerButton("⏻  Logout")
        btn_logout.clicked.connect(self._logout)
        layout.addWidget(btn_logout)

        ver = QLabel(f"v{APP_VERSION}")
        ver.setStyleSheet("color: #1E293B; font-size: 10px; padding: 4px 8px 0 8px;")
        layout.addWidget(ver)
        return sidebar

    # ── Content area ───────────────────────────────────────────────────────────

    def _build_content_area(self) -> QStackedWidget:
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_dashboard())    # 0
        self._stack.addWidget(self._build_attendance())   # 1
        self._stack.addWidget(self._build_register())     # 2
        self._stack.addWidget(self._build_users())        # 3
        self._stack.addWidget(self._build_reports())      # 4
        self._stack.addWidget(self._build_stats())        # 5
        self._stack.addWidget(self._build_settings())     # 6
        return self._stack

    # ══════════════════════════════════════════════════════════════════════════
    # Page builders
    # ══════════════════════════════════════════════════════════════════════════

    def _build_dashboard(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        hdr = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("title_label")
        hdr.addWidget(title)
        hdr.addStretch()
        self._dash_date = QLabel(current_date())
        self._dash_date.setStyleSheet("color: #475569; font-size: 13px;")
        hdr.addWidget(self._dash_date)
        layout.addLayout(hdr)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self._d_stat_users     = self._dash_stat("0", "Total Users",     "#38BDF8")
        self._d_stat_today     = self._dash_stat("0", "Today's Logs",    "#10B981")
        self._d_stat_entries   = self._dash_stat("0", "Entries Today",   "#A78BFA")
        self._d_stat_encodings = self._dash_stat("0", "Face Encodings",  "#F59E0B")
        for card in (self._d_stat_users, self._d_stat_today,
                     self._d_stat_entries, self._d_stat_encodings):
            cards_row.addWidget(card[2])
        layout.addLayout(cards_row)

        recent_lbl = QLabel("RECENT ACTIVITY")
        recent_lbl.setObjectName("section_label")
        layout.addWidget(recent_lbl)

        self._dash_table = self._make_log_table(["Time", "Name", "Type", "Log ID"])
        layout.addWidget(self._dash_table)

        qa_lbl = QLabel("QUICK ACTIONS")
        qa_lbl.setObjectName("section_label")
        layout.addWidget(qa_lbl)

        qa_row = QHBoxLayout()
        qa_row.setSpacing(12)
        btn_attend   = PrimaryButton("Open Attendance Scanner")
        btn_attend.clicked.connect(lambda: self._navigate(1))
        btn_register = SuccessButton("Register New User")
        btn_register.clicked.connect(lambda: self._navigate(2))
        btn_train    = SecondaryButton("Retrain Model")
        btn_train.clicked.connect(self._retrain)
        qa_row.addWidget(btn_attend)
        qa_row.addWidget(btn_register)
        qa_row.addWidget(btn_train)
        qa_row.addStretch()
        layout.addLayout(qa_row)
        layout.addStretch()
        return w

    def _dash_stat(self, value, label, color):
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: #111827; border-radius: 10px;"
            f"border-left: 3px solid {color};"
        )
        frame.setFixedHeight(88)
        vl = QVBoxLayout(frame)
        vl.setContentsMargins(20, 12, 12, 12)
        v = QLabel(value)
        v.setFont(QFont("Segoe UI", 26, QFont.Bold))
        v.setStyleSheet(f"color: {color}; border: none;")
        l = QLabel(label)
        l.setStyleSheet("color: #64748B; font-size: 12px; border: none;")
        vl.addWidget(v)
        vl.addWidget(l)
        return v, l, frame

    def _build_attendance(self) -> QWidget:
        from gui.attendance_window import AttendanceWindow
        self._attendance_page = AttendanceWindow()
        self._attendance_page.status_changed.connect(self._status_bar.showMessage)
        return self._attendance_page

    def _build_register(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Register New User")
        title.setObjectName("title_label")
        layout.addWidget(title)

        subtitle = QLabel(
            "Click the button below to open the registration wizard.\n"
            "You will enter a name, then capture face images via webcam."
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 13px; margin-top: 4px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addSpacing(32)

        btn = PrimaryButton("＋  Open Registration Wizard")
        btn.setFixedWidth(280)
        btn.setMinimumHeight(44)
        btn.clicked.connect(self._open_register_dialog)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _build_users(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("Registered Users")
        title.setObjectName("title_label")
        hdr.addWidget(title)
        hdr.addStretch()
        refresh_btn = SecondaryButton("↺  Refresh")
        refresh_btn.clicked.connect(self._refresh_users_table)
        del_btn = DangerButton("Delete Selected")
        del_btn.clicked.connect(self._delete_selected_user)
        hdr.addWidget(refresh_btn)
        hdr.addWidget(del_btn)
        layout.addLayout(hdr)

        self._users_table = self._make_log_table(["ID", "Name", "Registered At", "Image Path"])
        self._users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._users_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self._users_table)
        return w

    def _build_reports(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("Attendance Reports")
        title.setObjectName("title_label")
        layout.addWidget(title)

        hdr = QHBoxLayout()
        hdr.addStretch()
        export_btn = SecondaryButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        email_btn  = PrimaryButton("✉  Email Report")
        email_btn.clicked.connect(self._email_report)
        hdr.addWidget(export_btn)
        hdr.addWidget(email_btn)
        layout.addLayout(hdr)

        self._reports_table = self._make_log_table(
            ["Date", "Time", "ID", "Name", "Type", "Log ID"]
        )
        self._reports_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self._reports_table)
        return w

    def _build_stats(self) -> QWidget:
        from gui.stats_window import StatsWindow
        self._stats_page = StatsWindow()
        return self._stats_page

    def _build_settings(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Settings")
        title.setObjectName("title_label")
        layout.addWidget(title)

        # ── Camera selector ────────────────────────────────────────────────────
        cam_lbl = QLabel("CAMERA SELECTION")
        cam_lbl.setObjectName("section_label")
        layout.addWidget(cam_lbl)

        cam_row = QHBoxLayout()
        self._camera_combo = QComboBox()
        self._camera_combo.setMinimumHeight(38)
        self._camera_combo.setMinimumWidth(200)
        self._camera_combo.addItem("Scanning cameras…")
        cam_row.addWidget(self._camera_combo)

        btn_scan = SecondaryButton("🔍  Scan Cameras")
        btn_scan.clicked.connect(self._scan_cameras)
        cam_row.addWidget(btn_scan)

        btn_apply_cam = PrimaryButton("Apply Camera")
        btn_apply_cam.clicked.connect(self._apply_camera)
        cam_row.addWidget(btn_apply_cam)
        cam_row.addStretch()
        layout.addLayout(cam_row)

        self._cam_status = QLabel("Click 'Scan Cameras' to detect available cameras.")
        self._cam_status.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addWidget(self._cam_status)

        layout.addSpacing(16)

        # ── Model stats ────────────────────────────────────────────────────────
        stats_lbl = QLabel("MODEL STATUS")
        stats_lbl.setObjectName("section_label")
        layout.addWidget(stats_lbl)

        self._model_info = QLabel("Loading…")
        self._model_info.setStyleSheet(
            "color: #94A3B8; background-color: #111827;"
            "border-radius: 8px; padding: 16px; font-size: 13px;"
        )
        self._model_info.setWordWrap(True)
        layout.addWidget(self._model_info)

        btn_train = PrimaryButton("↻  Retrain Model Now")
        btn_train.setFixedWidth(220)
        btn_train.clicked.connect(self._retrain)
        layout.addWidget(btn_train)

        layout.addSpacing(16)

        # ── Email settings ─────────────────────────────────────────────────────
        email_lbl = QLabel("EMAIL REPORTS")
        email_lbl.setObjectName("section_label")
        layout.addWidget(email_lbl)

        from config.admin_settings import EMAIL_ENABLED, EMAIL_SENDER, EMAIL_RECEIVER
        email_info = QLabel(
            f"Status:    {'✓ Enabled' if EMAIL_ENABLED else '✗ Disabled'}\n"
            f"Sender:    {EMAIL_SENDER}\n"
            f"Receiver:  {EMAIL_RECEIVER}\n\n"
            "To enable email reports:\n"
            "  1. Open config/admin_settings.py\n"
            "  2. Set EMAIL_ENABLED = True\n"
            "  3. Fill in EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER\n"
            "  4. Use a Gmail App Password (not your login password)"
        )
        email_info.setStyleSheet(
            "color: #64748B; background-color: #0A0F1A;"
            "border-radius: 8px; padding: 16px;"
            "font-family: 'Consolas','Courier New',monospace; font-size: 12px;"
        )
        email_info.setWordWrap(True)
        layout.addWidget(email_info)

        layout.addSpacing(16)

        # ── Paths ──────────────────────────────────────────────────────────────
        paths_lbl = QLabel("CONFIGURED PATHS")
        paths_lbl.setObjectName("section_label")
        layout.addWidget(paths_lbl)

        from config.settings import USERS_CSV, ATTENDANCE_CSV, ENCODINGS_PKL, DATASET_DIR
        paths_display = QLabel(
            f"Users CSV:       {USERS_CSV}\n"
            f"Attendance CSV:  {ATTENDANCE_CSV}\n"
            f"Encodings:       {ENCODINGS_PKL}\n"
            f"Dataset:         {DATASET_DIR}"
        )
        paths_display.setStyleSheet(
            "color: #475569; background-color: #0A0F1A;"
            "border-radius: 8px; padding: 16px;"
            "font-family: 'Consolas','Courier New',monospace; font-size: 12px;"
        )
        layout.addWidget(paths_display)
        layout.addStretch()
        return w

    # ══════════════════════════════════════════════════════════════════════════
    # Navigation
    # ══════════════════════════════════════════════════════════════════════════

    def _navigate(self, index: int):
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._page_buttons):
            btn.set_active(i == index)

        if index == 0:
            self._refresh_dashboard()
        elif index == 1:
            self._attendance_page.refresh()
        elif index == 3:
            self._refresh_users_table()
        elif index == 4:
            self._refresh_reports_table()
        elif index == 5:
            self._stats_page.refresh()
        elif index == 6:
            self._refresh_settings()

    # ══════════════════════════════════════════════════════════════════════════
    # Data refresh
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_dashboard(self):
        today   = get_attendance_today()
        stats   = get_training_stats()
        entries = sum(1 for r in today if r["type"] == "ENTRY")

        self._d_stat_users[0].setText(str(get_user_count()))
        self._d_stat_today[0].setText(str(len(today)))
        self._d_stat_entries[0].setText(str(entries))
        self._d_stat_encodings[0].setText(str(stats["total"]))
        self._dash_date.setText(current_date())

        self._dash_table.setRowCount(0)
        for rec in reversed(today[-20:]):
            self._append_table_row(
                self._dash_table,
                [friendly_time(rec["timestamp"]), rec["name"], rec["type"], rec["log_id"]],
                type_col=2,
            )

    def _refresh_users_table(self):
        users = get_all_users()
        self._users_table.setRowCount(0)
        for u in users:
            self._append_table_row(
                self._users_table,
                [u["user_id"], u["name"], u["registered_at"], u["image_path"]],
            )

    def _refresh_reports_table(self):
        records = get_all_attendance()
        self._reports_table.setRowCount(0)
        for rec in reversed(records):
            ts = rec["timestamp"]
            self._append_table_row(
                self._reports_table,
                [rec["date"], ts.split(" ")[1] if " " in ts else ts,
                 rec["user_id"], rec["name"], rec["type"], rec["log_id"]],
                type_col=4,
            )

    def _refresh_settings(self):
        stats = get_training_stats()
        if stats["exists"]:
            lines = [f"✓  {stats['total']} encodings across {stats['unique_users']} user(s)", ""]
            for u in stats["users"]:
                lines.append(f"  ID {u['user_id']}  {u['name']}  —  {u['count']} images")
            self._model_info.setText("\n".join(lines))
        else:
            self._model_info.setText("✗  No trained model found. Register users and click Retrain.")

    # ══════════════════════════════════════════════════════════════════════════
    # Actions
    # ══════════════════════════════════════════════════════════════════════════

    def _open_register_dialog(self):
        from gui.register_window import RegisterWindow
        dlg = RegisterWindow(self)
        dlg.user_registered.connect(self._on_user_registered)
        dlg.exec_()

    @pyqtSlot(int, str)
    def _on_user_registered(self, user_id: int, name: str):
        self._status_bar.showMessage(f"User '{name}' (ID {user_id}) registered.")
        self._refresh_dashboard()

    def _delete_selected_user(self):
        row = self._users_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No selection", "Please select a user to delete.")
            return
        uid  = self._users_table.item(row, 0).text()
        name = self._users_table.item(row, 1).text()
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete user '{name}' (ID {uid}) and all their data?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        if delete_user(int(uid)):
            from models.face_model import remove_user_encodings
            remove_user_encodings(int(uid))
            self._refresh_users_table()
            self._status_bar.showMessage(f"User {uid} deleted.")
        else:
            QMessageBox.warning(self, "Error", "Could not delete user.")

    def _retrain(self):
        self._status_bar.showMessage("Training… please wait.")
        ok, msg = train()
        self._status_bar.showMessage(msg)
        if hasattr(self, "_model_info"):
            self._refresh_settings()
        QMessageBox.information(self, "Training Result", msg)

    def _export_csv(self):
        import shutil
        from config.settings import ATTENDANCE_CSV
        from PyQt5.QtWidgets import QFileDialog
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Attendance CSV", "attendance_export.csv", "CSV files (*.csv)"
        )
        if dest:
            shutil.copy2(ATTENDANCE_CSV, dest)
            QMessageBox.information(self, "Exported", f"Saved to:\n{dest}")

    def _email_report(self):
        from core.email_reporter import send_report
        from utils.time_utils import current_date
        today = current_date()
        # Default: last 30 days
        from datetime import datetime, timedelta
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        result = send_report(from_date, today)
        if result["success"]:
            QMessageBox.information(self, "Email Sent", result["message"])
        else:
            QMessageBox.warning(self, "Email Failed", result["message"])

    def _scan_cameras(self):
        self._cam_status.setText("Scanning… please wait.")
        from core.camera_manager import CameraManager
        self._camera_mgr = CameraManager()
        cameras = self._camera_mgr.scan()
        self._camera_combo.clear()
        if cameras:
            for c in cameras:
                self._camera_combo.addItem(c["label"], c["index"])
            self._cam_status.setText(f"{len(cameras)} camera(s) detected.")
        else:
            self._camera_combo.addItem("No cameras found")
            self._cam_status.setText("No cameras detected. Check connections.")

    def _apply_camera(self):
        if not hasattr(self, "_camera_mgr"):
            QMessageBox.information(self, "Scan First", "Click 'Scan Cameras' first.")
            return
        idx = self._camera_combo.currentData()
        if idx is None:
            return
        import config.settings as S
        S.CAMERA_INDEX = idx
        self._cam_status.setText(f"Camera {idx} set as active. Restart attendance scanner.")
        self._status_bar.showMessage(f"Camera switched to index {idx}.")

    def _logout(self):
        confirm = QMessageBox.question(
            self, "Logout", "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        if hasattr(self, "_attendance_page"):
            self._attendance_page.cleanup()

        AdminSession.logout()
        self.close()

        # Show login again
        from PyQt5.QtWidgets import QApplication
        from gui.login_window import LoginWindow
        login = LoginWindow()
        if login.exec_() == login.Accepted:
            new_window = MainWindow()
            new_window.show()
            # Keep reference so it doesn't get garbage collected
            QApplication.instance().main_window = new_window

    # ══════════════════════════════════════════════════════════════════════════
    # Shared helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _make_log_table(self, headers: list) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        t.setShowGrid(False)
        return t

    def _append_table_row(self, table: QTableWidget, values: list, type_col: int = -1):
        row = table.rowCount()
        table.insertRow(row)
        for col, val in enumerate(values):
            item = QTableWidgetItem(str(val))
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            if col == type_col:
                is_entry = str(val) == "ENTRY"
                item.setForeground(QColor("#6EE7B7" if is_entry else "#C4B5FD"))
                item.setBackground(QColor("#064E3B" if is_entry else "#3B0764"))
            table.setItem(row, col, item)
        table.setRowHeight(row, 38)

    def _update_clock(self):
        from utils.time_utils import current_timestamp
        self._clock_label.setText(current_timestamp())

    def closeEvent(self, event):
        if hasattr(self, "_attendance_page"):
            self._attendance_page.cleanup()
        super().closeEvent(event)
