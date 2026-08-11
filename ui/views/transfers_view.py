"""
ui/views/transfers_view.py
-----------------------------
Main Transfers grid: search, filters (type/activity/status/locations),
sorting, create/edit/delete/duplicate, export to Excel, and printing.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QProgressBar, QComboBox, QMenu,
)
from PySide6.QtCore import Qt

from database.base import new_session
from services import transfer_service as svc
from ui.views.transfer_dialog import TransferDialog
from ui.widgets.badge import status_badge
from reports.excel_export import export_transfers_to_excel
from reports.print_service import print_table, preview_table
from utils import constants

COLUMNS = [
    "TRF Number", "Planned Date", "Type", "Activity", "Sender", "Receiver",
    "Technology", "Status", "Preparation %", "Release %", "Tool Number(s)",
]


class TransfersView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = new_session()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QVBoxLayout()
        title = QLabel("Transfers")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Create, edit and track every transfer project")
        subtitle.setObjectName("pageSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search TRF number, location, technology...")
        self.search_edit.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search_edit, 2)

        self.type_filter = _combo_with_blank("All Types", constants.TRANSFER_TYPES)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.type_filter)

        self.activity_filter = _combo_with_blank("All Activities", constants.ACTIVITIES)
        self.activity_filter.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.activity_filter)

        self.status_filter = _combo_with_blank("All Statuses", constants.TRANSFER_STATUSES)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.status_filter)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Sort: Planned Date", "planned_transfer_date")
        self.sort_combo.addItem("Sort: TRF Number", "trf_number")
        self.sort_combo.addItem("Sort: Status", "status")
        self.sort_combo.addItem("Sort: Preparation %", "preparation_progress")
        self.sort_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.sort_combo)

        new_btn = QPushButton("+ New Transfer")
        new_btn.setObjectName("primaryButton")
        new_btn.clicked.connect(self._on_new)
        toolbar.addWidget(new_btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self.table)

        action_row = QHBoxLayout()
        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self._on_edit)
        dup_btn = QPushButton("Duplicate Selected")
        dup_btn.clicked.connect(self._on_duplicate)
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._on_delete)
        export_btn = QPushButton("Export to Excel")
        export_btn.clicked.connect(self._on_export)
        print_btn = QPushButton("Print / Preview")
        print_btn.clicked.connect(self._on_print)

        action_row.addWidget(edit_btn)
        action_row.addWidget(dup_btn)
        action_row.addWidget(delete_btn)
        action_row.addWidget(export_btn)
        action_row.addWidget(print_btn)
        action_row.addStretch()
        self.count_label = QLabel("")
        action_row.addWidget(self.count_label)
        layout.addLayout(action_row)

    # ------------------------------------------------------------------ #
    def refresh(self):
        self.session.close()
        self.session = new_session()
        transfers = svc.list_transfers(
            self.session,
            search=self.search_edit.text().strip(),
            transfer_type=self.type_filter.currentData() or "",
            activity=self.activity_filter.currentData() or "",
            status=self.status_filter.currentData() or "",
            sort_by=self.sort_combo.currentData() or "planned_transfer_date",
        )
        self._transfers = transfers

        self.table.setRowCount(len(transfers))
        for row, t in enumerate(transfers):
            self.table.setItem(row, 0, QTableWidgetItem(t.trf_number))
            self.table.setItem(row, 1, QTableWidgetItem(t.planned_transfer_date.isoformat() if t.planned_transfer_date else "-"))
            self.table.setItem(row, 2, QTableWidgetItem(t.transfer_type))
            self.table.setItem(row, 3, QTableWidgetItem(t.activity))
            self.table.setItem(row, 4, QTableWidgetItem(t.sender_location or "-"))
            self.table.setItem(row, 5, QTableWidgetItem(t.receiver_location or "-"))
            self.table.setItem(row, 6, QTableWidgetItem(t.technology or "-"))
            self.table.setCellWidget(row, 7, status_badge(t.status))

            prep_bar = QProgressBar()
            prep_bar.setRange(0, 100)
            prep_bar.setValue(int(t.preparation_progress))
            self.table.setCellWidget(row, 8, prep_bar)

            rel_bar = QProgressBar()
            rel_bar.setRange(0, 100)
            rel_bar.setValue(int(t.release_progress))
            self.table.setCellWidget(row, 9, rel_bar)

            tool_numbers = ", ".join(tool.tool_number for tool in t.tools) or "-"
            self.table.setItem(row, 10, QTableWidgetItem(tool_numbers))
            self.table.item(row, 0).setData(Qt.UserRole, t.id)

        self.count_label.setText(f"{len(transfers)} transfer(s)")

    def _selected_transfer_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def _on_new(self):
        dialog = TransferDialog(transfer_id=None, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_edit(self):
        tid = self._selected_transfer_id()
        if tid is None:
            QMessageBox.information(self, "No selection", "Select a transfer row first.")
            return
        dialog = TransferDialog(transfer_id=tid, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_duplicate(self):
        tid = self._selected_transfer_id()
        if tid is None:
            QMessageBox.information(self, "No selection", "Select a transfer row first.")
            return
        with_session = new_session()
        dup = svc.duplicate_transfer(with_session, tid)
        with_session.commit()
        with_session.close()
        if dup:
            QMessageBox.information(self, "Duplicated", f"Created {dup.trf_number}.")
        self.refresh()

    def _on_delete(self):
        tid = self._selected_transfer_id()
        if tid is None:
            QMessageBox.information(self, "No selection", "Select a transfer row first.")
            return
        confirm = QMessageBox.question(
            self, "Confirm delete",
            "Delete this transfer and all its Tools, Part Numbers, Preparation and Release data? This cannot be undone.",
        )
        if confirm == QMessageBox.Yes:
            with_session = new_session()
            svc.delete_transfer(with_session, tid)
            with_session.commit()
            with_session.close()
            self.refresh()

    def _on_export(self):
        path = export_transfers_to_excel(self._transfers)
        QMessageBox.information(self, "Export complete", f"Saved to:\n{path}")

    def _on_print(self):
        preview_table(self, self.table, "Transfer Management System - Transfers")

    def current_transfers(self):
        return getattr(self, "_transfers", [])


def _combo_with_blank(placeholder: str, options: list[str]) -> QComboBox:
    combo = QComboBox()
    combo.addItem(placeholder, "")
    for o in options:
        combo.addItem(o, o)
    return combo
