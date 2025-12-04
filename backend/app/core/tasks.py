import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Callable

from loguru import logger
from sqlalchemy.orm import Session

from app.core.risk_engine import risk_gate
from app.core.watchlist import cleanup_expired
from app.models.database import SessionLocal
from app.models.schemas import DecisionReceipt, Watchlist
from app.utils.config import settings


async def watchlist_expiry_job():
    while True:
        try:
            db: Session = SessionLocal()
            removed = cleanup_expired(db)
            if removed:
                logger.info(f"Expired watchlist entries cleaned: {removed}")
            db.close()
        except Exception as exc:
            logger.error(f"watchlist_expiry_job failure: {exc}")
        await asyncio.sleep(1800)


async def heartbeat_job():
    while True:
        try:
            db: Session = SessionLocal()
            now = datetime.utcnow()
            entries = db.query(Watchlist).filter(Watchlist.expires_at > now).all()
            for entry in entries:
                gate = risk_gate(db, entry.user_id, entry.market_ticker, "heartbeat", Decimal("0"), now)
                receipt = DecisionReceipt(
                    user_id=entry.user_id,
                    market_ticker=entry.market_ticker,
                    ts=now,
                    allowed=gate.allow_new_open,
                    reason_code=gate.reason_code,
                    kill_state=gate.kill_state.value,
                    spend_snapshot=gate.effective_limits,
                )
                db.add(receipt)
            db.commit()
            db.close()
        except Exception as exc:
            logger.error(f"heartbeat_job failure: {exc}")
        await asyncio.sleep(settings.HEARTBEAT_INTERVAL_SECONDS)


async def start_background_jobs():
    await asyncio.gather(
        watchlist_expiry_job(),
        heartbeat_job(),
    )
