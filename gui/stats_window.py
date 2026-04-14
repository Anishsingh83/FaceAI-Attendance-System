"""
gui/stats_window.py
Attendance percentage calculator page — date range picker + per-user stats table.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QFrame, QAbstractItemView, QProgressBar,
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont

from core.attendance_stats import calculate_attendance_percentage, get_daily_summary
from gui.components.buttons import PrimaryButton, SecondaryButton
from utils.time_utils import current_date
from utils.helpers import log_info


class StatsWindow(QWidget):
    """Attendance percentage page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        # Header
        title = QLabel("Attendance Statistics")
        title.setObjectName("title_label")
        layout.addWidget(title)

        # Date range row
        date_frame = QFrame()
        date_frame.setStyleSheet(
            "background-color: #111827; border-radius: 10px; padding: 4px;"
        )
        date_row = QHBoxLayout(date_frame)
        date_row.setContentsMargins(16, 12, 16, 12)
        date_row.setSpacing(16)

        date_row.addWidget(QLabel("From:"))
        self._from_date = QDateEdit()
        self._from_date.setCalendarPopup(True)
        self._from_date.setDate(QDate.currentDate().addDays(-30))
        self._from_date.setDisplayFormat("yyyy-MM-dd")
        self._from_date.setMinimumHeight(36)
        date_row.addWidget(self._from_date)

        date_row.addWidget(QLabel("To:"))
        self._to_date = QDateEdit()
        self._to_date.setCalendarPopup(True)
        self._to_date.setDate(QDate.currentDate())
        self._to_date.setDisplayFormat("yyyy-MM-dd")
        self._to_date.setMinimumHeight(36)
        date_row.addWidget(self._to_date)

        btn_calc = PrimaryButton("Calculate")
        btn_calc.clicked.connect(self._calculate)
        date_row.addWidget(btn_calc)

        btn_today = SecondaryButton("This Month")
        btn_today.clicked.connect(self._set_this_month)
        date_row.addWidget(btn_today)

        date_row.addStretch()
        layout.addWidget(date_frame)

        # Summary cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self._card_present  = self._stat_card("—", "Avg Present Days", "#10B981")
        self._card_pct      = self._stat_card("—", "Avg Attendance %", "#38BDF8")
        self._card_good     = self._stat_card("—", "Good (≥75%)",       "#6EE7B7")
        self._card_low      = self._stat_card("—", "Low (<50%)",         "#EF4444")
        for c in (self._card_present, self._card_pct, self._card_good, self._card_low):
            cards_row.addWidget(c[2])
        layout.addLayout(cards_row)

        # Table
        tbl_lbl = QLabel("PER USER BREAKDOWN")
        tbl_lbl.setObjectName("section_label")
        layout.addWidget(tbl_lbl)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["ID", "Name", "Present", "Total Days", "Percentage", "Status"]
        )
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        layout.addWidget(self._table)

        # Auto-calculate on load
        self._calculate()

    def _stat_card(self, value, label, color):
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: #111827; border-radius: 10px;"
            f"border-left: 3px solid {color};"
        )
        frame.setFixedHeight(80)
        vl = QVBoxLayout(frame)
        vl.setContentsMargins(16, 10, 12, 10)
        v = QLabel(value)
        v.setFont(QFont("Segoe UI", 20, QFont.Bold))
        v.setStyleSheet(f"color: {color}; border: none;")
        l = QLabel(label)
        l.setStyleSheet("color: #64748B; font-size: 11px; border: none;")
        vl.addWidget(v)
        vl.addWidget(l)
        return v, l, frame

    def _set_this_month(self):
        today = QDate.currentDate()
        self._from_date.setDate(QDate(today.year(), today.month(), 1))
        self._to_date.setDate(today)
        self._calculate()

    def _calculate(self):
        from_str = self._from_date.date().toString("yyyy-MM-dd")
        to_str   = self._to_date.date().toString("yyyy-MM-dd")

        results = calculate_attendance_percentage(from_str, to_str)
        self._table.setRowCount(0)

        if not results:
            return

        good_count = sum(1 for r in results if r["status"] == "Good")
        low_count  = sum(1 for r in results if r["status"] == "Low")
        avg_pct    = round(sum(r["percentage"] for r in results) / len(results), 1)
        avg_present= round(sum(r["present"]    for r in results) / len(results), 1)

        self._card_present[0].setText(str(avg_present))
        self._card_pct[0].setText(f"{avg_pct}%")
        self._card_good[0].setText(str(good_count))
        self._card_low[0].setText(str(low_count))

        for r in results:
            row = self._table.rowCount()
            self._table.insertRow(row)

            pct_color = (
                "#6EE7B7" if r["status"] == "Good" else
                "#FCD34D" if r["status"] == "Average" else
                "#FCA5A5"
            )

            values = [
                str(r["user_id"]), r["name"],
                str(r["present"]), str(r["total"]),
                f"{r['percentage']}%", r["status"],
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col in (4, 5):
                    item.setForeground(QColor(pct_color))
                self._table.setItem(row, col, item)
            self._table.setRowHeight(row, 42)

    def refresh(self):
        self._calculate()
