"""
ui/views/reports_view.py
----------------------------
Export/print hub: full Transfers export to Excel, and a print/preview
option for the same data through the OS print dialog.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QMessageBox
from PySide6.QtCore import Qt

from database.base import new_session
from services import transfer_service as svc
from reports.excel_export import export_transfers_to_excel
from reports.print_service import preview_table, print_table
from ui.widgets.badge import status_badge
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView


class ReportOptionCard(QFrame):
    def __init__(self, title, description, button_text, on_click, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 18, 20, 18)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("sectionTitle")
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: #888; font-size: 12px;")
        desc_lbl.setWordWrap(True)

        btn = QPushButton(button_text)
        btn.setObjectName("primaryButton")
        btn.clicked.connect(on_click)

        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addStretch()
        layout.addWidget(btn, alignment=Qt.AlignLeft)


class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = new_session()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QVBoxLayout()
        title = QLabel("Reports")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Export and print transfer data")
        subtitle.setObjectName("pageSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(ReportOptionCard(
            "Export to Excel", "Export every Transfer (flattened by Tool / Part Number) "
            "with all status fields as a formatted .xlsx workbook.", "Export Excel", self._export_excel,
        ))
        row.addWidget(ReportOptionCard(
            "Print Preview", "Preview and print the full Transfers list through your "
            "system's print dialog.", "Open Preview", self._print_preview,
        ))
        layout.addLayout(row)
        layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #1E8E3E; font-weight: 600;")
        layout.addWidget(self.status_label)

    def _build_print_table(self) -> QTableWidget:
        self.session.close()
        self.session = new_session()
        transfers = svc.list_transfers(self.session)
        table = QTableWidget(len(transfers), 8)
        table.setHorizontalHeaderLabels(["TRF Number", "Planned Date", "Type", "Activity", "Status", "Prep %", "Release %", "Tool Number(s)"])
        for row, t in enumerate(transfers):
            table.setItem(row, 0, QTableWidgetItem(t.trf_number))
            table.setItem(row, 1, QTableWidgetItem(t.planned_transfer_date.isoformat() if t.planned_transfer_date else "-"))
            table.setItem(row, 2, QTableWidgetItem(t.transfer_type))
            table.setItem(row, 3, QTableWidgetItem(t.activity))
            table.setItem(row, 4, QTableWidgetItem(t.status))
            table.setItem(row, 5, QTableWidgetItem(f"{t.preparation_progress:.0f}%"))
            table.setItem(row, 6, QTableWidgetItem(f"{t.release_progress:.0f}%"))
            table.setItem(row, 7, QTableWidgetItem(", ".join(tool.tool_number for tool in t.tools) or "-"))
        return table

    def _export_excel(self):
        self.session.close()
        self.session = new_session()
        transfers = svc.list_transfers(self.session)
        path = export_transfers_to_excel(transfers)
        self.status_label.setText(f"Saved: {path}")
        QMessageBox.information(self, "Export complete", f"Report saved to:\n{path}")

    def _print_preview(self):
        table = self._build_print_table()
        preview_table(self, table, "Transfer Management System - Transfers Report")
