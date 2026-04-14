"""
gui/components/camera_frame.py
QLabel subclass that displays a live OpenCV camera feed inside any PyQt5 layout.
The parent window supplies frames; this widget just renders them.
"""

import numpy as np
import cv2
from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QFont

from config.settings import CAMERA_DISPLAY_W, CAMERA_DISPLAY_H


class CameraFrame(QLabel):
    """
    A QLabel that displays BGR OpenCV frames scaled to fit its size.
    Call update_frame(bgr_array) to push a new frame.
    Call show_placeholder() to display a static 'camera off' screen.
    """

    def __init__(self, parent=None,
                 width: int = CAMERA_DISPLAY_W,
                 height: int = CAMERA_DISPLAY_H):
        super().__init__(parent)
        self._display_w = width
        self._display_h = height
        self.setFixedSize(width, height)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setStyleSheet(
            "background-color: #080C14;"
            "border: 1px solid #1E293B;"
            "border-radius: 10px;"
        )
        self.show_placeholder()

    # ── Public API ─────────────────────────────────────────────────────────────

    def update_frame(self, frame: np.ndarray) -> None:
        """Push a BGR OpenCV frame to the display."""
        if frame is None:
            return
        # Convert BGR → RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image).scaled(
            self._display_w, self._display_h,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(pixmap)

    def show_placeholder(self, message: str = "Camera is off") -> None:
        """Display a dark placeholder with a centred message."""
        pixmap = QPixmap(self._display_w, self._display_h)
        pixmap.fill(QColor("#080C14"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw a subtle camera icon outline
        pen_color = QColor("#1E293B")
        painter.setPen(pen_color)
        painter.setBrush(QColor("#0F1822"))
        cx, cy = self._display_w // 2, self._display_h // 2
        painter.drawRoundedRect(cx - 50, cy - 35, 100, 70, 10, 10)
        painter.drawEllipse(cx - 18, cy - 18, 36, 36)

        # Message text
        font = QFont("Segoe UI", 11)
        painter.setFont(font)
        painter.setPen(QColor("#334155"))
        painter.drawText(
            0, cy + 60, self._display_w, 30,
            Qt.AlignHCenter | Qt.AlignTop,
            message,
        )
        painter.end()
        self.setPixmap(pixmap)

    def show_error(self, message: str = "Camera error") -> None:
        """Display a red-tinted error placeholder."""
        pixmap = QPixmap(self._display_w, self._display_h)
        pixmap.fill(QColor("#1A0A0A"))
        painter = QPainter(pixmap)
        font = QFont("Segoe UI", 12)
        painter.setFont(font)
        painter.setPen(QColor("#EF4444"))
        painter.drawText(
            pixmap.rect(), Qt.AlignCenter, f"⚠  {message}"
        )
        painter.end()
        self.setPixmap(pixmap)

    def sizeHint(self) -> QSize:
        return QSize(self._display_w, self._display_h)
