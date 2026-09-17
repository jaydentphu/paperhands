"""daily_mark: mark, then close, then evaluate - in that order, one
combined transaction (unlike daily_run, nothing here calls the Anthropic
API or an LLM, so there's no single step likely enough to fail on its own
to justify splitting the transaction further).
"""

from __future__ import annotations

import datetime as dt
import logging
import sys
from collections.abc import Callable

from sqlalchemy.orm import Session

from src.config import get_settings, market_today
from src.evaluator import evaluate_closed_positions
from src.gateway import DataGateway
from src.gateway.factory import build_adapter, close_adapter
from src.models.db import get_sessionmaker
from src.portfolio import close_positions, mark_positions

logger = logging.getLogger(__name__)


def run_daily_mark(
    session_factory: Callable[[], Session], gateway: DataGateway, date: dt.date
) -> tuple[int, int, int]:
    with session_factory() as session:
        marked = mark_positions(session, gateway, date)
        closed = close_positions(session, gateway, date)
        evaluated = evaluate_closed_positions(session)
        session.commit()
    return marked, closed, evaluated


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    for noisy in ("httpx2", "mcp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    settings = get_settings()
    adapter = build_adapter(settings.adapter)
    gateway = DataGateway(adapter)
    try:
        marked, closed, evaluated = run_daily_mark(get_sessionmaker(), gateway, market_today())
    finally:
        close_adapter(adapter)

    print(f"marked {marked} positions, closed {closed}, evaluated {evaluated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
