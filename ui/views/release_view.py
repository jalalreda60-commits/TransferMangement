"""
ui/views/release_view.py
---------------------------
Release module (sidebar item 4): shows every Transfer with its
Preparation completeness at a glance, a manual sign-off checklist
mirroring each Preparation sub-module, and the final release decision
(status, actual release date, released-by, comments).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QFrame,
    QPushButton, QMessageBox, QProgressBar,
)
from PySide6.QtCore import Qt

from database.base import new_session
from services import transfer_service as svc
from ui.widgets.entity_picker import EntityPicker
from ui.widgets.dynamic_form import DynamicForm, FieldSpec
from ui.widgets.badge import status_badge
from utils import constants


def _release_checklist_fields():
    return [
        FieldSpec("checklist_ptt_signed_off", "PTT Approval Signed Off", "bool"),
        FieldSpec("checklist_safety_stock_signed_off", "Safety Stock Signed Off", "bool"),
        FieldSpec("checklist_rm_signed_off", "Raw Material Signed Off", "bool"),
        FieldSpec("checklist_precheck_signed_off", "Pre-check Signed Off", "bool"),
        FieldSpec("checklist_e2e_signed_off", "E2E Follow-up Signed Off", "bool"),
        FieldSpec("checklist_applicator_cp_signed_off", "Applicator/Counter Part Signed Off", "bool"),
        FieldSpec("checklist_training_signed_off", "Training Signed Off", "bool"),
    ]


def _release_decision_fields():
    return [
        FieldSpec("status", "Release Status", "combo", constants.RELEASE_STATUSES),
        FieldSpec("release_date", "Actual Release Date", "date"),
        FieldSpec("released_by", "Released By", "text"),
        FieldSpec("sign_off_comments", "Sign-off Comments", "textarea"),
        FieldSpec("open_actions", "Open Actions", "textarea"),
    ]


class ReleaseView(QWidget):
    def __init__(self, dark_mode: bool = False, parent=None):
        super().__init__(parent)
        self.session = new_session()
        self.current_transfer_id = None
        self.dark_mode = dark_mode
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        header = QVBoxLayout()
        title = QLabel("Release")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Final sign-off and release decision per transfer")
        subtitle.setObjectName("pageSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        outer.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, 1)

        picker_card = QFrame()
        picker_card.setObjectName("card")
        picker_layout = QVBoxLayout(picker_card)
        self.picker = EntityPicker(scope="transfer", status_fn=lambda t, tool, pn: t.release.status if t.release else None, dark_mode=self.dark_mode)
        self.picker.selection_changed.connect(self._on_selection_changed)
        picker_layout.addWidget(self.picker)
        splitter.addWidget(picker_card)

        form_card = QFrame()
        form_card.setObjectName("card")
        self.form_layout = QVBoxLayout(form_card)
        self.header_label = QLabel("Select a transfer on the left")
        self.header_label.setObjectName("sectionTitle")
        self.form_layout.addWidget(self.header_label)

        self.prep_progress_bar = QProgressBar()
        self.prep_progress_bar.setRange(0, 100)
        self.form_layout.addWidget(QLabel("Preparation Progress (gates release readiness):"))
        self.form_layout.addWidget(self.prep_progress_bar)

        checklist_title = QLabel("Sign-off Checklist")
        checklist_title.setObjectName("sectionTitle")
        self.form_layout.addWidget(checklist_title)
        self.checklist_form: DynamicForm | None = None
        self.checklist_container = QWidget()
        self.checklist_layout = QVBoxLayout(self.checklist_container)
        self.checklist_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.addWidget(self.checklist_container)

        decision_title = QLabel("Release Decision")
        decision_title.setObjectName("sectionTitle")
        self.form_layout.addWidget(decision_title)
        self.decision_form: DynamicForm | None = None
        self.decision_container = QWidget()
        self.decision_layout = QVBoxLayout(self.decision_container)
        self.decision_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.addWidget(self.decision_container)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setEnabled(False)
        btn_row.addWidget(self.save_btn)
        self.form_layout.addLayout(btn_row)
        self.form_layout.addStretch()

        splitter.addWidget(form_card)
        splitter.setSizes([320, 640])

    def set_dark_mode(self, dark: bool):
        self.dark_mode = dark
        self.picker.set_dark_mode(dark)

    def refresh(self):
        self.session.close()
        self.session = new_session()
        transfers = svc.list_transfers(self.session)
        self.picker.load(transfers, select_transfer_id=self.current_transfer_id)

    def _on_selection_changed(self, transfer_id, tool_id, part_number_id):
        self.current_transfer_id = transfer_id
        self._render()

    def _render(self):
        for layout in (self.checklist_layout, self.decision_layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        self.checklist_form = None
        self.decision_form = None

        if not self.current_transfer_id:
            self.header_label.setText("Select a transfer on the left")
            self.save_btn.setEnabled(False)
            self.prep_progress_bar.setValue(0)
            return

        transfer = next((t for t in svc.list_transfers(self.session) if t.id == self.current_transfer_id), None)
        if not transfer:
            return

        self.header_label.setText(f"{transfer.trf_number}  ·  {transfer.status}")
        self.prep_progress_bar.setValue(int(transfer.preparation_progress))

        self.checklist_form = DynamicForm(_release_checklist_fields())
        self.checklist_form.load(transfer.release)
        self.checklist_layout.addWidget(self.checklist_form)

        self.decision_form = DynamicForm(_release_decision_fields())
        self.decision_form.load(transfer.release)
        self.decision_layout.addWidget(self.decision_form)

        self.save_btn.setEnabled(True)
        self._current_transfer = transfer

    def _on_save(self):
        if not self.current_transfer_id:
            return
        transfer = self._current_transfer
        if transfer.release.status == constants.RELEASE_STATUS_RELEASED and self.decision_form.widgets["status"].currentText() != constants.RELEASE_STATUS_RELEASED:
            pass  # allow un-releasing; no special guard needed

        if self.checklist_form:
            self.checklist_form.save(transfer.release)
        if self.decision_form:
            self.decision_form.save(transfer.release)

        if transfer.release.status == constants.RELEASE_STATUS_READY and transfer.preparation_progress < 100:
            confirm = QMessageBox.question(
                self, "Preparation incomplete",
                f"Preparation is only {transfer.preparation_progress:.0f}% complete. "
                f"Mark as Ready for Release anyway?",
            )
            if confirm != QMessageBox.Yes:
                return

        svc.save_transfer(self.session, transfer)
        self.session.commit()
        QMessageBox.information(self, "Saved", f"Release data updated for {transfer.trf_number}.")
        self.refresh()
        self._render()
