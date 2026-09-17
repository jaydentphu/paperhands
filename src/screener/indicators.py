"""Technical indicators computed in code from historicals, shared by the
Cohort B screener and (Stage 4) the agent's context bundle - the agent
never computes these itself, only reads the numbers code already produced.

Bars are assumed ascending by date (oldest first), matching what
DataGateway.get_historicals returns.
"""

from __future__ import annotations

from decimal import Decimal

from src.gateway.types import Bar

RETURN_WINDOW = 20
RSI_PERIOD = 14


def twenty_day_return(bars: list[Bar]) -> Decimal:
    """Close-to-close return over the trailing 20 bars."""
    if len(bars) < RETURN_WINDOW + 1:
        raise ValueError(f"need at least {RETURN_WINDOW + 1} bars for a {RETURN_WINDOW}-day return")
    window = bars[-(RETURN_WINDOW + 1) :]
    start, end = window[0].close, window[-1].close
    return (end - start) / start


def rsi_14(bars: list[Bar]) -> Decimal:
    """14-period RSI from daily closes, using a simple (non-Wilder-smoothed)
    average of gains and losses - deterministic and easy to hand-verify."""
    if len(bars) < RSI_PERIOD + 1:
        raise ValueError(f"need at least {RSI_PERIOD + 1} bars for a {RSI_PERIOD}-period RSI")
    window = bars[-(RSI_PERIOD + 1) :]
    gains = Decimal(0)
    losses = Decimal(0)
    for prev, curr in zip(window, window[1:], strict=False):
        change = curr.close - prev.close
        if change > 0:
            gains += change
        else:
            losses += -change
    avg_gain = gains / RSI_PERIOD
    avg_loss = losses / RSI_PERIOD
    if avg_loss == 0:
        return Decimal(100)
    rs = avg_gain / avg_loss
    return Decimal(100) - (Decimal(100) / (1 + rs))
