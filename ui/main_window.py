"""
ui/main_window.py
--------------------
Top-level QMainWindow: collapsible sidebar + stacked pages, theme
switching, and wiring between Settings (DB path / theme changes) and
every other view so everything refreshes consistently.
"""
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget

import config
from database.base import new_session
from ui.theme import apply_theme
from ui.widgets.sidebar import Sidebar, PREPARATION_SUBMODULES, PREPARATION_KEY
from services import notification_service

from ui.views.dashboard_view import DashboardView
from ui.views.transfers_view import TransfersView
from ui.views.preparation_view import PreparationView
from ui.views.release_view import ReleaseView
from ui.views.notifications_view import NotificationsView
from ui.views.reports_view import ReportsView
from ui.views.settings_view import SettingsView


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.settings = config.load_settings()
        self.dark_mode = self.settings.get("theme", "light") == "dark"

        self.setWindowTitle(f"{config.APP_NAME}")
        self.resize(1500, 940)

        self._build_ui()
        apply_theme(self.app, "dark" if self.dark_mode else "light")
        self._refresh_notification_badge()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self._on_navigate)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.dashboard_view = DashboardView(dark_mode=self.dark_mode)
        self.transfers_view = TransfersView()
        self.release_view = ReleaseView(dark_mode=self.dark_mode)
        self.notifications_view = NotificationsView()
        self.reports_view = ReportsView()
        self.settings_view = SettingsView()
        self.settings_view.theme_changed.connect(self._on_theme_changed)
        self.settings_view.database_changed.connect(self._on_database_changed)

        # One PreparationView instance per sub-module (each with its own
        # picker/form scope - see ui/views/preparation_view.py).
        self.preparation_views = {key: PreparationView(key, dark_mode=self.dark_mode) for key, _ in PREPARATION_SUBMODULES}

        self.pages = {
            "dashboard": self.dashboard_view,
            "transfers": self.transfers_view,
            "release": self.release_view,
            "notifications": self.notifications_view,
            "reports": self.reports_view,
            "settings": self.settings_view,
            **self.preparation_views,
        }
        for page in self.pages.values():
            self.stack.addWidget(page)

        # "Preparation" (the group header) lands on its first sub-module.
        self.stack.setCurrentWidget(self.dashboard_view)

    # ------------------------------------------------------------------ #
    def _on_navigate(self, key: str):
        if key == PREPARATION_KEY:
            key = PREPARATION_SUBMODULES[0][0]
            self.sidebar.set_active(key)

        page = self.pages.get(key)
        if not page:
            return
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(key)

        if key == "dashboard":
            self.dashboard_view.refresh()
        elif key == "transfers":
            self.transfers_view.refresh()
        elif key == "release":
            self.release_view.refresh()
        elif key == "notifications":
            self.notifications_view.refresh()
        elif key in self.preparation_views:
            self.preparation_views[key].refresh()
        self._refresh_notification_badge()

    def _refresh_notification_badge(self):
        session = new_session()
        try:
            counts = notification_service.counts_by_severity(session)
        finally:
            session.close()
        total = sum(counts.values())
        if total == 0:
            self.sidebar.set_notification_summary("No active alerts")
        else:
            self.sidebar.set_notification_summary(
                f"{total} alert(s): {counts['danger']} overdue, {counts['warning']} due soon"
            )

    def _on_theme_changed(self, theme: str):
        self.dark_mode = theme == "dark"
        apply_theme(self.app, theme)
        self.dashboard_view.set_dark_mode(self.dark_mode)
        self.release_view.set_dark_mode(self.dark_mode)
        for view in self.preparation_views.values():
            view.set_dark_mode(self.dark_mode)

    def _on_database_changed(self):
        """Called after the user re-points the app at a different
        database file - refresh every view's cached data."""
        self.dashboard_view.refresh()
        self.transfers_view.refresh()
        self.release_view.refresh()
        self.notifications_view.refresh()
        for view in self.preparation_views.values():
            view.refresh()
        self._refresh_notification_badge()
