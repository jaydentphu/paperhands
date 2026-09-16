from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.enums import ContractType


class ContractSnapshot(Base):
    __tablename__ = "contract_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_type: Mapped[ContractType] = mapped_column(
        Enum(ContractType, name="contract_type"), nullable=False
    )
    strike: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    expiry: Mapped[dt.date] = mapped_column(Date, nullable=False)
    bid: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    ask: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    open_interest: Mapped[int] = mapped_column(Integer, nullable=False)
    implied_vol: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ineligible_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
