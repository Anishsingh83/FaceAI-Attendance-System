"""
main.py
FaceAI Attendance System — entry point.
"""

import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config.settings import STYLE_QSS, APP_NAME
from gui.main_window import MainWindow


def load_stylesheet(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    qss = load_stylesheet(STYLE_QSS)
    if qss:
        app.setStyleSheet(qss)

    app.setFont(QFont("Segoe UI", 13))

    from gui.login_window import LoginWindow
    login = LoginWindow()
    if login.exec_() != login.Accepted:
        sys.exit(0)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
