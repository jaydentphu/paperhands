"""`make run-agent TICKER=AAPL`: run the Cohort C agent on the latest stored
snapshot for one ticker and print the candidate (or the logged rejection).

Orchestration lives here, not in src/agent/: this module touches the
database and the adapter; the agent only ever sees a text bundle, the five
gateway tools, and a logger.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sys

import anthropic
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agent.bundle import BundleContract, BundleInputs, build_bundle
from src.agent.runner import AgentOutcome, AgentRunner, SdkMessages
from src.config import WATCHLIST, get_settings
from src.gateway import DataGateway
from src.gateway.factory import build_adapter, close_adapter
from src.logging import RunLogger
from src.models import ContractSnapshot, Run, Snapshot
from src.models.db import get_sessionmaker
from src.scheduler.snapshot import PENDING_REASON
from src.screener.indicators import RETURN_WINDOW, RSI_PERIOD, rsi_14, twenty_day_return
from src.validator.candidate import validate_candidate
from src.validator.eligibility import apply_eligibility, eligible_contracts

HISTORICAL_DAYS = 40


def bundle_inputs_for_snapshot(
    session: Session, gateway: DataGateway, snapshot: Snapshot, as_of: dt.date
) -> tuple[BundleInputs, list[ContractSnapshot]]:
    contracts = eligible_contracts(session, snapshot.run_id, snapshot.ticker)
    if not contracts:
        pending = session.scalar(
            select(ContractSnapshot.id).where(
                ContractSnapshot.snapshot_id == snapshot.id,
                ContractSnapshot.ineligible_reason == PENDING_REASON,
            )
        )
        if pending is not None:
            apply_eligibility(session, snapshot.run_id, as_of)
            session.flush()
            contracts = eligible_contracts(session, snapshot.run_id, snapshot.ticker)

    bars = gateway.get_historicals(snapshot.ticker, HISTORICAL_DAYS)
    ret = twenty_day_return(bars) if len(bars) > RETURN_WINDOW else None
    rsi = rsi_14(bars) if len(bars) > RSI_PERIOD else None

    inputs = BundleInputs(
        ticker=snapshot.ticker,
        as_of=as_of,
        quote={k: str(v) for k, v in snapshot.quote.items()},
        twenty_day_return=ret,
        rsi_14=rsi,
        earnings_date=snapshot.earnings_date,
        headlines=[{k: str(v) for k, v in h.items()} for h in snapshot.news_headlines],
        eligible_contracts=[
            BundleContract(
                contract_id=c.contract_id,
                contract_type=c.contract_type.value,
                strike=c.strike,
                expiry=c.expiry,
                dte=(c.expiry - as_of).days,
                bid=c.bid,
                ask=c.ask,
                open_interest=c.open_interest,
                implied_vol=c.implied_vol,
            )
            for c in contracts
        ],
    )
    return inputs, contracts


def _print_outcome(outcome: AgentOutcome, contracts: list[ContractSnapshot]) -> None:
    if outcome.candidate is None:
        print(f"REJECTED ({outcome.rejection_reason}) after {outcome.attempts} attempt(s)")
        return
    print(outcome.candidate.model_dump_json(indent=2))
    verdict = validate_candidate(outcome.candidate, contracts)
    print(f"validator: {type(verdict).__name__}", end="")
    if hasattr(verdict, "reason"):
        print(f" ({verdict.reason})")
    elif getattr(verdict, "max_loss", None) is not None:
        print(f" max_loss={verdict.max_loss}")
    else:
        print()


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx2", "mcp", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    ticker = (argv[1] if len(argv) > 1 else os.environ.get("TICKER", "")).strip().upper()
    if ticker not in WATCHLIST:
        print(f"usage: make run-agent TICKER=<one of {', '.join(WATCHLIST)}>")
        return 2

    settings = get_settings()
    if not settings.anthropic_api_key or settings.anthropic_api_key.endswith("..."):
        print("ANTHROPIC_API_KEY is not set in .env")
        return 2

    adapter = build_adapter(settings.adapter)
    gateway = DataGateway(adapter)
    try:
        with get_sessionmaker()() as session:
            snapshot = session.scalar(
                select(Snapshot).where(Snapshot.ticker == ticker).order_by(Snapshot.id.desc())
            )
            if snapshot is None:
                print(f"no stored snapshot for {ticker}; run `make run-snapshot` first")
                return 1
            run = session.get(Run, snapshot.run_id)
            assert run is not None
            inputs, contracts = bundle_inputs_for_snapshot(session, gateway, snapshot, run.run_date)
            bundle_text = build_bundle(inputs)

            runner = AgentRunner(
                SdkMessages(anthropic.Anthropic(api_key=settings.anthropic_api_key)),
                gateway,
                RunLogger(session, snapshot.run_id),
                model=settings.runtime_model,
            )
            outcome = runner.run(ticker, bundle_text)
            session.commit()
            print(f"--- snapshot {snapshot.id} (run {snapshot.run_id}, {run.run_date}) ---")
            _print_outcome(outcome, contracts)
    finally:
        close_adapter(adapter)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
