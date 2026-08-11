"""
ui/views/oem_dialog.py
-------------------------
Small dialog for adding/editing a single OEM Approval row under PTT
Approval's Step 2. The OEM table itself is read-only (see
ui/views/preparation_view.py) - all editing of an OEM's status, due
date, approval date and comments happens here, opened by double-clicking
a row or via "Edit Selected OEM".
"""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox

from models.preparation import OEMApproval
from ui.widgets.dynamic_form import DynamicForm, FieldSpec
from utils import constants


def _oem_fields():
    return [
        FieldSpec("oem_name", "OEM Name", "text"),
        FieldSpec("status", "Status", "combo", constants.STATUS_NOT_ONGOING_APPROVED_REJECTED),
        FieldSpec("due_date", "Due Date", "date"),
        FieldSpec("approval_date", "Approval Date", "date"),
        FieldSpec("comments", "Comments", "textarea"),
    ]


class OEMApprovalDialog(QDialog):
    def __init__(self, oem: OEMApproval, parent=None):
        super().__init__(parent)
        self.oem = oem
        self.setWindowTitle("Edit OEM Approval" if oem.oem_name else "Add OEM Approval")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        heading = QLabel("OEM Approval")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        self.form = DynamicForm(_oem_fields())
        self.form.load(oem)
        layout.addWidget(self.form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _on_save(self):
        if not self.form.widgets["oem_name"].text().strip():
            QMessageBox.warning(self, "Missing field", "OEM Name is required.")
            return
        self.form.save(self.oem)
        self.accept()
