"""Enumerations shared across models. Values are the PRD's own vocabulary
(action names, cohort labels, etc.) so they read the same in the DB as in
PRD.md."""

from __future__ import annotations

import enum


class Cohort(enum.StrEnum):
    A = "A"
    B = "B"
    C = "C"


class Action(enum.StrEnum):
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    NO_TRADE = "no_trade"


class ContractType(enum.StrEnum):
    CALL = "call"
    PUT = "put"


class ValidatorStatus(enum.StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class PositionStatus(enum.StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class CloseReason(enum.StrEnum):
    HORIZON = "horizon"
    PRE_EXPIRY = "pre_expiry"


class RunStatus(enum.StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LogLevel(enum.StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
