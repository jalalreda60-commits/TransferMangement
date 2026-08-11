"""
services/dashboard_service.py
--------------------------------
Aggregate queries backing the Dashboard: KPI cards, chart data
(progress by transfer, progress by phase, weekly progress, transfers by
technology, transfer type distribution), and the Recent
Activities/Upcoming Due Dates/Delayed Tasks tables.

Note on "Weekly Progress": the spec doesn't define a progress-history
table, so this is computed as the average Preparation progress of
transfers grouped by the ISO calendar week of their planned transfer
date (the most natural time axis already present in the data model),
covering the 8 weeks centred on today.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.transfer import Transfer
from services import progress_service, notification_service
from utils import constants


def kpis(session: Session) -> dict:
    transfers = session.scalars(select(Transfer)).unique().all()
    total = len(transfers)
    delayed = sum(1 for t in transfers if t.status == constants.TRANSFER_STATUS_DELAYED)
    completed = sum(1 for t in transfers if t.status == constants.TRANSFER_STATUS_COMPLETED)
    open_actions = 0
    for t in transfers:
        if t.e2e_followup and t.e2e_followup.open_actions.strip():
            open_actions += 1
        if t.release and t.release.open_actions.strip():
            open_actions += 1

    prog = progress_service.global_dashboard_progress(list(transfers))
    return {
        "total_transfers": total,
        "preparation_progress": prog["preparation_progress"],
        "release_progress": prog["release_progress"],
        "global_progress": prog["global_progress"],
        "delayed_activities": delayed,
        "open_actions": open_actions,
        "completed_transfers": completed,
    }


def transfers_by_technology(session: Session) -> dict:
    return _group_count(session, lambda t: t.technology or "Unspecified")


def transfers_by_sender_location(session: Session) -> dict:
    return _group_count(session, lambda t: t.sender_location or "Unspecified")


def transfers_by_receiver_location(session: Session) -> dict:
    return _group_count(session, lambda t: t.receiver_location or "Unspecified")


def transfer_type_distribution(session: Session) -> dict:
    return _group_count(session, lambda t: t.transfer_type or "Unspecified")


def status_distribution(session: Session) -> dict:
    transfers = session.scalars(select(Transfer)).unique().all()
    dist = {s: 0 for s in constants.TRANSFER_STATUSES}
    for t in transfers:
        dist[t.status] = dist.get(t.status, 0) + 1
    return dist


def progress_by_transfer(session: Session, limit: int = 12) -> tuple[list[str], list[float], list[str]]:
    """Returns (labels, prep_progress_values, colors) for the most
    urgent/upcoming transfers, used for a horizontal bar chart."""
    transfers = session.scalars(
        select(Transfer).order_by(Transfer.planned_transfer_date.asc().nulls_last())
    ).unique().all()
    transfers = transfers[:limit]
    labels = [t.trf_number for t in transfers]
    values = [t.preparation_progress for t in transfers]
    colors = [constants.color_for_status(t.status) for t in transfers]
    return labels, values, colors


def progress_by_phase(session: Session) -> dict:
    """Average progress across all transfers, broken down by
    Preparation phase (PTT / Safety Stock / RM / Pre-check / E2E /
    Applicator-CounterPart / Training) and Release."""
    transfers = session.scalars(select(Transfer)).unique().all()
    if not transfers:
        return {}

    ptt_vals, e2e_vals, ss_vals, rm_vals, pc_vals, ap_vals, tr_vals, rel_vals = [], [], [], [], [], [], [], []
    for t in transfers:
        if t.ptt_approval:
            ptt_vals.append(t.ptt_approval.progress())
        if t.e2e_followup:
            e2e_vals.append(t.e2e_followup.progress_pct())
        if t.release:
            rel_vals.append(t.release.progress_pct())
        for tool in t.tools:
            if tool.safety_stock:
                ss_vals.append(tool.safety_stock.progress_pct())
            if tool.training:
                tr_vals.append(tool.training.progress_pct())
            for pn in tool.part_numbers:
                if pn.raw_material:
                    rm_vals.append(pn.raw_material.progress_pct())
                if pn.pre_check:
                    pc_vals.append(pn.pre_check.progress_pct())
                if t.activity == "Stamping" and pn.applicator:
                    ap_vals.append(pn.applicator.progress_pct())
                elif t.activity == "Molding" and pn.counter_part:
                    ap_vals.append(pn.counter_part.progress_pct())

    def avg(vals):
        return round(sum(vals) / len(vals), 1) if vals else 0.0

    return OrderedDict([
        ("PTT Approval", avg(ptt_vals)),
        ("Safety Stock", avg(ss_vals)),
        ("Raw Material", avg(rm_vals)),
        ("Pre-check", avg(pc_vals)),
        ("E2E Follow-up", avg(e2e_vals)),
        ("Applicator/CP", avg(ap_vals)),
        ("Training", avg(tr_vals)),
        ("Release", avg(rel_vals)),
    ])


def weekly_progress_trend(session: Session, weeks_back: int = 4, weeks_forward: int = 4) -> dict:
    transfers = session.scalars(select(Transfer)).unique().all()
    today = date.today()
    this_week_start = today - timedelta(days=today.weekday())

    buckets: "OrderedDict[str, list[float]]" = OrderedDict()
    for i in range(-weeks_back, weeks_forward + 1):
        week_start = this_week_start + timedelta(weeks=i)
        key = f"WK{week_start.isocalendar()[1]:02d}"
        buckets[key] = []

    for t in transfers:
        if not t.planned_transfer_date:
            continue
        d = t.planned_transfer_date
        week_start = d - timedelta(days=d.weekday())
        key = f"WK{week_start.isocalendar()[1]:02d}"
        if key in buckets:
            buckets[key].append(t.preparation_progress)

    return {k: (round(sum(v) / len(v), 1) if v else 0.0) for k, v in buckets.items()}


def upcoming_transfer_dates(session: Session, days: int = 30, limit: int = 10) -> list[Transfer]:
    transfers = session.scalars(select(Transfer)).unique().all()
    upcoming = [t for t in transfers if t.days_until_transfer() is not None
                and 0 <= t.days_until_transfer() <= days
                and t.status != constants.TRANSFER_STATUS_COMPLETED]
    upcoming.sort(key=lambda t: t.days_until_transfer())
    return upcoming[:limit]


def next_transfer_this_month(session: Session) -> Optional[Transfer]:
    """The nearest upcoming transfer (today or later) whose planned
    transfer date falls within the current calendar month - used for
    the Dashboard's "next transfer this month" notification banner."""
    today = date.today()
    transfers = session.scalars(select(Transfer)).unique().all()
    candidates = [
        t for t in transfers
        if t.planned_transfer_date
        and t.planned_transfer_date.year == today.year
        and t.planned_transfer_date.month == today.month
        and t.planned_transfer_date >= today
        and t.status != constants.TRANSFER_STATUS_COMPLETED
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda t: t.planned_transfer_date)
    return candidates[0]


def transfers_this_month(session: Session) -> list[Transfer]:
    """All transfers (any status) planned within the current calendar
    month, sorted by date - used to back the same banner with a count."""
    today = date.today()
    transfers = session.scalars(select(Transfer)).unique().all()
    this_month = [
        t for t in transfers
        if t.planned_transfer_date
        and t.planned_transfer_date.year == today.year
        and t.planned_transfer_date.month == today.month
    ]
    this_month.sort(key=lambda t: t.planned_transfer_date)
    return this_month


def delayed_tasks(session: Session, limit: int = 15) -> list:
    notes = notification_service.build_notifications(session)
    return [n for n in notes if n.severity == "danger"][:limit]


def _group_count(session: Session, key_fn) -> dict:
    transfers = session.scalars(select(Transfer)).unique().all()
    out: dict = {}
    for t in transfers:
        key = key_fn(t)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
