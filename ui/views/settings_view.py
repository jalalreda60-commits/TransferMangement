"""
ui/views/settings_view.py
-----------------------------
Application settings: light/dark theme, notification window, and the
database location (local disk or shared network folder for multi-user
access - no cloud dependency).
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QComboBox, QSpinBox, QFormLayout,
)
from PySide6.QtCore import Qt, Signal

import config
from database.base import init_engine, new_session
from utils.excel_importer import import_workbook, ImportError_
from reports.excel_export import export_import_template


class SettingsView(QWidget):
    theme_changed = Signal(str)
    database_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = config.load_settings()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QVBoxLayout()
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Appearance, notifications and data storage")
        subtitle.setObjectName("pageSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        appearance_card = QFrame()
        appearance_card.setObjectName("card")
        a_layout = QVBoxLayout(appearance_card)
        a_title = QLabel("Appearance")
        a_title.setObjectName("sectionTitle")
        a_layout.addWidget(a_title)
        form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "light"))
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        form.addRow("Theme", self.theme_combo)

        self.notify_days_spin = QSpinBox()
        self.notify_days_spin.setRange(1, 60)
        self.notify_days_spin.setValue(self.settings.get("notify_days_before_due", 7))
        self.notify_days_spin.valueChanged.connect(self._on_notify_days_changed)
        form.addRow("Notify X days before due date", self.notify_days_spin)
        a_layout.addLayout(form)
        layout.addWidget(appearance_card)

        db_card = QFrame()
        db_card.setObjectName("card")
        db_layout = QVBoxLayout(db_card)
        db_title = QLabel("Database Location")
        db_title.setObjectName("sectionTitle")
        db_layout.addWidget(db_title)
        db_desc = QLabel(
            "Point every workstation at the same file on a shared network folder "
            "(e.g. \\\\server\\share\\TMS\\transfer_management.db) so the whole team "
            "works from a single, always-current database. No cloud service is used."
        )
        db_desc.setWordWrap(True)
        db_desc.setStyleSheet("color: #888; font-size: 12px;")
        db_layout.addWidget(db_desc)

        path_row = QHBoxLayout()
        self.db_path_edit = QLineEdit(self.settings.get("db_path", ""))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_db)
        apply_btn = QPushButton("Apply && Reconnect")
        apply_btn.setObjectName("primaryButton")
        apply_btn.clicked.connect(self._on_apply_db_path)
        path_row.addWidget(self.db_path_edit)
        path_row.addWidget(browse_btn)
        path_row.addWidget(apply_btn)
        db_layout.addLayout(path_row)
        layout.addWidget(db_card)

        import_card = QFrame()
        import_card.setObjectName("card")
        import_layout = QVBoxLayout(import_card)
        import_title = QLabel("Import from Excel")
        import_title.setObjectName("sectionTitle")
        import_layout.addWidget(import_title)
        import_desc = QLabel(
            "Bulk-load Transfers (with their Tools, Part Numbers, and the most commonly "
            "pre-filled Preparation fields) from an .xlsx workbook. Download the template "
            "first to see the exact expected columns - only 'TRF Number' and 'Tool Number' "
            "are required, everything else is optional. Import is additive: re-running it "
            "on the same file creates new records rather than updating existing ones."
        )
        import_desc.setWordWrap(True)
        import_desc.setStyleSheet("color: #888; font-size: 12px;")
        import_layout.addWidget(import_desc)

        import_btn_row = QHBoxLayout()
        template_btn = QPushButton("Download Import Template")
        template_btn.clicked.connect(self._on_download_template)
        import_btn = QPushButton("Import from Excel...")
        import_btn.setObjectName("primaryButton")
        import_btn.clicked.connect(self._on_import_excel)
        import_btn_row.addWidget(template_btn)
        import_btn_row.addWidget(import_btn)
        import_btn_row.addStretch()
        import_layout.addLayout(import_btn_row)
        layout.addWidget(import_card)

        layout.addStretch()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #1E8E3E; font-weight: 600;")
        layout.addWidget(self.status_label)

    def _on_theme_changed(self, theme: str):
        self.settings["theme"] = theme
        config.save_settings(self.settings)
        self.theme_changed.emit(theme)

    def _on_notify_days_changed(self, value: int):
        self.settings["notify_days_before_due"] = value
        config.save_settings(self.settings)

    def _on_browse_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Select or create database file", self.db_path_edit.text(),
            "SQLite Database (*.db)"
        )
        if path:
            self.db_path_edit.setText(path)

    def _on_apply_db_path(self):
        new_path = self.db_path_edit.text().strip()
        if not new_path:
            QMessageBox.warning(self, "Invalid path", "Please provide a database file path.")
            return
        try:
            config.set_db_path(new_path)
            init_engine(new_path)
        except Exception as e:
            QMessageBox.critical(self, "Connection failed", f"Could not open database at:\n{new_path}\n\n{e}")
            return
        self.status_label.setText(f"Connected to: {new_path}")
        QMessageBox.information(self, "Database connected", "The application is now using the selected database.\nAll users pointing at this same path will share this data.")
        self.database_changed.emit()

    def _on_download_template(self):
        path = export_import_template()
        self.status_label.setText(f"Template saved: {path}")
        QMessageBox.information(self, "Template saved", f"Import template saved to:\n{path}")

    def _on_import_excel(self):
        from pathlib import Path
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select workbook to import", str(Path.home()), "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        confirm = QMessageBox.question(
            self, "Confirm import",
            "This will add all transfers found in the workbook as new records "
            "(re-running on the same file will create duplicates). Continue?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            result = import_workbook(file_path)
        except ImportError_ as e:
            QMessageBox.warning(self, "Import failed", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Import failed", f"Could not import the workbook:\n{e}")
            return

        summary = (
            f"Imported {result['transfers_created']} transfer(s), "
            f"{result['tools_created']} tool(s), "
            f"{result['part_numbers_created']} part number(s)."
        )
        if result["rows_skipped"]:
            summary += f"\n{result['rows_skipped']} row(s) skipped (missing TRF Number or Tool Number)."
        self.status_label.setText(summary.replace(chr(10), " "))
        QMessageBox.information(self, "Import complete", summary)
        self.database_changed.emit()
