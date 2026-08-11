"""
ui/views/preparation_view.py
--------------------------------
One reusable view class that implements all seven Preparation
sub-modules (PTT Approval, Safety Stock, Raw Material, Pre-check, E2E
Follow-up, Applicator/Counter Part, Training). Each sub-module is
described by a small config entry (`_MODULE_CONFIG`) giving its scope
(Transfer / Tool / PartNumber), the entity accessor, and the
DynamicForm field specs - the picker + form + save/history wiring is
shared code.

PTT Approval additionally manages its one-to-many OEM Approvals via a
small embedded table, and Applicator/Counter Part switches between the
two entities depending on the parent Transfer's Activity, as required.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMessageBox, QHeaderView,
)
from PySide6.QtCore import Qt

from database.base import new_session
from services import transfer_service as svc
from ui.widgets.entity_picker import EntityPicker
from ui.widgets.dynamic_form import DynamicForm, FieldSpec
from ui.widgets.badge import status_badge
from ui.views.oem_dialog import OEMApprovalDialog
from utils import constants


# ---------------------------------------------------------------------
# Per-submodule field specs
# ---------------------------------------------------------------------
def _ptt_fields():
    return [
        FieldSpec("internal_status", "Internal Status", "combo", constants.STATUS_NOT_ONGOING_APPROVED),
        FieldSpec("internal_responsible", "Responsible", "text"),
        FieldSpec("internal_due_date", "Due Date", "date"),
        FieldSpec("internal_approval_date", "Approval Date", "date"),
        FieldSpec("internal_comments", "Comments", "textarea"),
    ]


def _safety_stock_fields():
    return [
        FieldSpec("required", "Safety Stock Required", "bool"),
        FieldSpec("start_week", "Start Calendar Week", "text"),
        FieldSpec("number_of_weeks", "Number of Weeks", "int", min_value=0, max_value=104),
        FieldSpec("required_quantity", "Required Quantity", "float", min_value=0, max_value=1_000_000),
        FieldSpec("built_quantity", "Current Built Quantity", "float", min_value=0, max_value=1_000_000),
        FieldSpec("finish_week", "Finish Calendar Week", "text"),
    ]


def _rm_fields():
    return [
        FieldSpec("subgroup_status", "Subgroup", "combo", constants.STATUS_NA_ONGOING_DONE),
        FieldSpec("setup_status", "Setup", "combo", constants.STATUS_NA_ONGOING_DONE),
        FieldSpec("order_status", "RM Order", "combo", constants.STATUS_NA_ONGOING_DONE),
        FieldSpec("availability_status", "RM Availability", "combo", constants.STATUS_NA_ONGOING_DONE),
        FieldSpec("due_date", "Due Date", "date"),
        FieldSpec("comment", "Comment", "textarea"),
    ]


def _pre_check_fields():
    return [
        FieldSpec("pe_responsible", "PE Responsible", "text"),
        FieldSpec("samples_before_status", "Samples Before", "combo", constants.STATUS_NA_ONGOING_RECEIVED),
        FieldSpec("pe_requirement_status", "PE Requirement", "combo", constants.STATUS_NA_ONGOING_RECEIVED),
        FieldSpec("measurement_report_status", "Measurement Report", "combo", constants.STATUS_NA_ONGOING_RECEIVED),
        FieldSpec("feedback_status", "Pre-check Feedback", "combo", constants.STATUS_NA_ONGOING_ACCEPTED_REJECTED),
        FieldSpec("due_date", "Due Date", "date"),
        FieldSpec("actions", "Actions", "textarea"),
        FieldSpec("comments", "Comments", "textarea"),
    ]


def _e2e_fields():
    return [
        FieldSpec("kickoff_week", "Kick-off Call - Planned Week", "text"),
        FieldSpec("kickoff_status", "Kick-off Call - Status", "combo", constants.STATUS_CALL_GENERIC),
        FieldSpec("pcn_ppap_week", "PCN & PPAP Call - Planned Week", "text"),
        FieldSpec("pcn_ppap_status", "PCN & PPAP Call - Status", "combo", constants.STATUS_CALL_GENERIC),
        FieldSpec("pcn_decision", "PCN Decision (Yes)", "bool"),
        FieldSpec("pcn_status", "PCN Status", "combo", constants.STATUS_NOT_SENT_SENT_ONGOING_APPROVED),
        FieldSpec("action_list", "Action List", "textarea"),
        FieldSpec("sop_week", "SOP Readiness Call - Planned Week", "text"),
        FieldSpec("sop_status", "SOP Readiness Call - Status", "combo", constants.STATUS_CALL_GENERIC),
        FieldSpec("link_file", "Link to E2E File", "text"),
        FieldSpec("comments", "Comments", "textarea"),
        FieldSpec("open_actions", "Open Actions", "textarea"),
    ]


def _applicator_fields():
    return [
        FieldSpec("pe", "PE", "text"),
        FieldSpec("urgency", "Urgency", "combo", constants.URGENCY_LEVELS),
        FieldSpec("applicator_required", "Applicator Required", "bool"),
        FieldSpec("applicator", "Applicator", "text"),
        FieldSpec("crimping_specification", "Crimping Specification", "text"),
        FieldSpec("terminal", "Terminal", "text"),
        FieldSpec("wire_section", "Wire Section", "text"),
        FieldSpec("number_of_parts", "Number of Parts", "int", min_value=0, max_value=1_000_000),
        FieldSpec("required_approvals", "Required Approvals", "text"),
        FieldSpec("applicator_available_location", "Applicator Available Location", "text"),
        FieldSpec("crimping_request", "Crimping Request", "combo", constants.STATUS_NOT_ONGOING_DONE),
        FieldSpec("comments", "Comments", "textarea"),
    ]


def _counter_part_fields():
    return [
        FieldSpec("pe", "PE", "text"),
        FieldSpec("counter_part", "Counter Part", "text"),
        FieldSpec("terminal", "Terminal", "text"),
        FieldSpec("crimping", "Crimping", "text"),
        FieldSpec("terminal_request", "Terminal Request", "combo", constants.STATUS_NOT_ONGOING_DONE),
        FieldSpec("status_field", "Status", "combo", constants.STATUS_NOT_ONGOING_DONE),
        FieldSpec("comments", "Comments", "textarea"),
    ]


def _training_fields():
    return [
        FieldSpec("required", "Training Required", "bool"),
        FieldSpec("planned_week", "Planned Calendar Week", "text"),
        FieldSpec("duration", "Duration", "text"),
        FieldSpec("invitation_sent", "Invitation Sent", "bool"),
        FieldSpec("status", "Status", "combo", constants.STATUS_NOT_ONGOING_DONE),
        FieldSpec("comments", "Comments", "textarea"),
    ]


_MODULE_CONFIG = {
    "prep_ptt": {
        "title": "PTT Approval", "scope": "transfer", "fields": _ptt_fields,
        "get_entity": lambda t, tool, pn: t.ptt_approval,
        "status_fn": lambda t, tool, pn: (t.ptt_approval.overall_status() if t.ptt_approval else None) if tool is None and pn is None else None,
    },
    "prep_safety_stock": {
        "title": "Safety Stock Build-up", "scope": "tool", "fields": _safety_stock_fields,
        "get_entity": lambda t, tool, pn: tool.safety_stock if tool else None,
        "status_fn": lambda t, tool, pn: (tool.safety_stock.status() if tool and tool.safety_stock else None) if tool and pn is None else None,
    },
    "prep_raw_material": {
        "title": "Raw Material Follow-up", "scope": "part_number", "fields": _rm_fields,
        "get_entity": lambda t, tool, pn: pn.raw_material if pn else None,
        "status_fn": lambda t, tool, pn: (pn.raw_material.overall_status() if pn and pn.raw_material else None) if pn else None,
    },
    "prep_pre_check": {
        "title": "Pre-check", "scope": "part_number", "fields": _pre_check_fields,
        "get_entity": lambda t, tool, pn: pn.pre_check if pn else None,
        "status_fn": lambda t, tool, pn: (pn.pre_check.feedback_status if pn and pn.pre_check else None) if pn else None,
    },
    "prep_e2e": {
        "title": "E2E Follow-up", "scope": "transfer", "fields": _e2e_fields,
        "get_entity": lambda t, tool, pn: t.e2e_followup,
        "status_fn": lambda t, tool, pn: None,
    },
    "prep_applicator_cp": {
        "title": "Applicator / Counter Part Check", "scope": "part_number", "fields": None,
        "get_entity": None, "status_fn": lambda t, tool, pn: None,
    },
    "prep_training": {
        "title": "Training", "scope": "tool", "fields": _training_fields,
        "get_entity": lambda t, tool, pn: tool.training if tool else None,
        "status_fn": lambda t, tool, pn: (tool.training.status if tool and tool.training else None) if tool and pn is None else None,
    },
}


class PreparationView(QWidget):
    def __init__(self, module_key: str, dark_mode: bool = False, parent=None):
        super().__init__(parent)
        self.module_key = module_key
        self.config = _MODULE_CONFIG[module_key]
        self.session = new_session()
        self.current_ids = (None, None, None)
        self.dark_mode = dark_mode

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ #
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        header = QVBoxLayout()
        title = QLabel(self.config["title"])
        title.setObjectName("pageTitle")
        subtitle = QLabel("Preparation")
        subtitle.setObjectName("pageSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        outer.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, 1)

        picker_card = QFrame()
        picker_card.setObjectName("card")
        picker_layout = QVBoxLayout(picker_card)
        self.picker = EntityPicker(scope=self.config["scope"], status_fn=self._picker_status_fn, dark_mode=self.dark_mode)
        self.picker.selection_changed.connect(self._on_selection_changed)
        picker_layout.addWidget(self.picker)
        splitter.addWidget(picker_card)

        form_card = QFrame()
        form_card.setObjectName("card")
        self.form_layout = QVBoxLayout(form_card)
        self.form_header = QLabel("Select an item on the left")
        self.form_header.setObjectName("sectionTitle")
        self.form_layout.addWidget(self.form_header)

        self.form_container = QWidget()
        self.form_container_layout = QVBoxLayout(self.form_container)
        self.form_container_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.addWidget(self.form_container, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setEnabled(False)
        btn_row.addWidget(self.save_btn)
        self.form_layout.addLayout(btn_row)

        splitter.addWidget(form_card)
        splitter.setSizes([320, 640])

        self.current_form: DynamicForm | None = None
        self.oem_table: QTableWidget | None = None
        self._current_entity = None

    def _picker_status_fn(self, t, tool, pn):
        return self.config["status_fn"](t, tool, pn)

    def set_dark_mode(self, dark: bool):
        self.dark_mode = dark
        self.picker.set_dark_mode(dark)

    # ------------------------------------------------------------------ #
    def refresh(self):
        self.session.close()
        self.session = new_session()
        transfers = svc.list_transfers(self.session)
        keep_transfer_id = self.current_ids[0]
        self.picker.load(transfers, select_transfer_id=keep_transfer_id)

    def _on_selection_changed(self, transfer_id, tool_id, part_number_id):
        self.current_ids = (transfer_id, tool_id, part_number_id)
        self._render_form()

    def _clear_form_container(self):
        while self.form_container_layout.count():
            item = self.form_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.current_form = None
        self.oem_table = None

    def _resolve_context(self):
        transfer_id, tool_id, part_number_id = self.current_ids
        transfer = tool = pn = None
        transfers = svc.list_transfers(self.session)

        if transfer_id:
            transfer = next((t for t in transfers if t.id == transfer_id), None)

        if tool_id and not transfer:
            for t in transfers:
                match = next((tt for tt in t.tools if tt.id == tool_id), None)
                if match:
                    transfer, tool = t, match
                    break
        elif tool_id and transfer:
            tool = next((tt for tt in transfer.tools if tt.id == tool_id), None)

        if part_number_id:
            search_space = [transfer] if transfer else transfers
            for t in search_space:
                for tl in t.tools:
                    match = next((p for p in tl.part_numbers if p.id == part_number_id), None)
                    if match:
                        transfer, tool, pn = t, tl, match
                        break
                if pn:
                    break

        return transfer, tool, pn

    def _render_form(self):
        self._clear_form_container()
        transfer, tool, pn = self._resolve_context()

        if not transfer:
            self.form_header.setText("Select an item on the left")
            self.save_btn.setEnabled(False)
            return

        if self.module_key == "prep_applicator_cp":
            self._render_applicator_cp(transfer, tool, pn)
            return
        if self.module_key == "prep_ptt":
            self._render_ptt(transfer)
            return

        entity = self.config["get_entity"](transfer, tool, pn)
        if entity is None:
            self.form_header.setText("Nothing to edit for this selection")
            self.save_btn.setEnabled(False)
            return

        label = tool.tool_number if tool else (pn.part_number if pn else transfer.trf_number)
        self.form_header.setText(f"{self.config['title']} — {transfer.trf_number} / {label}")

        form = DynamicForm(self.config["fields"]())
        form.load(entity)
        self.form_container_layout.addWidget(form)
        self.current_form = form
        self._current_entity = entity
        self.save_btn.setEnabled(True)

    def _render_ptt(self, transfer):
        entity = transfer.ptt_approval
        self.form_header.setText(f"PTT Approval — {transfer.trf_number}  (Overall: {entity.overall_status()})")

        internal_label = QLabel("Step 1 - Internal Approval")
        internal_label.setObjectName("sectionTitle")
        self.form_container_layout.addWidget(internal_label)

        form = DynamicForm(_ptt_fields())
        form.load(entity)
        self.form_container_layout.addWidget(form)
        self.current_form = form
        self._current_entity = entity

        oem_label = QLabel("Step 2 - OEM Approval")
        oem_label.setObjectName("sectionTitle")
        self.form_container_layout.addWidget(oem_label)

        self.oem_table = QTableWidget(0, 5)
        self.oem_table.setHorizontalHeaderLabels(["OEM Name", "Status", "Due Date", "Approval Date", "Comments"])
        self.oem_table.verticalHeader().setVisible(False)
        self.oem_table.horizontalHeader().setStretchLastSection(True)
        for col in range(4):
            self.oem_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.oem_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.oem_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.oem_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.oem_table.doubleClicked.connect(lambda _idx: self._on_edit_oem(entity))
        self._reload_oem_table(entity)
        self.form_container_layout.addWidget(self.oem_table)

        oem_hint = QLabel("Double-click a row (or select it and click Edit) to set its status, due date, approval date and comments.")
        oem_hint.setStyleSheet("color: #888; font-size: 11px;")
        oem_hint.setWordWrap(True)
        self.form_container_layout.addWidget(oem_hint)

        oem_btn_row = QHBoxLayout()
        add_oem_btn = QPushButton("+ Add OEM")
        add_oem_btn.clicked.connect(lambda: self._on_add_oem(entity))
        edit_oem_btn = QPushButton("Edit Selected OEM")
        edit_oem_btn.clicked.connect(lambda: self._on_edit_oem(entity))
        remove_oem_btn = QPushButton("Remove Selected OEM")
        remove_oem_btn.clicked.connect(lambda: self._on_remove_oem(entity))
        oem_btn_row.addWidget(add_oem_btn)
        oem_btn_row.addWidget(edit_oem_btn)
        oem_btn_row.addWidget(remove_oem_btn)
        oem_btn_row.addStretch()
        self.form_container_layout.addLayout(oem_btn_row)

        self.save_btn.setEnabled(True)

    def _reload_oem_table(self, ptt_entity):
        self.oem_table.setRowCount(len(ptt_entity.oem_approvals))
        for row, oem in enumerate(ptt_entity.oem_approvals):
            self.oem_table.setItem(row, 0, QTableWidgetItem(oem.oem_name))
            self.oem_table.setCellWidget(row, 1, status_badge(oem.status))
            self.oem_table.setItem(row, 2, QTableWidgetItem(oem.due_date.isoformat() if oem.due_date else ""))
            self.oem_table.setItem(row, 3, QTableWidgetItem(oem.approval_date.isoformat() if oem.approval_date else ""))
            self.oem_table.setItem(row, 4, QTableWidgetItem(oem.comments))
            # Row position (not oem.id, which is None until the record is
            # first saved) is what reliably identifies a row here, since
            # several newly-added OEMs can exist in the same edit session
            # before the user clicks Save.
            self.oem_table.item(row, 0).setData(Qt.UserRole, row)

    def _on_add_oem(self, ptt_entity):
        from models.preparation import OEMApproval
        new_oem = OEMApproval(oem_name="", status="Not Started")
        dialog = OEMApprovalDialog(new_oem, parent=self)
        if dialog.exec():
            ptt_entity.oem_approvals.append(new_oem)
            self._reload_oem_table(ptt_entity)

    def _on_edit_oem(self, ptt_entity):
        row = self.oem_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No selection", "Select an OEM row first.")
            return
        oem = ptt_entity.oem_approvals[row]
        dialog = OEMApprovalDialog(oem, parent=self)
        if dialog.exec():
            self._reload_oem_table(ptt_entity)

    def _on_remove_oem(self, ptt_entity):
        row = self.oem_table.currentRow()
        if row < 0:
            return
        del ptt_entity.oem_approvals[row]
        self._reload_oem_table(ptt_entity)

    def _render_applicator_cp(self, transfer, tool, pn):
        if not pn:
            self.form_header.setText("Select a Part Number on the left")
            self.save_btn.setEnabled(False)
            return
        if transfer.activity == "Stamping":
            self.form_header.setText(f"Applicator Check — {transfer.trf_number} / {pn.part_number}")
            entity = pn.applicator
            specs = _applicator_fields()
        else:
            self.form_header.setText(f"Counter Part Check — {transfer.trf_number} / {pn.part_number}")
            entity = pn.counter_part
            specs = _counter_part_fields()

        form = DynamicForm(specs)
        form.load(entity)
        self.form_container_layout.addWidget(form)
        self.current_form = form
        self._current_entity = entity
        self.save_btn.setEnabled(True)

    # ------------------------------------------------------------------ #
    def _on_save(self):
        transfer, tool, pn = self._resolve_context()
        if not transfer:
            return
        if self.current_form and self._current_entity is not None:
            self.current_form.save(self._current_entity)
        svc.save_transfer(self.session, transfer)
        self.session.commit()
        QMessageBox.information(self, "Saved", f"{self.config['title']} updated for {transfer.trf_number}.")
        keep_ids = self.current_ids
        self.refresh()
        self.current_ids = keep_ids
        self._render_form()
