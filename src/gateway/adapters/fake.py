"""Deterministic synthetic adapter for tests and dry runs. Same ticker, same
day, same seed -> same data. Deliberately produces a mix of contracts that
pass and fail the PRD section 4 eligibility rules."""

from __future__ import annotations

import datetime as dt
import math
import random
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal

from src.config import market_today
from src.gateway.types import Bar, ContractKind, Headline, OptionContract, Quote

CENT = Decimal("0.01")
STRIKE_STEPS_EACH_SIDE = 8


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _strike_step(spot: Decimal) -> Decimal:
    # ~2.5% of spot, snapped to a 2.5 grid, so the ladder spans about +/-20%
    # and the far-OTM contracts land under the $300 premium cap.
    raw = spot * Decimal("0.025") / Decimal("2.5")
    return max(Decimal("2.5"), raw.to_integral_value(rounding=ROUND_HALF_UP) * Decimal("2.5"))


class FakeAdapter:
    def __init__(self, today: Callable[[], dt.date] = market_today, seed: int = 0) -> None:
        self._today = today
        self._seed = seed

    def _rng(self, ticker: str, salt: str) -> random.Random:
        return random.Random(f"{self._seed}:{ticker}:{salt}")

    def _spot(self, ticker: str) -> Decimal:
        return Decimal(50 + sum(ord(c) for c in ticker) % 400)

    def get_quote(self, ticker: str) -> Quote:
        spot = self._spot(ticker)
        return Quote(
            ticker=ticker,
            last=spot,
            bid=_cents(spot - Decimal("0.05")),
            ask=_cents(spot + Decimal("0.05")),
            previous_close=_cents(spot * Decimal("0.99")),
            as_of=dt.datetime.now(dt.UTC),
        )

    def get_option_chain(self, ticker: str, min_dte: int, max_dte: int) -> list[OptionContract]:
        today = self._today()
        spot = self._spot(ticker)
        rng = self._rng(ticker, "chain")
        offsets = sorted({min_dte + 2, (min_dte + max_dte) // 2, max_dte - 1})
        expiries = [today + dt.timedelta(days=d) for d in offsets if min_dte <= d <= max_dte]
        step_size = _strike_step(spot)
        atm = (spot / step_size).to_integral_value(rounding=ROUND_HALF_UP) * step_size
        contracts: list[OptionContract] = []
        for expiry in expiries:
            dte = (expiry - today).days
            for step in range(-STRIKE_STEPS_EACH_SIDE, STRIKE_STEPS_EACH_SIDE + 1):
                strike = atm + step_size * step
                for kind in ("call", "put"):
                    contracts.append(self._contract(ticker, kind, strike, expiry, dte, spot, rng))
        return contracts

    def _contract(
        self,
        ticker: str,
        kind: ContractKind,
        strike: Decimal,
        expiry: dt.date,
        dte: int,
        spot: Decimal,
        rng: random.Random,
    ) -> OptionContract:
        signed = spot - strike if kind == "call" else strike - spot
        intrinsic = max(signed, Decimal(0))
        iv = Decimal(str(round(rng.uniform(0.2, 0.5), 6)))
        years = dte / 365
        # Rough Black-Scholes shape: time value peaks at the money and decays
        # with moneyness, so far-OTM contracts get realistically cheap.
        moneyness = float(strike / spot) - 1.0
        decay = math.exp(-(moneyness**2) / (2 * float(iv) ** 2 * years))
        time_value = spot * iv * Decimal(str(round(years**0.5 * 0.4 * decay, 6)))
        mid = intrinsic + time_value
        spread_pct = Decimal(str(rng.choice([0.04, 0.06, 0.08, 0.20])))
        half = mid * spread_pct / 2
        bid = _cents(mid - half)
        ask = _cents(mid + half)
        if mid < Decimal("0.05"):
            bid = Decimal("0.00")
        code = "C" if kind == "call" else "P"
        contract_id = f"{ticker}{expiry:%y%m%d}{code}{int(strike * 1000):08d}"
        return OptionContract(
            contract_id=contract_id,
            ticker=ticker,
            contract_type=kind,
            strike=strike.quantize(Decimal("0.0001")),
            expiry=expiry,
            bid=bid,
            ask=ask,
            volume=rng.choice([0, 12, 150, 900]),
            open_interest=rng.choice([50, 300, 800, 2500]),
            implied_vol=iv,
        )

    def get_historicals(self, ticker: str, days: int) -> list[Bar]:
        today = self._today()
        rng = self._rng(ticker, "bars")
        price = self._spot(ticker) * Decimal("0.95")
        bars: list[Bar] = []
        day = today - dt.timedelta(days=days * 2)
        while len(bars) < days:
            if day.weekday() < 5:
                change = Decimal(str(round(rng.uniform(-0.02, 0.022), 5)))
                open_ = price
                close = _cents(price * (1 + change))
                high = _cents(max(open_, close) * Decimal("1.005"))
                low = _cents(min(open_, close) * Decimal("0.995"))
                volume = rng.randint(1_000_000, 9_000_000)
                bars.append(Bar(day, _cents(open_), high, low, close, volume))
                price = close
            day += dt.timedelta(days=1)
        return bars[-days:]

    def get_earnings_date(self, ticker: str) -> dt.date | None:
        checksum = sum(ord(c) for c in ticker)
        if checksum % 2:
            return None
        return self._today() + dt.timedelta(days=10 + checksum % 30)

    def get_news(self, ticker: str, limit: int) -> list[Headline]:
        now = dt.datetime.now(dt.UTC)
        return [
            Headline(
                title=f"{ticker} synthetic headline {i + 1}",
                publisher="FakeWire",
                published_at=now - dt.timedelta(hours=i),
            )
            for i in range(limit)
        ]
