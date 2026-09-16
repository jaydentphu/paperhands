from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class WatchlistSymbol(Base):
    __tablename__ = "watchlist_symbols"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    added_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
