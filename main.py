#!/usr/bin/env python3
"""
main.py
--------
Entry point for the Transfer Management System desktop application.

Run with:
    python main.py

On first run, the app creates a local SQLite database under ./data/.
Go to Settings to point it at a shared network folder so your whole
team works from the same data.
"""
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon

import config
from database.base import init_engine
from ui.main_window import MainWindow


def main():
    init_engine()

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setOrganizationName(config.APP_ORG)
    app.setFont(QFont("Segoe UI", 10))

    icon_path = config.resource_path("resources", "icons", "app_icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(app)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
