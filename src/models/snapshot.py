from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (UniqueConstraint("run_id", "ticker", name="uq_snapshot_run_ticker"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(
        String(10), ForeignKey("watchlist_symbols.ticker"), nullable=False
    )
    quote: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    earnings_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    news_headlines: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
