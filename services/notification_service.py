"""
services/notification_service.py
------------------------------------
Automatic notifications for overdue activities, scanning every
Preparation sub-module (not just the Transfer's own planned date):
PTT internal/OEM due dates, Raw Material due dates, and Pre-check due
dates, plus the Transfer's own planned transfer date. Each notification
carries enough context (transfer, tool/part number, field) for the UI
to link straight back to the relevant record.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.transfer import Transfer
import config


@dataclass
class Notification:
    severity: str          # "danger" (overdue) | "warning" (due soon)
    title: str
    detail: str
    transfer_id: int
    transfer_trf: str


def _days_left(d: Optional[date]) -> Optional[int]:
    if not d:
        return None
    return (d - date.today()).days


def build_notifications(session: Session) -> list[Notification]:
    settings = config.load_settings()
    horizon = settings.get("notify_days_before_due", 7)
    notes: list[Notification] = []

    transfers = session.scalars(select(Transfer)).all()
    for t in transfers:
        _check_date(notes, t, t.planned_transfer_date, "Planned Transfer Date", horizon,
                    skip_if_completed=True)

        if t.ptt_approval:
            _check_date(notes, t, t.ptt_approval.internal_due_date, "PTT Internal Approval", horizon,
                        skip=t.ptt_approval.internal_status == "Approved")
            for oem in t.ptt_approval.oem_approvals:
                _check_date(notes, t, oem.due_date, f"PTT OEM Approval ({oem.oem_name or 'Unnamed OEM'})",
                            horizon, skip=oem.status == "Approved")

        for tool in t.tools:
            for pn in tool.part_numbers:
                if pn.raw_material:
                    _check_date(notes, t, pn.raw_material.due_date,
                                f"Raw Material - Tool {tool.tool_number} / PN {pn.part_number}",
                                horizon, skip=pn.raw_material.overall_status() in ("Done", "NA"))
                if pn.pre_check:
                    _check_date(notes, t, pn.pre_check.due_date,
                                f"Pre-check - Tool {tool.tool_number} / PN {pn.part_number}",
                                horizon, skip=pn.pre_check.feedback_status in ("Accepted", "Rejected"))

    order = {"danger": 0, "warning": 1}
    notes.sort(key=lambda n: order.get(n.severity, 2))
    return notes


def _check_date(notes: list[Notification], transfer: Transfer, due: Optional[date], label: str,
                 horizon: int, skip: bool = False, skip_if_completed: bool = False) -> None:
    if skip or not due:
        return
    if skip_if_completed and transfer.status == "Completed":
        return
    days = _days_left(due)
    if days is None:
        return
    if days < 0:
        notes.append(Notification(
            severity="danger",
            title=f"Overdue: {label}",
            detail=f"{transfer.trf_number} - due {due.isoformat()} ({abs(days)} day(s) overdue)",
            transfer_id=transfer.id, transfer_trf=transfer.trf_number,
        ))
    elif days <= horizon:
        notes.append(Notification(
            severity="warning",
            title=f"Due soon: {label}",
            detail=f"{transfer.trf_number} - due {due.isoformat()} (in {days} day(s))",
            transfer_id=transfer.id, transfer_trf=transfer.trf_number,
        ))


def counts_by_severity(session: Session) -> dict:
    notes = build_notifications(session)
    out = {"danger": 0, "warning": 0}
    for n in notes:
        out[n.severity] += 1
    return out
