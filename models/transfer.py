"""
models/transfer.py
-------------------
Core hierarchy: Transfer -> Tool -> PartNumber.

A Transfer is the top-level project record (TRF Number, planned date,
type, activity, locations, technology). It owns one or more Tools; each
Tool owns one or more Part Numbers. Preparation-module data (PTT,
Safety Stock, RM, Pre-check, E2E, Applicator/Counter Part, Training)
hangs off Transfer / Tool / PartNumber as appropriate (see
models/preparation.py) and Release data hangs off Transfer (see
models/release.py).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Date, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from utils import constants


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    trf_number: Mapped[str] = mapped_column(String(64), index=True)
    planned_transfer_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_transfer_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    transfer_type: Mapped[str] = mapped_column(String(16), default=constants.TRANSFER_TYPES[0])
    activity: Mapped[str] = mapped_column(String(16), default=constants.ACTIVITIES[0])

    sender_location: Mapped[str] = mapped_column(String(128), default="")
    receiver_location: Mapped[str] = mapped_column(String(128), default="")
    technology: Mapped[str] = mapped_column(String(128), default="")

    status: Mapped[str] = mapped_column(String(32), default=constants.TRANSFER_STATUS_NOT_STARTED)
    preparation_progress: Mapped[float] = mapped_column(Float, default=0.0)
    release_progress: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    tools: Mapped[list["Tool"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", order_by="Tool.id"
    )
    ptt_approval: Mapped[Optional["PTTApproval"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", uselist=False
    )
    e2e_followup: Mapped[Optional["E2EFollowup"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", uselist=False
    )
    release: Mapped[Optional["Release"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", uselist=False
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", order_by="Attachment.uploaded_at.desc()"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", order_by="Comment.created_at.desc()"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", order_by="ActivityLog.created_at.desc()"
    )

    # ------------------------------------------------------------------ #
    def days_until_transfer(self) -> Optional[int]:
        if not self.planned_transfer_date:
            return None
        return (self.planned_transfer_date - date.today()).days

    def is_overdue(self) -> bool:
        days = self.days_until_transfer()
        return days is not None and days < 0 and self.status != constants.TRANSFER_STATUS_COMPLETED

    def all_part_numbers(self) -> list["PartNumber"]:
        return [pn for tool in self.tools for pn in tool.part_numbers]

    def __repr__(self):
        return f"<Transfer {self.trf_number}>"


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfers.id", ondelete="CASCADE"))
    tool_number: Mapped[str] = mapped_column(String(64), index=True)

    transfer: Mapped["Transfer"] = relationship(back_populates="tools")
    part_numbers: Mapped[list["PartNumber"]] = relationship(
        back_populates="tool", cascade="all, delete-orphan", order_by="PartNumber.id"
    )
    safety_stock: Mapped[Optional["SafetyStock"]] = relationship(
        back_populates="tool", cascade="all, delete-orphan", uselist=False
    )
    training: Mapped[Optional["Training"]] = relationship(
        back_populates="tool", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self):
        return f"<Tool {self.tool_number}>"


class PartNumber(Base):
    __tablename__ = "part_numbers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tool_id: Mapped[int] = mapped_column(ForeignKey("tools.id", ondelete="CASCADE"))
    part_number: Mapped[str] = mapped_column(String(64), index=True)

    tool: Mapped["Tool"] = relationship(back_populates="part_numbers")
    raw_material: Mapped[Optional["RawMaterial"]] = relationship(
        back_populates="part_number", cascade="all, delete-orphan", uselist=False
    )
    pre_check: Mapped[Optional["PreCheck"]] = relationship(
        back_populates="part_number", cascade="all, delete-orphan", uselist=False
    )
    applicator: Mapped[Optional["Applicator"]] = relationship(
        back_populates="part_number", cascade="all, delete-orphan", uselist=False
    )
    counter_part: Mapped[Optional["CounterPart"]] = relationship(
        back_populates="part_number", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self):
        return f"<PartNumber {self.part_number}>"


# Deferred imports so the relationship() calls above have real classes to
# resolve against, without creating an import cycle at module load time.
from models.preparation import (  # noqa: E402
    PTTApproval, SafetyStock, RawMaterial, PreCheck, E2EFollowup, Applicator, CounterPart, Training,
)
from models.release import Release  # noqa: E402
from models.support import Attachment, Comment, ActivityLog  # noqa: E402
