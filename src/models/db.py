"""Engine/session helpers. Not imported by src/agent/ (CLAUDE.md rule 3:
the agent never touches the database directly, only through code in
src/validator, src/portfolio, src/evaluator)."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


def get_sessionmaker(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or get_engine())
