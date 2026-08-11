"""
ui/widgets/dynamic_form.py
-----------------------------
A small declarative form builder: given a list of FieldSpec entries, it
builds a QFormLayout with the right widget per field type and exposes
`load(obj)` / `save(obj)` to bind directly to a model instance's
attributes. This is what keeps the seven Preparation sub-modules (and
Release's checklist) from needing hand-written, repetitive form code.

Supported field types: "text", "textarea", "date", "bool", "combo",
"int", "float".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_cls
from typing import Any, Callable, Optional

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox, QDateEdit, QCheckBox,
    QTextEdit, QSpinBox, QDoubleSpinBox, QLabel,
)
from PySide6.QtCore import Qt, QDate


@dataclass
class FieldSpec:
    attr: str
    label: str
    kind: str                      # text | textarea | date | bool | combo | int | float
    options: Optional[list[str]] = None
    suffix: str = ""
    min_value: float = 0.0
    max_value: float = 1_000_000.0
    on_change: Optional[Callable[[QWidget], None]] = None  # optional callback(widget) wired to change signal


def _date_to_qdate(d: Optional[date_cls]) -> QDate:
    if not d:
        return QDate.currentDate()
    return QDate(d.year, d.month, d.day)


def _qdate_to_date(qd: QDate) -> Optional[date_cls]:
    if not qd or not qd.isValid():
        return None
    return date_cls(qd.year(), qd.month(), qd.day())


class DynamicForm(QWidget):
    def __init__(self, specs: list[FieldSpec], parent=None):
        super().__init__(parent)
        self.specs = specs
        self.widgets: dict[str, QWidget] = {}

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)

        for spec in specs:
            widget = self._build_widget(spec)
            self.widgets[spec.attr] = widget
            layout.addRow(spec.label, widget)

    def _build_widget(self, spec: FieldSpec) -> QWidget:
        if spec.kind == "text":
            w = QLineEdit()
        elif spec.kind == "textarea":
            w = QTextEdit()
            w.setMaximumHeight(80)
        elif spec.kind == "date":
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
        elif spec.kind == "bool":
            w = QCheckBox()
        elif spec.kind == "combo":
            w = QComboBox()
            w.addItems(spec.options or [])
        elif spec.kind == "int":
            w = QSpinBox()
            w.setRange(int(spec.min_value), int(spec.max_value))
            if spec.suffix:
                w.setSuffix(f" {spec.suffix}")
        elif spec.kind == "float":
            w = QDoubleSpinBox()
            w.setRange(spec.min_value, spec.max_value)
            w.setDecimals(2)
            if spec.suffix:
                w.setSuffix(f" {spec.suffix}")
        else:
            w = QLineEdit()

        if spec.on_change:
            signal = {
                "text": w.textChanged if spec.kind == "text" else None,
                "combo": w.currentTextChanged if spec.kind == "combo" else None,
                "bool": w.stateChanged if spec.kind == "bool" else None,
                "int": w.valueChanged if spec.kind == "int" else None,
                "float": w.valueChanged if spec.kind == "float" else None,
            }.get(spec.kind)
            if signal is not None:
                signal.connect(lambda *_, s=spec, ww=w: spec.on_change(ww))
        return w

    # ------------------------------------------------------------------ #
    def load(self, obj: Any):
        for spec in self.specs:
            value = getattr(obj, spec.attr, None)
            w = self.widgets[spec.attr]
            if spec.kind in ("text",):
                w.setText(value or "")
            elif spec.kind == "textarea":
                w.setPlainText(value or "")
            elif spec.kind == "date":
                w.setDate(_date_to_qdate(value))
            elif spec.kind == "bool":
                w.setChecked(bool(value))
            elif spec.kind == "combo":
                idx = w.findText(value or "")
                w.setCurrentIndex(idx if idx >= 0 else 0)
            elif spec.kind == "int":
                w.setValue(int(value or 0))
            elif spec.kind == "float":
                w.setValue(float(value or 0.0))

    def save(self, obj: Any):
        for spec in self.specs:
            w = self.widgets[spec.attr]
            if spec.kind == "text":
                setattr(obj, spec.attr, w.text().strip())
            elif spec.kind == "textarea":
                setattr(obj, spec.attr, w.toPlainText().strip())
            elif spec.kind == "date":
                setattr(obj, spec.attr, _qdate_to_date(w.date()))
            elif spec.kind == "bool":
                setattr(obj, spec.attr, w.isChecked())
            elif spec.kind == "combo":
                setattr(obj, spec.attr, w.currentText())
            elif spec.kind == "int":
                setattr(obj, spec.attr, w.value())
            elif spec.kind == "float":
                setattr(obj, spec.attr, w.value())

    def set_enabled_all(self, enabled: bool):
        for w in self.widgets.values():
            w.setEnabled(enabled)
