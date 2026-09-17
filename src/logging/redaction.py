"""CLAUDE.md rule 6: anything that looks like an account identifier is
replaced with [REDACTED] before it reaches the database or stdout.

Deliberately over-eager: an 8+ digit run in a headline or a stray
"account ... 5" phrase gets redacted too. Losing a number in a log line is
cheap; leaking an account number is not.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

_PATTERNS = (
    # "account 12345", "Account #: 4567-89", "account_id=778899", "accountNumber: 5XY12345"
    re.compile(r"\baccount[\w-]*[^\n\d]{0,24}\d[\w-]*", re.IGNORECASE),
    # any run of 8+ digits
    re.compile(r"\b\d{8,}\b"),
    # separated groups: 1234-5678-9012, 4111 1111 1111 1111
    re.compile(r"\b(?:\d{3,4}[ -]){2,}\d{3,4}\b"),
)


def redact(text: str) -> str:
    for pattern in _PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


def redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {redact(str(k)): redact_payload(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact_payload(v) for v in value]
    return value
