from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from src.config import DTE_MAX, DTE_MIN
from src.gateway import DataGateway
from src.gateway.adapters.fake import FakeAdapter
from src.gateway.types import Quote
from src.models import ContractSnapshot, Run, Snapshot
from src.models.enums import RunStatus
from src.scheduler.snapshot import PENDING_REASON, run_snapshot_job

TODAY = dt.date(2026, 9, 16)


class ExplodingAdapter(FakeAdapter):
    def get_quote(self, ticker: str) -> Quote:
        if ticker == "MSFT":
            raise RuntimeError("synthetic quote outage")
        return super().get_quote(ticker)


def test_snapshot_job_stores_one_snapshot_per_ticker_and_contract_rows(
    db_session_factory: sessionmaker[Session],
) -> None:
    gateway = DataGateway(FakeAdapter(today=lambda: TODAY))
    run_id, results, failed = run_snapshot_job(db_session_factory, gateway, ("AAPL", "MSFT"), TODAY)

    assert failed == []
    assert [r.ticker for r in results] == ["AAPL", "MSFT"]
    assert all(r.contracts > 0 for r in results)

    with db_session_factory() as session:
        run = session.get(Run, run_id)
        assert run is not None
        assert run.status == RunStatus.COMPLETED
        assert run.completed_at is not None

        snapshots = session.scalars(select(Snapshot).where(Snapshot.run_id == run_id)).all()
        assert {s.ticker for s in snapshots} == {"AAPL", "MSFT"}
        assert all("last" in s.quote and len(s.news_headlines) == 10 for s in snapshots)

        contracts = session.scalars(
            select(ContractSnapshot).where(
                ContractSnapshot.snapshot_id.in_([s.id for s in snapshots])
            )
        ).all()
        assert len(contracts) == sum(r.contracts for r in results)
        assert all(not c.eligible and c.ineligible_reason == PENDING_REASON for c in contracts)
        assert all(DTE_MIN <= (c.expiry - TODAY).days <= DTE_MAX for c in contracts)


def test_snapshot_job_isolates_a_failing_ticker(db_session_factory: sessionmaker[Session]) -> None:
    gateway = DataGateway(ExplodingAdapter(today=lambda: TODAY))
    run_id, results, failed = run_snapshot_job(db_session_factory, gateway, ("AAPL", "MSFT"), TODAY)

    assert failed == ["MSFT"]
    assert [r.ticker for r in results] == ["AAPL"]

    with db_session_factory() as session:
        run = session.get(Run, run_id)
        assert run is not None and run.status == RunStatus.COMPLETED
        stored = session.scalar(
            select(func.count()).select_from(Snapshot).where(Snapshot.run_id == run_id)
        )
        assert stored == 1
