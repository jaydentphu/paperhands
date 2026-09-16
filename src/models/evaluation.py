from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    position_id: Mapped[int] = mapped_column(
        ForeignKey("paper_positions.id"), unique=True, nullable=False
    )
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    direction_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
