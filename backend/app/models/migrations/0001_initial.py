"""Initial schema for early access trading/risk flows."""
from sqlalchemy import MetaData
from app.models.database import Base


def upgrade(engine):
    Base.metadata.create_all(bind=engine)


def downgrade(engine):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    for table in [
        "decision_receipts",
        "pnl_ledger",
        "day_state",
        "alerts_log",
        "market_requests",
        "watchlist_overrides",
        "user_rules",
        "watchlists",
        "market_access",
        "baseline_markets",
    ]:
        if table in metadata.tables:
            metadata.tables[table].drop(engine, checkfirst=True)
