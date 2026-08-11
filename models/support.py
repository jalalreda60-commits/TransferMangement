"""
models/support.py
-------------------
Cross-cutting entities attached to a Transfer: file Attachments, user
Comments, and the ActivityLog that powers the History Log requirement
and the Dashboard's "Recent Activities" table.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.transfer import Transfer


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfers.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(256))
    stored_path: Mapped[str] = mapped_column(String(1024))
    file_type: Mapped[str] = mapped_column(String(32), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transfer: Mapped["Transfer"] = relationship(back_populates="attachments")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfers.id", ondelete="CASCADE"))
    author: Mapped[str] = mapped_column(String(128), default="User")
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transfer: Mapped["Transfer"] = relationship(back_populates="comments")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transfers.id", ondelete="CASCADE"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(128))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transfer: Mapped[Optional["Transfer"]] = relationship(back_populates="activity_logs")
