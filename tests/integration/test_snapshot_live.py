"""Runs the snapshot job against the live Robinhood adapter for one ticker.
Needs network and the token from `make robinhood-auth`; opt in with
ROBINHOOD_LIVE_TESTS=1 so CI skips it."""

from __future__ import annotations

import os

import pytest
from sqlalchemy.orm import Session

from src.config import market_today
from src.gateway import DataGateway
from src.gateway.adapters.robinhood import RobinhoodAdapter
from src.models import Run
from src.models.enums import RunStatus
from src.scheduler.snapshot import snapshot_ticker

pytestmark = pytest.mark.skipif(
    os.environ.get("ROBINHOOD_LIVE_TESTS") != "1",
    reason="set ROBINHOOD_LIVE_TESTS=1 to run against the live Robinhood MCP",
)


def test_live_snapshot_for_one_ticker(db_session: Session) -> None:
    adapter = RobinhoodAdapter()
    try:
        run = Run(run_date=market_today(), status=RunStatus.RUNNING)
        db_session.add(run)
        db_session.flush()
        result = snapshot_ticker(db_session, DataGateway(adapter), run.id, "AAPL", market_today())
    finally:
        adapter.close()
    assert result.contracts > 0
