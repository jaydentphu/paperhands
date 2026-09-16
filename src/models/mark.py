from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Mark(Base):
    __tablename__ = "marks"
    __table_args__ = (UniqueConstraint("position_id", "mark_date", name="uq_mark_position_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("paper_positions.id"), nullable=False)
    mark_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    bid: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
