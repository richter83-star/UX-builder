from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.compiler import compiles

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):  # pragma: no cover
    return "BLOB"

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.core.risk_engine as risk_engine
from app.core.risk_engine import risk_gate
from app.models.database import Base
from app.models.enums import DecisionReason, KillState
from app.models.schemas import DayState, PNLLedger, Watchlist, WatchlistOverride
from app.utils import config


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, tables=[
        DayState.__table__,
        PNLLedger.__table__,
        Watchlist.__table__,
        WatchlistOverride.__table__,
    ])
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal


def test_soft_hysteresis_triggers_after_second_tick(monkeypatch):
    monkeypatch.setattr(config.settings, "TRADING_MODE", "live")
    monkeypatch.setattr(risk_engine, "_count_open_positions", lambda db, uid: 0)
    SessionLocal = setup_db()
    db = SessionLocal()
    user_id = uuid.uuid4()
    now = datetime.utcnow()
    db.add(
        DayState(
            user_id=user_id,
            date_local=now.strftime("%Y-%m-%d"),
            start_equity=Decimal("1000"),
            realized_pnl_today=Decimal("0"),
            daily_spend=Decimal("0"),
        )
    )
    db.add(
        PNLLedger(
            user_id=user_id,
            market_ticker="TICK",
            realized_pnl=Decimal("-25"),
            opened_at=now,
            closed_at=now,
            qty=1,
            entry_price=Decimal("10"),
            exit_price=Decimal("0"),
        )
    )
    db.commit()

    first = risk_gate(db, user_id, "TICK", "open", Decimal("10"), now)
    assert first.kill_state == KillState.NONE

    later = risk_gate(db, user_id, "TICK", "open", Decimal("10"), now + timedelta(seconds=65))
    assert later.kill_state == KillState.SOFT
    assert later.size_multiplier == 0.5
    assert later.reason_code == DecisionReason.SOFT_THROTTLE.value


def test_hard_kill_stops_opens(monkeypatch):
    monkeypatch.setattr(config.settings, "TRADING_MODE", "live")
    monkeypatch.setattr(risk_engine, "_count_open_positions", lambda db, uid: 0)
    SessionLocal = setup_db()
    db = SessionLocal()
    user_id = uuid.uuid4()
    now = datetime.utcnow()
    db.add(
        DayState(
            user_id=user_id,
            date_local=now.strftime("%Y-%m-%d"),
            start_equity=Decimal("1000"),
            realized_pnl_today=Decimal("0"),
            daily_spend=Decimal("0"),
        )
    )
    db.add(
        PNLLedger(
            user_id=user_id,
            market_ticker="TICK",
            realized_pnl=Decimal("-40"),
            opened_at=now,
            closed_at=now,
            qty=1,
            entry_price=Decimal("10"),
            exit_price=Decimal("0"),
        )
    )
    db.commit()

    first = risk_gate(db, user_id, "TICK", "open", Decimal("10"), now)
    assert first.allow_new_open is False or first.kill_state in (KillState.NONE, KillState.HARD)

    later = risk_gate(db, user_id, "TICK", "open", Decimal("10"), now + timedelta(seconds=70))
    assert later.kill_state == KillState.HARD
    assert later.allow_new_open is False
    assert later.reason_code == DecisionReason.KILL_HARD.value


def test_daily_cap_blocks(monkeypatch):
    monkeypatch.setattr(config.settings, "TRADING_MODE", "live")
    monkeypatch.setattr(risk_engine, "_count_open_positions", lambda db, uid: 0)
    SessionLocal = setup_db()
    db = SessionLocal()
    user_id = uuid.uuid4()
    now = datetime.utcnow()
    db.add(
        DayState(
            user_id=user_id,
            date_local=now.strftime("%Y-%m-%d"),
            start_equity=Decimal("1000"),
            realized_pnl_today=Decimal("0"),
            daily_spend=Decimal("95"),
        )
    )
    db.commit()
    result = risk_gate(db, user_id, "TICK", "open", Decimal("10"), now)
    assert result.allow_new_open is False
    assert result.reason_code == DecisionReason.DAILY_CAP_REACHED.value
