"""
ui/views/transfer_dialog.py
------------------------------
Create/Edit dialog for a Transfer. Tabs:
  * Details          - TRF Number, planned date, type, activity, locations, technology
  * Tools & Parts     - tree editor: add/remove Tools, add/remove Part Numbers per Tool
  * Attachments       - linked documents
  * Comments          - threaded free-text notes
  * History           - activity log for this transfer

Editing a Transfer's Tools/Part Numbers here is what drives which rows
appear in every Preparation sub-module's entity picker (see
ui/views/preparation_view.py) - adding a Tool auto-provisions its
Safety Stock/Training records, and adding a Part Number auto-provisions
Raw Material/Pre-check/Applicator-or-CounterPart, via
services.transfer_service.ensure_related_records().
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QTabWidget, QWidget, QLabel, QListWidget,
    QListWidgetItem, QFileDialog, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QInputDialog, QAbstractItemView,
)
from PySide6.QtCore import Qt, QDate

from database.base import new_session
from models.transfer import Transfer, Tool, PartNumber
from services import transfer_service as svc
from utils import constants
import config


def _qdate_to_date(qd: QDate):
    if not qd or not qd.isValid():
        return None
    return qd.toPython()


def _date_to_qdate(d):
    if not d:
        return QDate.currentDate()
    return QDate(d.year, d.month, d.day)


class TransferDialog(QDialog):
    def __init__(self, transfer_id: int | None = None, parent=None):
        super().__init__(parent)
        self.is_new = transfer_id is None
        self.session = new_session()
        self.transfer = svc.get_transfer(self.session, transfer_id) if transfer_id else Transfer(
            transfer_type=constants.TRANSFER_TYPES[0], activity=constants.ACTIVITIES[0],
        )
        if self.is_new:
            svc.ensure_related_records(self.transfer)

        self.setWindowTitle("New Transfer" if self.is_new else f"Edit Transfer - {self.transfer.trf_number}")
        self.setMinimumSize(760, 640)

        self._build_ui()

    # ------------------------------------------------------------------ #
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        heading = QLabel("New Transfer" if self.is_new else "Edit Transfer")
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_details_tab(), "Details")
        self.tabs.addTab(self._build_tools_tab(), "Tools && Parts")
        if not self.is_new:
            self.tabs.addTab(self._build_attachments_tab(), "Attachments")
            self.tabs.addTab(self._build_comments_tab(), "Comments")
            self.tabs.addTab(self._build_history_tab(), "History")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Transfer")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _build_details_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        t = self.transfer
        self.trf_number_edit = QLineEdit(t.trf_number)
        self.planned_date_edit = QDateEdit(_date_to_qdate(t.planned_transfer_date))
        self.planned_date_edit.setCalendarPopup(True)
        self.actual_date_edit = QDateEdit(_date_to_qdate(t.actual_transfer_date))
        self.actual_date_edit.setCalendarPopup(True)

        self.transfer_type_combo = QComboBox()
        self.transfer_type_combo.addItems(constants.TRANSFER_TYPES)
        self.transfer_type_combo.setCurrentText(t.transfer_type or constants.TRANSFER_TYPES[0])

        self.activity_combo = QComboBox()
        self.activity_combo.addItems(constants.ACTIVITIES)
        self.activity_combo.setCurrentText(t.activity or constants.ACTIVITIES[0])

        self.sender_edit = QLineEdit(t.sender_location)
        self.receiver_edit = QLineEdit(t.receiver_location)
        self.technology_edit = QLineEdit(t.technology)

        form.addRow("TRF Number *", self.trf_number_edit)
        form.addRow("Planned Transfer Date", self.planned_date_edit)
        form.addRow("Actual Transfer Date", self.actual_date_edit)
        form.addRow("Transfer Type", self.transfer_type_combo)
        form.addRow("Activity", self.activity_combo)
        form.addRow("Sender Location", self.sender_edit)
        form.addRow("Receiver Location", self.receiver_edit)
        form.addRow("Technology", self.technology_edit)

        if not self.is_new:
            status_label = QLabel(f"{t.status}  ·  Preparation {t.preparation_progress:.0f}%  ·  Release {t.release_progress:.0f}%")
            status_label.setStyleSheet("color: #888;")
            form.addRow("Current Status", status_label)

        return w

    def _build_tools_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel("One Transfer can contain multiple Tools; one Tool can contain multiple Part Numbers.")
        info.setStyleSheet("color: #888; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tools_tree = QTreeWidget()
        self.tools_tree.setHeaderLabels(["Tool Number / Part Number"])
        self.tools_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.tools_tree)
        self._reload_tools_tree()

        btn_row = QHBoxLayout()
        add_tool_btn = QPushButton("+ Add Tool")
        add_tool_btn.clicked.connect(self._on_add_tool)
        add_pn_btn = QPushButton("+ Add Part Number to Selected Tool")
        add_pn_btn.clicked.connect(self._on_add_pn)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self._on_remove_tool_or_pn)
        btn_row.addWidget(add_tool_btn)
        btn_row.addWidget(add_pn_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return w

    def _reload_tools_tree(self):
        self.tools_tree.clear()
        for tool in self.transfer.tools:
            tool_item = QTreeWidgetItem([f"🔧 {tool.tool_number}"])
            tool_item.setData(0, Qt.UserRole, ("tool", tool))
            self.tools_tree.addTopLevelItem(tool_item)
            for pn in tool.part_numbers:
                pn_item = QTreeWidgetItem([f"▫ {pn.part_number}"])
                pn_item.setData(0, Qt.UserRole, ("part_number", pn))
                tool_item.addChild(pn_item)
        self.tools_tree.expandAll()

    def _on_add_tool(self):
        text, ok = QInputDialog.getText(self, "Add Tool", "Tool Number:")
        if not ok or not text.strip():
            return
        tool = Tool(tool_number=text.strip())
        self.transfer.tools.append(tool)
        self._reload_tools_tree()

    def _on_add_pn(self):
        item = self.tools_tree.currentItem()
        if not item:
            QMessageBox.information(self, "Select a Tool", "Select a Tool row first, then add a Part Number to it.")
            return
        kind, obj = item.data(0, Qt.UserRole)
        tool = obj if kind == "tool" else item.parent().data(0, Qt.UserRole)[1]
        text, ok = QInputDialog.getText(self, "Add Part Number", "Part Number:")
        if not ok or not text.strip():
            return
        pn = PartNumber(part_number=text.strip())
        tool.part_numbers.append(pn)
        self._reload_tools_tree()

    def _on_remove_tool_or_pn(self):
        item = self.tools_tree.currentItem()
        if not item:
            return
        kind, obj = item.data(0, Qt.UserRole)
        confirm = QMessageBox.question(
            self, "Confirm removal",
            f"Remove this {'Tool (and all its Part Numbers)' if kind == 'tool' else 'Part Number'}? "
            f"All its Preparation data will be deleted too.",
        )
        if confirm != QMessageBox.Yes:
            return
        if kind == "tool":
            self.transfer.tools.remove(obj)
        else:
            parent_tool = item.parent().data(0, Qt.UserRole)[1]
            parent_tool.part_numbers.remove(obj)
        self._reload_tools_tree()

    def _build_attachments_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.attachments_list = QListWidget()
        layout.addWidget(self.attachments_list)
        self._load_attachments()

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Attach File (PDF / Excel / Image)")
        add_btn.clicked.connect(self._on_add_attachment)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._on_remove_attachment)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    def _load_attachments(self):
        self.attachments_list.clear()
        for a in svc.list_attachments(self.session, self.transfer.id):
            item = QListWidgetItem(f"{a.file_name}  ({a.file_type})  - {a.uploaded_at:%Y-%m-%d %H:%M}")
            item.setData(Qt.UserRole, a.id)
            self.attachments_list.addItem(item)

    def _on_add_attachment(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select file to attach", str(Path.home()),
            "Documents (*.pdf *.xlsx *.xls *.csv *.png *.jpg *.jpeg *.bmp)"
        )
        if not file_path:
            return
        src = Path(file_path)
        dest_dir = Path(config.ATTACHMENTS_DIR) / str(self.transfer.id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / src.name
        try:
            shutil.copy2(src, dest_path)
        except OSError as e:
            QMessageBox.warning(self, "Attachment error", f"Could not copy file:\n{e}")
            return
        svc.add_attachment(self.session, self.transfer.id, src.name, str(dest_path), src.suffix.lstrip("."))
        self.session.commit()
        self._load_attachments()

    def _on_remove_attachment(self):
        item = self.attachments_list.currentItem()
        if not item:
            return
        svc.delete_attachment(self.session, item.data(Qt.UserRole))
        self.session.commit()
        self._load_attachments()

    def _build_comments_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.comments_list = QListWidget()
        layout.addWidget(self.comments_list)
        self._load_comments()

        add_row = QHBoxLayout()
        self.new_comment_edit = QLineEdit()
        self.new_comment_edit.setPlaceholderText("Add a comment...")
        add_btn = QPushButton("Add")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._on_add_comment)
        add_row.addWidget(self.new_comment_edit)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)
        return w

    def _load_comments(self):
        self.comments_list.clear()
        for c in svc.list_comments(self.session, self.transfer.id):
            self.comments_list.addItem(QListWidgetItem(f"[{c.created_at:%Y-%m-%d %H:%M}] {c.author}: {c.body}"))

    def _on_add_comment(self):
        text = self.new_comment_edit.text().strip()
        if not text:
            return
        svc.add_comment(self.session, self.transfer.id, text)
        self.session.commit()
        self.new_comment_edit.clear()
        self._load_comments()

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        history_list = QListWidget()
        from sqlalchemy import select
        from models.support import ActivityLog
        stmt = select(ActivityLog).where(ActivityLog.transfer_id == self.transfer.id).order_by(ActivityLog.created_at.desc())
        for entry in self.session.scalars(stmt).all():
            history_list.addItem(QListWidgetItem(f"[{entry.created_at:%Y-%m-%d %H:%M}] {entry.action} - {entry.details}"))
        layout.addWidget(history_list)
        return w

    # ------------------------------------------------------------------ #
    def _on_save(self):
        if not self.trf_number_edit.text().strip():
            QMessageBox.warning(self, "Missing field", "TRF Number is required.")
            self.tabs.setCurrentIndex(0)
            return

        t = self.transfer
        t.trf_number = self.trf_number_edit.text().strip()
        t.planned_transfer_date = _qdate_to_date(self.planned_date_edit.date())
        t.actual_transfer_date = _qdate_to_date(self.actual_date_edit.date())
        t.transfer_type = self.transfer_type_combo.currentText()
        t.activity = self.activity_combo.currentText()
        t.sender_location = self.sender_edit.text().strip()
        t.receiver_location = self.receiver_edit.text().strip()
        t.technology = self.technology_edit.text().strip()

        if self.is_new:
            self.session.add(t)
            svc.ensure_related_records(t)
            self.session.flush()
            from services import progress_service
            progress_service.refresh_transfer(self.session, t)
            svc.log_activity(self.session, t.id, "Created", f"Transfer {t.trf_number} created")
        else:
            svc.save_transfer(self.session, t)

        self.session.commit()
        self.accept()

    def closeEvent(self, event):
        self.session.close()
        super().closeEvent(event)
