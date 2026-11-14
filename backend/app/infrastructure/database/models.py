"""SQLAlchemy ORM models (infrastructure persistence)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.time import utc_now
from .base import Base


class DownloadTaskModel(Base):
    __tablename__ = "download_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    total_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    results: Mapped[List["RequestResultModel"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="RequestResultModel.request_index",
    )


class RequestResultModel(Base):
    __tablename__ = "request_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("download_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_index: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    bytes_downloaded: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    task: Mapped["DownloadTaskModel"] = relationship(back_populates="results")
