"""
services/transfer_service.py
-------------------------------
CRUD and query operations for the Transfer -> Tool -> PartNumber
hierarchy, plus comments/attachments/activity history and the
duplicate-transfer function. Every write path calls
`ensure_related_records()` so a Transfer/Tool/PartNumber always has its
one-to-one Preparation children (PTT, E2E, Release, Safety Stock,
Training, Raw Material, Pre-check, Applicator/Counter Part) ready to
bind to in the UI - callers never need to null-check those attributes.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload

from models.transfer import Transfer, Tool, PartNumber
from models.preparation import PTTApproval, E2EFollowup, SafetyStock, RawMaterial, PreCheck, Applicator, CounterPart, Training
from models.release import Release
from models.support import Attachment, Comment, ActivityLog
from services import progress_service
from utils import constants


# ------------------------------------------------------------------ #
# Related-record bootstrapping
# ------------------------------------------------------------------ #
def ensure_related_records(transfer: Transfer) -> None:
    if transfer.ptt_approval is None:
        transfer.ptt_approval = PTTApproval()
    if transfer.e2e_followup is None:
        transfer.e2e_followup = E2EFollowup()
    if transfer.release is None:
        transfer.release = Release()

    for tool in transfer.tools:
        if tool.safety_stock is None:
            tool.safety_stock = SafetyStock()
        if tool.training is None:
            tool.training = Training()
        for pn in tool.part_numbers:
            if pn.raw_material is None:
                pn.raw_material = RawMaterial()
            if pn.pre_check is None:
                pn.pre_check = PreCheck()
            if transfer.activity == "Stamping" and pn.applicator is None:
                pn.applicator = Applicator()
            if transfer.activity == "Molding" and pn.counter_part is None:
                pn.counter_part = CounterPart()


def _eager_options():
    return (
        selectinload(Transfer.tools).selectinload(Tool.part_numbers).selectinload(PartNumber.raw_material),
        selectinload(Transfer.tools).selectinload(Tool.part_numbers).selectinload(PartNumber.pre_check),
        selectinload(Transfer.tools).selectinload(Tool.part_numbers).selectinload(PartNumber.applicator),
        selectinload(Transfer.tools).selectinload(Tool.part_numbers).selectinload(PartNumber.counter_part),
        selectinload(Transfer.tools).selectinload(Tool.safety_stock),
        selectinload(Transfer.tools).selectinload(Tool.training),
        selectinload(Transfer.ptt_approval).selectinload(PTTApproval.oem_approvals),
        selectinload(Transfer.e2e_followup),
        selectinload(Transfer.release),
    )


# ------------------------------------------------------------------ #
# CRUD
# ------------------------------------------------------------------ #
def create_transfer(session: Session, **fields) -> Transfer:
    transfer = Transfer(**fields)
    ensure_related_records(transfer)
    session.add(transfer)
    session.flush()
    progress_service.refresh_transfer(session, transfer)
    log_activity(session, transfer.id, "Created", f"Transfer {transfer.trf_number} created")
    return transfer


def get_transfer(session: Session, transfer_id: int) -> Optional[Transfer]:
    stmt = select(Transfer).where(Transfer.id == transfer_id).options(*_eager_options())
    transfer = session.scalars(stmt).first()
    if transfer:
        ensure_related_records(transfer)
    return transfer


def list_transfers(
    session: Session,
    search: str = "",
    transfer_type: str = "",
    activity: str = "",
    status: str = "",
    sender_location: str = "",
    receiver_location: str = "",
    technology: str = "",
    sort_by: str = "planned_transfer_date",
    sort_desc: bool = False,
) -> list[Transfer]:
    stmt = select(Transfer).options(*_eager_options())

    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(
            Transfer.trf_number.ilike(like),
            Transfer.sender_location.ilike(like),
            Transfer.receiver_location.ilike(like),
            Transfer.technology.ilike(like),
        ))
    if transfer_type:
        stmt = stmt.where(Transfer.transfer_type == transfer_type)
    if activity:
        stmt = stmt.where(Transfer.activity == activity)
    if status:
        stmt = stmt.where(Transfer.status == status)
    if sender_location:
        stmt = stmt.where(Transfer.sender_location == sender_location)
    if receiver_location:
        stmt = stmt.where(Transfer.receiver_location == receiver_location)
    if technology:
        stmt = stmt.where(Transfer.technology == technology)

    sort_col = getattr(Transfer, sort_by, Transfer.planned_transfer_date)
    stmt = stmt.order_by(sort_col.desc() if sort_desc else sort_col.asc().nulls_last())

    transfers = list(session.scalars(stmt).unique().all())
    for t in transfers:
        ensure_related_records(t)
    return transfers


def save_transfer(session: Session, transfer: Transfer) -> Transfer:
    """Call after mutating a Transfer (or its nested tree) in place to
    persist changes and refresh cached progress/status."""
    ensure_related_records(transfer)
    progress_service.refresh_transfer(session, transfer)
    session.add(transfer)
    session.flush()
    log_activity(session, transfer.id, "Updated", f"Transfer {transfer.trf_number} updated")
    return transfer


def delete_transfer(session: Session, transfer_id: int) -> None:
    transfer = session.get(Transfer, transfer_id)
    if transfer:
        session.delete(transfer)


def duplicate_transfer(session: Session, transfer_id: int) -> Optional[Transfer]:
    """Deep-copies a Transfer's structure (Tools, PartNumbers, and every
    Preparation sub-record) into a new Transfer, resetting statuses/dates
    so the copy starts fresh rather than inheriting completed progress."""
    original = get_transfer(session, transfer_id)
    if not original:
        return None

    new_transfer = Transfer(
        trf_number=f"{original.trf_number}-COPY",
        planned_transfer_date=original.planned_transfer_date,
        transfer_type=original.transfer_type,
        activity=original.activity,
        sender_location=original.sender_location,
        receiver_location=original.receiver_location,
        technology=original.technology,
    )
    for tool in original.tools:
        new_tool = Tool(tool_number=tool.tool_number)
        for pn in tool.part_numbers:
            new_pn = PartNumber(part_number=pn.part_number)
            new_tool.part_numbers.append(new_pn)
        new_transfer.tools.append(new_tool)

    ensure_related_records(new_transfer)
    session.add(new_transfer)
    session.flush()
    progress_service.refresh_transfer(session, new_transfer)
    log_activity(session, new_transfer.id, "Duplicated", f"Duplicated from {original.trf_number}")
    return new_transfer


def distinct_values(session: Session, column_name: str) -> list[str]:
    col = getattr(Transfer, column_name)
    stmt = select(col).where(col.isnot(None), col != "").distinct().order_by(col)
    return [v for v in session.scalars(stmt).all() if v]


# ------------------------------------------------------------------ #
# Comments / Attachments / Activity log
# ------------------------------------------------------------------ #
def add_comment(session: Session, transfer_id: int, body: str, author: str = "User") -> Comment:
    comment = Comment(transfer_id=transfer_id, body=body, author=author)
    session.add(comment)
    log_activity(session, transfer_id, "Comment added", body[:80])
    session.flush()
    return comment


def list_comments(session: Session, transfer_id: int) -> list[Comment]:
    stmt = select(Comment).where(Comment.transfer_id == transfer_id).order_by(Comment.created_at.desc())
    return list(session.scalars(stmt).all())


def add_attachment(session: Session, transfer_id: int, file_name: str, stored_path: str, file_type: str) -> Attachment:
    att = Attachment(transfer_id=transfer_id, file_name=file_name, stored_path=stored_path, file_type=file_type)
    session.add(att)
    log_activity(session, transfer_id, "Attachment added", file_name)
    session.flush()
    return att


def list_attachments(session: Session, transfer_id: int) -> list[Attachment]:
    stmt = select(Attachment).where(Attachment.transfer_id == transfer_id).order_by(Attachment.uploaded_at.desc())
    return list(session.scalars(stmt).all())


def delete_attachment(session: Session, attachment_id: int) -> None:
    att = session.get(Attachment, attachment_id)
    if att:
        session.delete(att)


def log_activity(session: Session, transfer_id: Optional[int], action: str, details: str = "") -> None:
    session.add(ActivityLog(transfer_id=transfer_id, action=action, details=details))


def recent_activity(session: Session, limit: int = 15) -> list[ActivityLog]:
    stmt = select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
    return list(session.scalars(stmt).all())
