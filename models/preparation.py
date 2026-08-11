"""
models/preparation.py
-----------------------
All "Preparation" module entities from the spec:

  3.1 PTT Approval        -> PTTApproval (one per Transfer) + OEMApproval (many)
  3.2 Safety Stock         -> SafetyStock (one per Tool)
  3.3 Raw Material         -> RawMaterial (one per PartNumber)
  3.4 Pre-check            -> PreCheck (one per PartNumber)
  3.5 E2E Follow-up        -> E2EFollowup (one per Transfer)
  3.6 Applicator / Counter Part -> Applicator / CounterPart (one per PartNumber,
                                    shown depending on Transfer.activity)
  3.7 Training              -> Training (one per Tool)

Each entity exposes a small `.status_summary()` / `.progress()` helper
used by services/progress_service.py to roll up automatic progress
calculations at the Tool, Transfer and Dashboard level.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Date, DateTime, ForeignKey, Float, Boolean, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from utils import constants

if TYPE_CHECKING:
    from models.transfer import Transfer, Tool, PartNumber


# ======================================================================
# 3.1 PTT Approval
# ======================================================================
class PTTApproval(Base):
    __tablename__ = "ptt_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfers.id", ondelete="CASCADE"), unique=True)

    # Step 1: Internal Approval
    internal_status: Mapped[str] = mapped_column(String(32), default="Not Started")
    internal_responsible: Mapped[str] = mapped_column(String(128), default="")
    internal_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    internal_approval_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    internal_comments: Mapped[str] = mapped_column(Text, default="")

    transfer: Mapped["Transfer"] = relationship(back_populates="ptt_approval")
    oem_approvals: Mapped[list["OEMApproval"]] = relationship(
        back_populates="ptt_approval", cascade="all, delete-orphan", order_by="OEMApproval.id"
    )

    def overall_status(self) -> str:
        """Step 2 (OEM) automatically rolls up: internal must be Approved
        AND every OEM must be Approved for the overall status to read
        Approved; any Rejected OEM makes the overall Rejected; otherwise
        Ongoing once anything has started, else Not Started."""
        oem_statuses = [o.status for o in self.oem_approvals]
        if "Rejected" in oem_statuses:
            return "Rejected"
        if self.internal_status == "Approved" and oem_statuses and all(s == "Approved" for s in oem_statuses):
            return "Approved"
        if self.internal_status == "Approved" and not oem_statuses:
            return "Approved"
        if self.internal_status == "Not Started" and not any(s != "Not Started" for s in oem_statuses):
            return "Not Started"
        return "Ongoing"

    def progress(self) -> float:
        steps = [1 if self.internal_status == "Approved" else 0]
        steps += [1 if o.status == "Approved" else 0 for o in self.oem_approvals]
        return 100.0 * sum(steps) / len(steps) if steps else 0.0


class OEMApproval(Base):
    __tablename__ = "oem_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    ptt_approval_id: Mapped[int] = mapped_column(ForeignKey("ptt_approvals.id", ondelete="CASCADE"))

    oem_name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="Not Started")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    approval_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    comments: Mapped[str] = mapped_column(Text, default="")

    ptt_approval: Mapped["PTTApproval"] = relationship(back_populates="oem_approvals")


# ======================================================================
# 3.2 Safety Stock Build-up (one per Tool)
# ======================================================================
class SafetyStock(Base):
    __tablename__ = "safety_stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    tool_id: Mapped[int] = mapped_column(ForeignKey("tools.id", ondelete="CASCADE"), unique=True)

    required: Mapped[bool] = mapped_column(Boolean, default=False)
    start_week: Mapped[str] = mapped_column(String(16), default="")   # e.g. "WK03-2026"
    number_of_weeks: Mapped[int] = mapped_column(Integer, default=0)
    required_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    built_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    finish_week: Mapped[str] = mapped_column(String(16), default="")

    tool: Mapped["Tool"] = relationship(back_populates="safety_stock")

    def progress_pct(self) -> float:
        if not self.required or not self.required_quantity:
            return 100.0 if not self.required else 0.0
        return max(0.0, min(100.0, 100.0 * self.built_quantity / self.required_quantity))

    def status(self) -> str:
        if not self.required:
            return "NA"
        pct = self.progress_pct()
        if pct >= 100:
            return "Done"
        if pct > 0:
            return "Ongoing"
        return "Not Started"


# ======================================================================
# 3.3 Raw Material Follow-up (one per PartNumber)
# ======================================================================
class RawMaterial(Base):
    __tablename__ = "raw_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_number_id: Mapped[int] = mapped_column(ForeignKey("part_numbers.id", ondelete="CASCADE"), unique=True)

    subgroup_status: Mapped[str] = mapped_column(String(16), default="NA")   # NA/Ongoing/Done
    setup_status: Mapped[str] = mapped_column(String(16), default="NA")
    order_status: Mapped[str] = mapped_column(String(16), default="NA")
    availability_status: Mapped[str] = mapped_column(String(16), default="NA")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")

    part_number: Mapped["PartNumber"] = relationship(back_populates="raw_material")

    def overall_status(self) -> str:
        statuses = [self.subgroup_status, self.setup_status, self.order_status, self.availability_status]
        if all(s in ("Done", "NA") for s in statuses):
            return "Done" if any(s == "Done" for s in statuses) else "NA"
        if any(s == "Ongoing" for s in statuses):
            return "Ongoing"
        return "NA"

    def progress_pct(self) -> float:
        statuses = [self.subgroup_status, self.setup_status, self.order_status, self.availability_status]
        relevant = [s for s in statuses if s != "NA"] or statuses
        if not relevant:
            return 100.0
        done = sum(1 for s in relevant if s == "Done")
        return 100.0 * done / len(relevant)


# ======================================================================
# 3.4 Pre-check (one per PartNumber)
# ======================================================================
class PreCheck(Base):
    __tablename__ = "pre_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_number_id: Mapped[int] = mapped_column(ForeignKey("part_numbers.id", ondelete="CASCADE"), unique=True)

    pe_responsible: Mapped[str] = mapped_column(String(128), default="")
    samples_before_status: Mapped[str] = mapped_column(String(16), default="NA")     # NA/Ongoing/Received
    pe_requirement_status: Mapped[str] = mapped_column(String(16), default="NA")
    measurement_report_status: Mapped[str] = mapped_column(String(16), default="NA")
    feedback_status: Mapped[str] = mapped_column(String(16), default="NA")           # NA/Ongoing/Accepted/Rejected
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actions: Mapped[str] = mapped_column(Text, default="")
    comments: Mapped[str] = mapped_column(Text, default="")

    part_number: Mapped["PartNumber"] = relationship(back_populates="pre_check")

    def progress_pct(self) -> float:
        if self.feedback_status == "Accepted":
            return 100.0
        if self.feedback_status == "Rejected":
            return 0.0
        statuses = [self.samples_before_status, self.pe_requirement_status, self.measurement_report_status]
        relevant = [s for s in statuses if s != "NA"] or statuses
        done = sum(1 for s in relevant if s == "Received")
        base = 100.0 * done / len(relevant) if relevant else 0.0
        return min(base, 90.0)  # capped below 100 until feedback is Accepted


# ======================================================================
# 3.5 E2E Follow-up (one per Transfer) - three mandatory meetings
# ======================================================================
class E2EFollowup(Base):
    __tablename__ = "e2e_followups"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfers.id", ondelete="CASCADE"), unique=True)

    # Kick-off Call
    kickoff_week: Mapped[str] = mapped_column(String(16), default="")
    kickoff_status: Mapped[str] = mapped_column(String(16), default="Not Started")

    # PCN & PPAP Call
    pcn_ppap_week: Mapped[str] = mapped_column(String(16), default="")
    pcn_ppap_status: Mapped[str] = mapped_column(String(16), default="Not Started")
    pcn_decision: Mapped[bool] = mapped_column(Boolean, default=False)
    pcn_status: Mapped[str] = mapped_column(String(16), default="Not Sent")   # Not Sent/Sent/Ongoing/Approved
    action_list: Mapped[str] = mapped_column(Text, default="")

    # SOP Readiness Call
    sop_week: Mapped[str] = mapped_column(String(16), default="")
    sop_status: Mapped[str] = mapped_column(String(16), default="Not Started")

    link_file: Mapped[str] = mapped_column(String(512), default="")
    comments: Mapped[str] = mapped_column(Text, default="")
    open_actions: Mapped[str] = mapped_column(Text, default="")

    transfer: Mapped["Transfer"] = relationship(back_populates="e2e_followup")

    def progress_pct(self) -> float:
        steps = [self.kickoff_status == "Done", self.sop_status == "Done"]
        if self.pcn_decision:
            steps.append(self.pcn_status == "Approved")
        else:
            steps.append(self.pcn_ppap_status == "Done")
        return 100.0 * sum(steps) / len(steps)


# ======================================================================
# 3.6 Applicator / Counter Part Check (one per PartNumber, shown based
#     on Transfer.activity: Applicator for Stamping, CounterPart for
#     Molding)
# ======================================================================
class Applicator(Base):
    __tablename__ = "applicators"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_number_id: Mapped[int] = mapped_column(ForeignKey("part_numbers.id", ondelete="CASCADE"), unique=True)

    pe: Mapped[str] = mapped_column(String(128), default="")
    urgency: Mapped[str] = mapped_column(String(16), default="Medium")
    applicator_required: Mapped[bool] = mapped_column(Boolean, default=True)
    applicator: Mapped[str] = mapped_column(String(128), default="")
    crimping_specification: Mapped[str] = mapped_column(String(128), default="")
    terminal: Mapped[str] = mapped_column(String(128), default="")
    wire_section: Mapped[str] = mapped_column(String(64), default="")
    number_of_parts: Mapped[int] = mapped_column(Integer, default=0)
    required_approvals: Mapped[str] = mapped_column(String(128), default="")
    applicator_available_location: Mapped[str] = mapped_column(String(128), default="")
    crimping_request: Mapped[str] = mapped_column(String(16), default="Not Started")
    comments: Mapped[str] = mapped_column(Text, default="")

    part_number: Mapped["PartNumber"] = relationship(back_populates="applicator")

    def status(self) -> str:
        if not self.applicator_required:
            return "NA"
        return self.crimping_request

    def progress_pct(self) -> float:
        if not self.applicator_required:
            return 100.0
        return 100.0 if self.crimping_request == "Done" else (50.0 if self.crimping_request == "Ongoing" else 0.0)


class CounterPart(Base):
    __tablename__ = "counter_parts"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_number_id: Mapped[int] = mapped_column(ForeignKey("part_numbers.id", ondelete="CASCADE"), unique=True)

    pe: Mapped[str] = mapped_column(String(128), default="")
    counter_part: Mapped[str] = mapped_column(String(128), default="")
    terminal: Mapped[str] = mapped_column(String(128), default="")
    crimping: Mapped[str] = mapped_column(String(128), default="")
    terminal_request: Mapped[str] = mapped_column(String(16), default="Not Started")
    status_field: Mapped[str] = mapped_column("status", String(16), default="Not Started")
    comments: Mapped[str] = mapped_column(Text, default="")

    part_number: Mapped["PartNumber"] = relationship(back_populates="counter_part")

    def progress_pct(self) -> float:
        return 100.0 if self.status_field == "Done" else (50.0 if self.status_field == "Ongoing" else 0.0)


# ======================================================================
# 3.7 Training (one per Tool)
# ======================================================================
class Training(Base):
    __tablename__ = "trainings"

    id: Mapped[int] = mapped_column(primary_key=True)
    tool_id: Mapped[int] = mapped_column(ForeignKey("tools.id", ondelete="CASCADE"), unique=True)

    required: Mapped[bool] = mapped_column(Boolean, default=False)
    planned_week: Mapped[str] = mapped_column(String(16), default="")
    duration: Mapped[str] = mapped_column(String(64), default="")
    invitation_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="Not Started")   # Not Started/Ongoing/Done
    comments: Mapped[str] = mapped_column(Text, default="")

    tool: Mapped["Tool"] = relationship(back_populates="training")

    def progress_pct(self) -> float:
        if not self.required:
            return 100.0
        return 100.0 if self.status == "Done" else (50.0 if self.status == "Ongoing" else 0.0)
