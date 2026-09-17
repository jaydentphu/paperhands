from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.gateway import DataGateway
from src.gateway.adapters.fake import FakeAdapter
from src.models import ContractSnapshot
from src.scheduler.snapshot import PENDING_REASON, run_snapshot_job
from src.validator.eligibility import apply_eligibility

TODAY = dt.date(2026, 9, 16)


def test_apply_eligibility_produces_a_mix_of_reasons(
    db_session_factory: sessionmaker[Session],
) -> None:
    # GOOGL is the fixed seed/ticker combo that reliably clears the 5%
    # spread cap for at least one contract - not every ticker does, since
    # FakeAdapter's spread choices are randomized per (ticker, day).
    gateway = DataGateway(FakeAdapter(today=lambda: TODAY))
    run_id, results, failed = run_snapshot_job(db_session_factory, gateway, ("GOOGL",), TODAY)
    assert failed == []
    snapshot_id = results[0].snapshot_id

    with db_session_factory() as session:
        updated = apply_eligibility(session, run_id, TODAY)
        session.commit()
    assert updated == results[0].contracts

    with db_session_factory() as session:
        contracts = session.scalars(
            select(ContractSnapshot).where(ContractSnapshot.snapshot_id == snapshot_id)
        ).all()

    reasons = {c.ineligible_reason for c in contracts if not c.eligible}
    assert reasons, "expected at least one ineligible contract"
    assert PENDING_REASON not in reasons
    assert any(c.eligible for c in contracts), "expected at least one eligible contract"
