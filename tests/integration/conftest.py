from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from alembic import command

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/options_agent"
)


def _postgres_reachable() -> bool:
    # A short connect_timeout matters: without one, a dead/unreachable
    # Postgres can make this hang the whole suite for minutes instead of
    # skipping cleanly, which defeats the point of a reachability check.
    try:
        engine = sa.create_engine(DATABASE_URL, connect_args={"connect_timeout": 3})
        with engine.connect():
            return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def migrated_engine() -> Iterator[sa.Engine]:
    if not _postgres_reachable():
        message = f"Postgres not reachable at {DATABASE_URL}"
        # Skipping is right on a laptop with Docker down. In CI the service
        # is supposed to be there, and a skip would turn a broken service
        # into a green check - so CI sets REQUIRE_POSTGRES=1 and fails.
        if os.environ.get("REQUIRE_POSTGRES") == "1":
            pytest.fail(f"{message} (REQUIRE_POSTGRES=1, refusing to skip)")
        pytest.skip(message)
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


@pytest.fixture
def db_session_factory(migrated_engine: sa.Engine) -> Iterator[sessionmaker[Session]]:
    """Sessions whose commit() only releases a savepoint; everything rolls
    back at teardown, so jobs that commit per ticker leave no residue."""
    connection = migrated_engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield factory
    finally:
        transaction.rollback()
        connection.close()
