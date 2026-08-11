"""
ui/widgets/kpi_card.py
------------------------
Small "at a glance" statistic card used on the Dashboard.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel


class KpiCard(QFrame):
    def __init__(self, title: str, value, accent_color: str = "#0F5FA8", suffix: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setMinimumHeight(92)
        self.suffix = suffix

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        stripe = QFrame()
        stripe.setFixedSize(4, 26)
        stripe.setStyleSheet(f"background-color: {accent_color}; border-radius: 2px;")
        top_row.addWidget(stripe)
        top_row.addSpacing(10)

        self._value_label = QLabel(f"{value}{suffix}")
        self._value_label.setObjectName("kpiValue")
        self._value_label.setStyleSheet(f"color: {accent_color};")
        top_row.addWidget(self._value_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        title_label = QLabel(title.upper())
        title_label.setObjectName("kpiLabel")
        layout.addWidget(title_label)

    def set_value(self, value):
        self._value_label.setText(f"{value}{self.suffix}")
