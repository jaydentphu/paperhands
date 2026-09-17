from __future__ import annotations

import re

import pytest

from src.logging import REDACTED, MemoryLogger, redact, redact_payload
from src.models.enums import LogLevel


@pytest.mark.parametrize(
    "text",
    [
        "account 123456789",
        "Account #: 4567-89",
        "account_id=778899",
        "my account number is 5XY12345",
        "ref 12345678",
        "card 4111-1111-1111-1111",
        "id 1234 5678 9012",
    ],
)
def test_account_like_strings_are_redacted(text: str) -> None:
    out = redact(text)
    assert REDACTED in out
    assert re.search(r"\d{5,}", out) is None


@pytest.mark.parametrize(
    "text",
    [
        "AAPL last 331.335 bid 331.54 ask 331.64",
        "20-day return: +4.12% RSI(14): 62.3",
        "expiry 2026-10-16 dte 30 open_interest 15948",
        "contract 7dd906e5-7d4b-4161-a3fe-2c3b62038482",
        "published 2026-09-15T19:59:59.986621+00:00",
    ],
)
def test_market_data_is_left_alone(text: str) -> None:
    assert redact(text) == text


def test_redact_payload_recurses_into_dicts_and_lists() -> None:
    payload = {
        "note": "Account #: 987654321",
        "nested": ["acct 12345678", {"deep": "account 42"}],
        "price": "331.34",
        "count": 7,
    }
    out = redact_payload(payload)
    assert out["note"] == REDACTED
    assert out["nested"][0] == f"acct {REDACTED}"
    assert out["nested"][1]["deep"] == REDACTED
    assert out["price"] == "331.34"
    assert out["count"] == 7


def test_memory_logger_redacts_message_and_payload() -> None:
    logger = MemoryLogger()
    logger.log(LogLevel.INFO, "test", "account 123456789 seen", {"raw": "id 99887766"})
    entry = logger.entries[0]
    assert "123456789" not in entry.message
    assert entry.payload is not None
    assert "99887766" not in entry.payload["raw"]
