"""Read-only response DTOs for the FastAPI endpoints (Stage 7). Money and
other Decimal fields are typed as str, not float, and converted explicitly
in src/api/main.py - never left to Pydantic's own ORM coercion - so JSON
output never loses precision or silently rounds.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel


class RunOut(BaseModel):
    id: int
    run_date: dt.date
    status: str
    started_at: dt.datetime
    completed_at: dt.datetime | None


class DecisionOut(BaseModel):
    id: int
    run_id: int
    cohort: str
    ticker: str
    action: str
    contract_id: str | None
    reasoning: dict[str, Any] | None
    confidence: float | None
    validator_status: str
    rejection_reason: str | None
    created_at: dt.datetime


class PositionOut(BaseModel):
    id: int
    cohort: str
    decision_id: int
    contract_id: str
    expiry: dt.date
    opened_at: dt.datetime
    open_price: str
    underlying_open: str
    underlying_close: str | None
    quantity: int
    max_loss: str
    status: str
    closed_at: dt.datetime | None
    close_price: str | None
    close_reason: str | None


class MetricsOut(BaseModel):
    cohort: str
    start: dt.date
    end: dt.date
    decisions: int
    no_trade_count: int
    trades: int
    hit_rate: str
    mean_pnl: str
    median_pnl: str
    total_pnl: str
    max_drawdown: str
    pnl_vs_cash: str


class LogOut(BaseModel):
    id: int
    run_id: int
    level: str
    component: str
    message: str
    payload: dict[str, Any] | None
    created_at: dt.datetime
