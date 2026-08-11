"""
ui/widgets/badge.py
---------------------
Small coloured pill label for status values, following the spec's
colour indicator scheme: Green=Completed, Yellow=Ongoing, Red=Delayed,
Grey=Not Started (and a few extra states mapped sensibly - see
utils.constants.STATUS_COLOR_MAP).
"""
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

from utils.constants import color_for_status


class Badge(QLabel):
    def __init__(self, text: str, color: str = "#8A8886", parent=None):
        super().__init__(text, parent)
        self.setProperty("badge", "true")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"background-color: {color}; color: white; border-radius: 9px; "
            f"padding: 3px 10px; font-weight: 600; font-size: 11px;"
        )


def status_badge(status: str) -> Badge:
    return Badge(status, color_for_status(status))
