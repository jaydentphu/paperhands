"""Snapshot job: for each watchlist ticker, store one snapshot row and one
contract_snapshot row per contract in the DTE window. Each ticker commits
in its own transaction so one failure does not lose the others.

Contracts are stored with eligible=False / "pending_eligibility"; the
eligibility filter (Stage 3) is what marks them.
"""

from __future__ import annotations

import datetime as dt
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.config import DTE_MAX, DTE_MIN, SNAPSHOT_NEWS_LIMIT, WATCHLIST, get_settings, market_today
from src.gateway import DataGateway
from src.gateway.factory import build_adapter, close_adapter
from src.models import ContractSnapshot, Run, Snapshot, WatchlistSymbol
from src.models.db import get_sessionmaker
from src.models.enums import ContractType, RunStatus

logger = logging.getLogger(__name__)

PENDING_REASON = "pending_eligibility"


@dataclass(frozen=True)
class SnapshotResult:
    ticker: str
    snapshot_id: int
    contracts: int


def snapshot_ticker(
    session: Session, gateway: DataGateway, run_id: int, ticker: str, as_of: dt.date
) -> SnapshotResult:
    if session.get(WatchlistSymbol, ticker) is None:
        session.add(WatchlistSymbol(ticker=ticker))
        session.flush()

    quote = gateway.get_quote(ticker)
    contracts = gateway.get_option_chain(ticker, DTE_MIN, DTE_MAX)
    earnings_date = gateway.get_earnings_date(ticker)
    headlines = gateway.get_news(ticker, SNAPSHOT_NEWS_LIMIT)

    snapshot = Snapshot(
        run_id=run_id,
        ticker=ticker,
        quote=quote.to_json(),
        earnings_date=earnings_date,
        news_headlines=[h.to_json() for h in headlines],
    )
    session.add(snapshot)
    session.flush()

    stored = 0
    for contract in contracts:
        if not DTE_MIN <= contract.dte(as_of) <= DTE_MAX:
            continue
        session.add(
            ContractSnapshot(
                snapshot_id=snapshot.id,
                contract_id=contract.contract_id,
                contract_type=ContractType(contract.contract_type),
                strike=contract.strike,
                expiry=contract.expiry,
                bid=contract.bid,
                ask=contract.ask,
                volume=contract.volume,
                open_interest=contract.open_interest,
                implied_vol=contract.implied_vol,
                eligible=False,
                ineligible_reason=PENDING_REASON,
            )
        )
        stored += 1
    session.flush()
    return SnapshotResult(ticker=ticker, snapshot_id=snapshot.id, contracts=stored)


def run_snapshot_job(
    session_factory: Callable[[], Session],
    gateway: DataGateway,
    tickers: Sequence[str],
    as_of: dt.date,
) -> tuple[int, list[SnapshotResult], list[str]]:
    with session_factory() as session:
        run = Run(run_date=as_of, status=RunStatus.RUNNING)
        session.add(run)
        session.commit()
        run_id = run.id

    results: list[SnapshotResult] = []
    failed: list[str] = []
    for ticker in tickers:
        with session_factory() as session:
            try:
                results.append(snapshot_ticker(session, gateway, run_id, ticker, as_of))
                session.commit()
                logger.info("snapshot stored for %s: %d contracts", ticker, results[-1].contracts)
            except Exception:
                session.rollback()
                logger.exception("snapshot failed for %s", ticker)
                failed.append(ticker)

    with session_factory() as session:
        stored_run = session.get(Run, run_id)
        assert stored_run is not None
        stored_run.status = RunStatus.COMPLETED if results else RunStatus.FAILED
        stored_run.completed_at = dt.datetime.now(dt.UTC)
        session.commit()
    return run_id, results, failed


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    for noisy in ("httpx2", "mcp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    settings = get_settings()
    adapter = build_adapter(settings.adapter)
    try:
        run_id, results, failed = run_snapshot_job(
            get_sessionmaker(), DataGateway(adapter), WATCHLIST, market_today()
        )
    finally:
        close_adapter(adapter)
    for r in results:
        print(f"run {run_id}: {r.ticker} snapshot {r.snapshot_id}, {r.contracts} contracts")
    if failed:
        print(f"run {run_id}: FAILED for {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
