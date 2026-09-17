"""daily_run: create a run, snapshot every ticker, apply eligibility once
for the whole run, then run each cohort - each inside its own transaction,
so a failure in one cohort (e.g. an Anthropic API error in Cohort C) never
loses the other cohorts' already-committed work for the day - and mark
the run complete.
"""

from __future__ import annotations

import datetime as dt
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import anthropic
from sqlalchemy.orm import Session

from src.agent.runner import MessagesAPI, SdkMessages
from src.config import WATCHLIST, get_settings, market_today
from src.gateway import DataGateway
from src.gateway.factory import build_adapter, close_adapter
from src.models import Run
from src.models.db import get_sessionmaker
from src.models.enums import Cohort, RunStatus
from src.scheduler.cohorts import run_cohort_a, run_cohort_b, run_cohort_c
from src.scheduler.snapshot import snapshot_all_tickers
from src.validator.eligibility import apply_eligibility

logger = logging.getLogger(__name__)

_COHORT_RUNNERS = (
    (Cohort.A, run_cohort_a),
    (Cohort.B, run_cohort_b),
    (Cohort.C, run_cohort_c),
)


@dataclass(frozen=True)
class CohortRunResult:
    cohort: Cohort
    tickers_processed: int
    failed: bool


@dataclass(frozen=True)
class DailyRunResult:
    run_id: int
    snapshot_failed: list[str]
    cohort_results: list[CohortRunResult]


def run_daily(
    session_factory: Callable[[], Session],
    gateway: DataGateway,
    messages: MessagesAPI,
    tickers: Sequence[str],
    as_of: dt.date,
    model: str,
) -> DailyRunResult:
    with session_factory() as session:
        run = Run(run_date=as_of, status=RunStatus.RUNNING)
        session.add(run)
        session.commit()
        run_id = run.id

    _, snapshot_failed = snapshot_all_tickers(session_factory, gateway, run_id, tickers, as_of)

    with session_factory() as session:
        apply_eligibility(session, run_id, as_of)
        session.commit()

    cohort_results: list[CohortRunResult] = []
    for cohort, runner in _COHORT_RUNNERS:
        processed = 0
        with session_factory() as session:
            try:
                for ticker in tickers:
                    runner(session, gateway, messages, run_id, ticker, as_of, model)
                    processed += 1
                session.commit()
                cohort_results.append(CohortRunResult(cohort, processed, failed=False))
            except Exception:
                session.rollback()
                logger.exception(
                    "cohort %s failed for run %d after %d/%d tickers",
                    cohort.value,
                    run_id,
                    processed,
                    len(tickers),
                )
                cohort_results.append(CohortRunResult(cohort, processed, failed=True))

    with session_factory() as session:
        stored_run = session.get(Run, run_id)
        assert stored_run is not None
        stored_run.status = RunStatus.COMPLETED
        stored_run.completed_at = dt.datetime.now(dt.UTC)
        session.commit()

    return DailyRunResult(
        run_id=run_id, snapshot_failed=snapshot_failed, cohort_results=cohort_results
    )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    for noisy in ("httpx2", "mcp", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    settings = get_settings()
    if not settings.anthropic_api_key or settings.anthropic_api_key.endswith("..."):
        print("ANTHROPIC_API_KEY is not set in .env")
        return 2

    adapter = build_adapter(settings.adapter)
    gateway = DataGateway(adapter)
    messages = SdkMessages(anthropic.Anthropic(api_key=settings.anthropic_api_key))
    try:
        result = run_daily(
            get_sessionmaker(), gateway, messages, WATCHLIST, market_today(), settings.runtime_model
        )
    finally:
        close_adapter(adapter)

    failed_snapshots = ", ".join(result.snapshot_failed) if result.snapshot_failed else "none"
    print(f"run {result.run_id}: snapshot failed for {failed_snapshots}")
    for cr in result.cohort_results:
        status = "FAILED" if cr.failed else "ok"
        print(f"  cohort {cr.cohort.value}: {cr.tickers_processed} tickers processed ({status})")
    return 1 if any(cr.failed for cr in result.cohort_results) else 0


if __name__ == "__main__":
    sys.exit(main())
