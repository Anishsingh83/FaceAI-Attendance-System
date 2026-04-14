"""
gui/components/buttons.py
Reusable, pre-styled PyQt5 button widgets.
Import these instead of creating raw QPushButton instances in windows.
"""

from PyQt5.QtWidgets import QPushButton, QSizePolicy
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QCursor


class PrimaryButton(QPushButton):
    """Sky-blue primary action button."""
    def __init__(self, text: str, parent=None, icon: QIcon = None):
        super().__init__(text, parent)
        self.setObjectName("btn_primary")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(38)
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(16, 16))


class SuccessButton(QPushButton):
    """Green confirmation / proceed button."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("btn_success")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(38)


class DangerButton(QPushButton):
    """Red destructive action button."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("btn_danger")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(38)


class SecondaryButton(QPushButton):
    """Neutral secondary / cancel button."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(38)


class SidebarButton(QPushButton):
    """Left-aligned navigation button for the sidebar."""
    def __init__(self, text: str, parent=None, active: bool = False):
        super().__init__(text, parent)
        self._active = active
        self._apply_style()
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_style()

    def _apply_style(self) -> None:
        name = "btn_sidebar_active" if self._active else "btn_sidebar"
        self.setObjectName(name)
        # Force stylesheet re-evaluation
        self.style().unpolish(self)
        self.style().polish(self)
