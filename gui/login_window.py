"""
gui/login_window.py
Admin login dialog shown on app startup.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QKeyEvent

from core.admin_auth import AdminSession
from gui.components.buttons import PrimaryButton, SecondaryButton


class LoginWindow(QDialog):
    """
    Blocking login dialog. Closes with accept() on success.
    If user cancels, the app should exit.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FaceAI Attendance — Admin Login")
        self.setFixedSize(420, 520)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._attempts = 0
        self._locked   = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)

        # Logo / App name
        logo = QLabel("⬡")
        logo.setFont(QFont("Segoe UI", 40))
        logo.setStyleSheet("color: #38BDF8;")
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        title = QLabel("FaceAI Attendance")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC; margin-top: 8px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Admin Login")
        sub.setStyleSheet("color: #475569; font-size: 12px; margin-bottom: 36px;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(24)

        # Username
        u_lbl = QLabel("USERNAME")
        u_lbl.setObjectName("section_label")
        layout.addWidget(u_lbl)
        layout.addSpacing(6)

        self._username = QLineEdit()
        self._username.setPlaceholderText("Enter username")
        self._username.setMinimumHeight(42)
        self._username.setText("admin")
        layout.addWidget(self._username)
        layout.addSpacing(20)

        # Password
        p_lbl = QLabel("PASSWORD")
        p_lbl.setObjectName("section_label")
        layout.addWidget(p_lbl)
        layout.addSpacing(6)

        self._password = QLineEdit()
        self._password.setPlaceholderText("Enter password")
        self._password.setEchoMode(QLineEdit.Password)
        self._password.setMinimumHeight(42)
        self._password.returnPressed.connect(self._attempt_login)
        layout.addWidget(self._password)
        layout.addSpacing(8)

        # Error label
        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet("color: #EF4444; font-size: 12px;")
        self._error_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._error_lbl)

        layout.addSpacing(24)

        # Login button
        self._btn_login = PrimaryButton("Login")
        self._btn_login.setMinimumHeight(44)
        self._btn_login.clicked.connect(self._attempt_login)
        layout.addWidget(self._btn_login)

        layout.addSpacing(10)

        btn_exit = SecondaryButton("Exit")
        btn_exit.clicked.connect(self.reject)
        layout.addWidget(btn_exit)

        layout.addStretch()

        # Default hint
        hint = QLabel("Default: admin / faceai@123")
        hint.setStyleSheet("color: #1E293B; font-size: 10px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        self._password.setFocus()

    def _attempt_login(self):
        if self._locked:
            return

        username = self._username.text().strip()
        password = self._password.text()

        if not username or not password:
            self._show_error("Please enter both username and password.")
            return

        result = AdminSession.login(username, password)
        if result["success"]:
            self.accept()
        else:
            self._attempts += 1
            if self._attempts >= 5:
                self._lockout()
            else:
                remaining = 5 - self._attempts
                self._show_error(
                    f"Invalid credentials. {remaining} attempt(s) remaining."
                )
                self._password.clear()
                self._password.setFocus()

    def _show_error(self, msg: str):
        self._error_lbl.setText(msg)
        # Flash the password field red
        original = self._password.styleSheet()
        self._password.setStyleSheet(original + "border-color: #EF4444;")
        QTimer.singleShot(800, lambda: self._password.setStyleSheet(original))

    def _lockout(self):
        """Lock out after 5 failed attempts for 30 seconds."""
        self._locked = True
        self._btn_login.setEnabled(False)
        self._username.setEnabled(False)
        self._password.setEnabled(False)
        self._show_error("Too many attempts. Locked for 30 seconds.")

        countdown = [30]
        def tick():
            countdown[0] -= 1
            if countdown[0] <= 0:
                self._locked = False
                self._attempts = 0
                self._btn_login.setEnabled(True)
                self._username.setEnabled(True)
                self._password.setEnabled(True)
                self._password.clear()
                self._error_lbl.setText("")
                self._password.setFocus()
            else:
                self._show_error(f"Too many attempts. Locked for {countdown[0]}s.")
                QTimer.singleShot(1000, tick)
        QTimer.singleShot(1000, tick)
