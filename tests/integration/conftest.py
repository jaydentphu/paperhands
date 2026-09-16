from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy.orm import Session

from alembic import command

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/options_agent"
)


def _postgres_reachable() -> bool:
    try:
        engine = sa.create_engine(DATABASE_URL)
        with engine.connect():
            return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def migrated_engine() -> Iterator[sa.Engine]:
    if not _postgres_reachable():
        pytest.skip(f"Postgres not reachable at {DATABASE_URL}")
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")
    engine = sa.create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(migrated_engine: sa.Engine) -> Iterator[Session]:
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
