"""
ui/views/notifications_view.py
----------------------------------
Notification Center: automatic notifications for overdue activities
across every Preparation sub-module, plus upcoming deadlines.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt

from database.base import new_session
from services import notification_service

SEVERITY_COLOR = {"danger": "#D13438", "warning": "#F2A900"}
SEVERITY_LABEL = {"danger": "Overdue", "warning": "Due Soon"}


class NotificationCard(QFrame):
    def __init__(self, note, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        stripe = QFrame()
        stripe.setFixedWidth(4)
        stripe.setStyleSheet(f"background-color: {SEVERITY_COLOR[note.severity]}; border-radius: 2px;")
        layout.addWidget(stripe)

        text_col = QVBoxLayout()
        title = QLabel(note.title)
        title.setStyleSheet("font-weight: 600;")
        detail = QLabel(note.detail)
        detail.setStyleSheet("color: #888; font-size: 11px;")
        detail.setWordWrap(True)
        text_col.addWidget(title)
        text_col.addWidget(detail)
        layout.addLayout(text_col, 1)

        tag = QLabel(SEVERITY_LABEL[note.severity])
        tag.setProperty("badge", "true")
        tag.setStyleSheet(f"background-color: {SEVERITY_COLOR[note.severity]}; color: white; border-radius: 9px; padding: 3px 10px; font-size: 11px; font-weight: 600;")
        layout.addWidget(tag)


class NotificationsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = new_session()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(24, 20, 24, 20)
        self.layout_.setSpacing(14)

        header = QVBoxLayout()
        title = QLabel("Notification Center")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Automatic alerts for overdue activities across every module")
        subtitle.setObjectName("pageSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)

        refresh_row = QHBoxLayout()
        refresh_row.addLayout(header)
        refresh_row.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        refresh_row.addWidget(refresh_btn, alignment=Qt.AlignTop)
        self.layout_.addLayout(refresh_row)

        self.list_container = QVBoxLayout()
        self.list_container.setSpacing(8)
        self.layout_.addLayout(self.list_container)
        self.layout_.addStretch()

    def refresh(self):
        self.session.close()
        self.session = new_session()

        while self.list_container.count():
            item = self.list_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        notes = notification_service.build_notifications(self.session)
        if not notes:
            empty = QLabel("You're all caught up - no active notifications.")
            empty.setStyleSheet("color: #888; padding: 20px;")
            self.list_container.addWidget(empty)
            return

        for n in notes:
            self.list_container.addWidget(NotificationCard(n))
