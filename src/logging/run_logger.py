"""Run logging with redaction applied on the way in. Two sinks share one
entry builder so the redaction path is identical: RunLogger writes
run_logs rows, MemoryLogger keeps entries in a list for tests."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy.orm import Session

from src.logging.redaction import redact, redact_payload
from src.models import RunLog
from src.models.enums import LogLevel

_stdout = logging.getLogger("run")


@dataclass(frozen=True)
class LogEntry:
    level: LogLevel
    component: str
    message: str
    payload: dict[str, Any] | None


class LogSink(Protocol):
    def log(
        self,
        level: LogLevel,
        component: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None: ...


def redacted_entry(
    level: LogLevel, component: str, message: str, payload: dict[str, Any] | None
) -> LogEntry:
    clean_payload = redact_payload(payload) if payload is not None else None
    return LogEntry(level, component, redact(message), clean_payload)


class MemoryLogger:
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def log(
        self,
        level: LogLevel,
        component: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.entries.append(redacted_entry(level, component, message, payload))


class RunLogger:
    def __init__(self, session: Session, run_id: int) -> None:
        self._session = session
        self._run_id = run_id

    def log(
        self,
        level: LogLevel,
        component: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        entry = redacted_entry(level, component, message, payload)
        self._session.add(
            RunLog(
                run_id=self._run_id,
                level=entry.level,
                component=entry.component,
                message=entry.message,
                payload=entry.payload,
            )
        )
        self._session.flush()
        _stdout.log(
            logging.getLevelName(entry.level.value.upper()),
            "[%s] %s",
            entry.component,
            entry.message,
        )
