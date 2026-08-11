"""
models/release.py
--------------------
Release module (sidebar item 4). The spec names "Release" as a sidebar
module and requires the app to compute "Release Progress" on the
Dashboard, without detailing individual fields the way Preparation's
sub-modules are detailed. This model implements a release-readiness
checklist that mirrors the Preparation sub-modules (auto-checked from
their computed status, with a manual override available for anything
that needs sign-off outside the tracked data) plus the final release
decision itself: status, actual release date, released-by, and sign-off
comments.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Date, DateTime, ForeignKey, Boolean, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from utils import constants

if TYPE_CHECKING:
    from models.transfer import Transfer


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfers.id", ondelete="CASCADE"), unique=True)

    status: Mapped[str] = mapped_column(String(32), default=constants.RELEASE_STATUS_PENDING)
    release_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    released_by: Mapped[str] = mapped_column(String(128), default="")

    # Manual sign-off checklist (in addition to the automatically
    # computed Preparation progress that gates whether Release is
    # actually achievable).
    checklist_ptt_signed_off: Mapped[bool] = mapped_column(Boolean, default=False)
    checklist_safety_stock_signed_off: Mapped[bool] = mapped_column(Boolean, default=False)
    checklist_rm_signed_off: Mapped[bool] = mapped_column(Boolean, default=False)
    checklist_precheck_signed_off: Mapped[bool] = mapped_column(Boolean, default=False)
    checklist_e2e_signed_off: Mapped[bool] = mapped_column(Boolean, default=False)
    checklist_applicator_cp_signed_off: Mapped[bool] = mapped_column(Boolean, default=False)
    checklist_training_signed_off: Mapped[bool] = mapped_column(Boolean, default=False)

    sign_off_comments: Mapped[str] = mapped_column(Text, default="")
    open_actions: Mapped[str] = mapped_column(Text, default="")

    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    transfer: Mapped["Transfer"] = relationship(back_populates="release")

    def checklist_items(self) -> list[bool]:
        return [
            self.checklist_ptt_signed_off,
            self.checklist_safety_stock_signed_off,
            self.checklist_rm_signed_off,
            self.checklist_precheck_signed_off,
            self.checklist_e2e_signed_off,
            self.checklist_applicator_cp_signed_off,
            self.checklist_training_signed_off,
        ]

    def progress_pct(self) -> float:
        if self.status == constants.RELEASE_STATUS_RELEASED:
            return 100.0
        items = self.checklist_items()
        return 100.0 * sum(1 for i in items if i) / len(items) if items else 0.0
