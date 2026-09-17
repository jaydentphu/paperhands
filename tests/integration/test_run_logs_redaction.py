"""Proves an account-number-like string never reaches the run_logs table."""

from __future__ import annotations

import datetime as dt
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.logging import REDACTED, RunLogger
from src.models import Run, RunLog
from src.models.enums import LogLevel, RunStatus


def test_run_logger_redacts_before_the_row_is_written(db_session: Session) -> None:
    run = Run(run_date=dt.date(2026, 9, 16), status=RunStatus.RUNNING)
    db_session.add(run)
    db_session.flush()

    RunLogger(db_session, run.id).log(
        LogLevel.INFO,
        "agent",
        "prompt mentions account 123456789 and card 4111-1111-1111-1111",
        {"system": "Account #: 987654321", "nested": ["acct 12345678"], "price": "331.34"},
    )

    row = db_session.scalar(select(RunLog).where(RunLog.run_id == run.id))
    assert row is not None
    assert "123456789" not in row.message
    assert "4111" not in row.message
    assert REDACTED in row.message
    assert row.payload is not None
    assert row.payload["price"] == "331.34"
    assert re.search(r"\d{8,}", json.dumps(row.payload)) is None
    assert re.search(r"(?i)account[^\n\d]{0,24}\d", row.message + json.dumps(row.payload)) is None
