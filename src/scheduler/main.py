"""Worker entrypoint. Schedules daily_run at RUN_TIME and daily_mark at
MARK_TIME, Mon-Fri, in America/New_York. APScheduler's cron trigger has no
NYSE-holiday concept, so each job checks is_trading_day itself and skips
(logging why) on a holiday rather than running.
"""

from __future__ import annotations

import datetime as dt
import logging
from zoneinfo import ZoneInfo

import anthropic
from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.agent.runner import SdkMessages
from src.config import (
    MARK_TIME,
    MARKET_TIMEZONE,
    RUN_TIME,
    WATCHLIST,
    get_settings,
    is_trading_day,
    market_today,
)
from src.gateway import DataGateway
from src.gateway.factory import build_adapter, close_adapter
from src.models.db import get_sessionmaker
from src.scheduler.daily_mark import run_daily_mark
from src.scheduler.daily_run import run_daily

logger = logging.getLogger(__name__)


def _daily_run_job() -> None:
    today = market_today()
    if not is_trading_day(today):
        logger.info("skipping daily_run: %s is not a trading day", today)
        return
    settings = get_settings()
    adapter = build_adapter(settings.adapter)
    gateway = DataGateway(adapter)
    messages = SdkMessages(anthropic.Anthropic(api_key=settings.anthropic_api_key))
    try:
        result = run_daily(
            get_sessionmaker(), gateway, messages, WATCHLIST, today, settings.runtime_model
        )
        logger.info("daily_run complete: run %d", result.run_id)
    except Exception:
        logger.exception("daily_run failed")
    finally:
        close_adapter(adapter)


def _daily_mark_job() -> None:
    today = market_today()
    if not is_trading_day(today):
        logger.info("skipping daily_mark: %s is not a trading day", today)
        return
    settings = get_settings()
    adapter = build_adapter(settings.adapter)
    gateway = DataGateway(adapter)
    try:
        marked, closed, evaluated = run_daily_mark(get_sessionmaker(), gateway, today)
        logger.info(
            "daily_mark complete: marked=%d closed=%d evaluated=%d", marked, closed, evaluated
        )
    except Exception:
        logger.exception("daily_mark failed")
    finally:
        close_adapter(adapter)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    for noisy in ("httpx2", "mcp", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    tz = ZoneInfo(MARKET_TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)
    run_trigger = CronTrigger(
        day_of_week="mon-fri", hour=RUN_TIME.hour, minute=RUN_TIME.minute, timezone=tz
    )
    mark_trigger = CronTrigger(
        day_of_week="mon-fri", hour=MARK_TIME.hour, minute=MARK_TIME.minute, timezone=tz
    )
    scheduler.add_job(_daily_run_job, run_trigger, id="daily_run")
    scheduler.add_job(_daily_mark_job, mark_trigger, id="daily_mark")

    now = dt.datetime.now(tz)
    for job_id, trigger in (("daily_run", run_trigger), ("daily_mark", mark_trigger)):
        next_fire = trigger.get_next_fire_time(None, now)
        logger.info("[worker] %s next scheduled run: %s", job_id, next_fire)

    scheduler.start()


if __name__ == "__main__":
    main()
