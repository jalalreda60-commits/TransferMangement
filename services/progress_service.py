"""
services/progress_service.py
-------------------------------
Automatic progress calculation, rolled up through the hierarchy exactly
as required by the spec:

    Progress of every activity
        -> Progress of every Tool
            -> Progress of every Transfer (Preparation + Release)
                -> Global Dashboard Progress

Each Preparation/Release entity already knows how to compute its own
`progress_pct()` (see models/preparation.py, models/release.py); this
module is purely about the roll-up arithmetic and about keeping the
cached `Transfer.preparation_progress` / `Transfer.release_progress` /
`Transfer.status` columns in sync so the Dashboard and Transfers list
can sort/filter on them cheaply.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from models.transfer import Transfer, Tool, PartNumber
from utils import constants


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def part_number_progress(pn: PartNumber, activity: str) -> float:
    parts: list[float] = []
    if pn.raw_material:
        parts.append(pn.raw_material.progress_pct())
    if pn.pre_check:
        parts.append(pn.pre_check.progress_pct())
    if activity == "Stamping" and pn.applicator:
        parts.append(pn.applicator.progress_pct())
    elif activity == "Molding" and pn.counter_part:
        parts.append(pn.counter_part.progress_pct())
    return _average(parts)


def tool_progress(tool: Tool, activity: str) -> float:
    parts: list[float] = []
    pn_progresses = [part_number_progress(pn, activity) for pn in tool.part_numbers]
    if pn_progresses:
        parts.append(_average(pn_progresses))
    if tool.safety_stock:
        parts.append(tool.safety_stock.progress_pct())
    if tool.training:
        parts.append(tool.training.progress_pct())
    return _average(parts)


def transfer_preparation_progress(transfer: Transfer) -> float:
    parts: list[float] = []
    if transfer.ptt_approval:
        parts.append(transfer.ptt_approval.progress())
    if transfer.e2e_followup:
        parts.append(transfer.e2e_followup.progress_pct())
    tool_progresses = [tool_progress(tool, transfer.activity) for tool in transfer.tools]
    if tool_progresses:
        parts.append(_average(tool_progresses))
    return round(_average(parts), 1)


def transfer_release_progress(transfer: Transfer) -> float:
    return round(transfer.release.progress_pct(), 1) if transfer.release else 0.0


def compute_transfer_status(transfer: Transfer, preparation_progress: float, release_progress: float) -> str:
    if transfer.release and transfer.release.status == constants.RELEASE_STATUS_RELEASED:
        return constants.TRANSFER_STATUS_COMPLETED
    if transfer.is_overdue():
        return constants.TRANSFER_STATUS_DELAYED
    if preparation_progress > 0 or release_progress > 0:
        return constants.TRANSFER_STATUS_ONGOING
    return constants.TRANSFER_STATUS_NOT_STARTED


def refresh_transfer(session: Session, transfer: Transfer) -> Transfer:
    """Recomputes and persists the cached progress/status fields on a
    single Transfer. Call this after any change to the transfer or its
    nested Tools/PartNumbers/Preparation/Release data."""
    prep = transfer_preparation_progress(transfer)
    rel = transfer_release_progress(transfer)
    transfer.preparation_progress = prep
    transfer.release_progress = rel
    transfer.status = compute_transfer_status(transfer, prep, rel)
    session.add(transfer)
    return transfer


def refresh_all(session: Session) -> None:
    """Recomputes cached progress for every transfer - used after a bulk
    change (e.g. Excel import) or as a periodic consistency sweep."""
    from sqlalchemy import select
    for transfer in session.scalars(select(Transfer)):
        refresh_transfer(session, transfer)


def global_dashboard_progress(transfers: list[Transfer]) -> dict:
    """Aggregate KPIs used by the Dashboard's top-level progress cards."""
    if not transfers:
        return {"preparation_progress": 0.0, "release_progress": 0.0, "global_progress": 0.0}
    prep = _average([t.preparation_progress for t in transfers])
    rel = _average([t.release_progress for t in transfers])
    return {
        "preparation_progress": round(prep, 1),
        "release_progress": round(rel, 1),
        "global_progress": round(_average([prep, rel]), 1),
    }
