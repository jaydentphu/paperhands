"""Plain-text context bundle, one per ticker, assembled by code.

BundleInputs carries only what PRD.md section 3 allows the agent to see:
quote, indicators already computed by code, earnings date, headlines, and
the eligible contracts. There is no field for P&L, positions, or past
decisions, so they cannot leak in (PRD section 9: the agent never sees its
own P&L in Phase 1).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

HEADLINE_LIMIT = 5


@dataclass(frozen=True)
class BundleContract:
    contract_id: str
    contract_type: str
    strike: Decimal
    expiry: dt.date
    dte: int
    bid: Decimal
    ask: Decimal
    open_interest: int
    implied_vol: Decimal | None


@dataclass(frozen=True)
class BundleInputs:
    ticker: str
    as_of: dt.date
    quote: dict[str, str]
    twenty_day_return: Decimal | None
    rsi_14: Decimal | None
    earnings_date: dt.date | None
    headlines: list[dict[str, str]]
    eligible_contracts: list[BundleContract]


def _pct(value: Decimal) -> str:
    return f"{(value * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):+}%"


def _num(value: Decimal | None, places: str = "0.01") -> str:
    if value is None:
        return "n/a"
    return str(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def build_bundle(inputs: BundleInputs) -> str:
    q = inputs.quote
    lines = [
        f"TICKER: {inputs.ticker}",
        f"AS OF: {inputs.as_of.isoformat()}",
        "",
        "QUOTE",
        f"  last {q.get('last', 'n/a')}  bid {q.get('bid', 'n/a')}  ask {q.get('ask', 'n/a')}"
        f"  previous close {q.get('previous_close', 'n/a')}",
        "",
        "INDICATORS (computed by code from daily closes)",
        "  20-day return: "
        + (_pct(inputs.twenty_day_return) if inputs.twenty_day_return is not None else "n/a"),
        f"  RSI(14): {_num(inputs.rsi_14, '0.1')}",
        "",
        "EARNINGS",
    ]
    if inputs.earnings_date is None:
        lines.append("  no upcoming report date known")
    else:
        days = (inputs.earnings_date - inputs.as_of).days
        lines.append(f"  next report {inputs.earnings_date.isoformat()} ({days} days away)")

    lines += ["", f"HEADLINES (most recent {HEADLINE_LIMIT})"]
    headlines = inputs.headlines[:HEADLINE_LIMIT]
    if not headlines:
        lines.append("  none")
    for h in headlines:
        published = h.get("published_at", "")[:10]
        lines.append(f"  - [{h.get('publisher', '?')} {published}] {h.get('title', '')}")

    lines += [
        "",
        f"ELIGIBLE CONTRACTS ({len(inputs.eligible_contracts)}) - every contract below "
        "already passed the DTE, spread, open-interest, and premium rules; "
        "contract_id must be one of these ids",
        "  contract_id | type | strike | expiry | dte | bid | ask | open_interest | iv",
    ]
    if not inputs.eligible_contracts:
        lines.append("  none - the only valid action is no_trade")
    for c in inputs.eligible_contracts:
        lines.append(
            f"  {c.contract_id} | {c.contract_type} | {_num(c.strike)} | {c.expiry.isoformat()}"
            f" | {c.dte} | {_num(c.bid)} | {_num(c.ask)} | {c.open_interest}"
            f" | {_num(c.implied_vol, '0.001')}"
        )
    return "\n".join(lines)
