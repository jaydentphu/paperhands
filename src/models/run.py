from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.enums import RunStatus


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), nullable=False, default=RunStatus.RUNNING
    )
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
