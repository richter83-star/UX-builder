from datetime import datetime, timedelta
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

from app.core.watchlist import cleanup_expired, compute_expiry
from app.models.database import Base
from app.models.schemas import Watchlist


def test_expiry_adds_24h():
    close = datetime(2024, 1, 1, 12, 0, 0)
    expected = close + timedelta(hours=24)
    assert compute_expiry(close) == expected


def test_cleanup_removes_expired():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, tables=[Watchlist.__table__])
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    now = datetime.utcnow()
    user_id = uuid.uuid4()
    db.add(Watchlist(user_id=user_id, market_ticker="A", expires_at=now - timedelta(hours=1)))
    db.add(Watchlist(user_id=user_id, market_ticker="B", expires_at=now + timedelta(hours=2)))
    db.commit()
    removed = cleanup_expired(db, now)
    assert removed == 1
    remaining = db.query(Watchlist).count()
    assert remaining == 1
