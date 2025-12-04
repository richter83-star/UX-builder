from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.endpoints.auth import get_current_user
from app.core.watchlist import add_to_watchlist, remove_from_watchlist, watchlist_payload
from app.models.database import SessionLocal, get_db
from app.models.schemas import DecisionReceipt, WatchlistOverride, Watchlist
from app.models.enums import DecisionReason

router = APIRouter()


class WatchlistEntry(BaseModel):
    market_ticker: str
    tracked_at: datetime
    expires_at: datetime
    alerts_enabled: bool
    effective_rules: dict
    decision_trace: str


class OverridePayload(BaseModel):
    alerts_enabled: Optional[bool] = None
    edge_threshold: Optional[float] = None
    min_liquidity: Optional[float] = None
    max_spread: Optional[float] = None
    channels_json: Optional[dict] = None


@router.get("/", response_model=List[WatchlistEntry])
async def list_watchlist(current_user=Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    return watchlist_payload(db, current_user.id)


@router.post("/{market_ticker}")
async def track_market(
    market_ticker: str,
    alerts_enabled: bool = True,
    current_user=Depends(get_current_user),
    db: SessionLocal = Depends(get_db),
):
    try:
        entry = add_to_watchlist(db, current_user.id, market_ticker, None, alerts_enabled)
        return {"market_ticker": entry.market_ticker, "expires_at": entry.expires_at}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access not granted for this market")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{market_ticker}/untrack")
async def untrack_market(
    market_ticker: str,
    current_user=Depends(get_current_user),
    db: SessionLocal = Depends(get_db),
):
    remove_from_watchlist(db, current_user.id, market_ticker)
    return {"status": "removed"}


@router.get("/{market_ticker}/override", response_model=OverridePayload)
async def get_override(market_ticker: str, current_user=Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    override = (
        db.query(WatchlistOverride)
        .filter(
            WatchlistOverride.user_id == current_user.id,
            WatchlistOverride.market_ticker == market_ticker,
        )
        .first()
    )
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")
    return override


@router.put("/{market_ticker}/override", response_model=OverridePayload)
async def upsert_override(
    market_ticker: str,
    payload: OverridePayload,
    current_user=Depends(get_current_user),
    db: SessionLocal = Depends(get_db),
):
    override = (
        db.query(WatchlistOverride)
        .filter(
            WatchlistOverride.user_id == current_user.id,
            WatchlistOverride.market_ticker == market_ticker,
        )
        .first()
    )
    if not override:
        override = WatchlistOverride(user_id=current_user.id, market_ticker=market_ticker)
        db.add(override)
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(override, field, value)
    override.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(override)
    return override


@router.delete("/{market_ticker}/override")
async def delete_override(market_ticker: str, current_user=Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    override = (
        db.query(WatchlistOverride)
        .filter(
            WatchlistOverride.user_id == current_user.id,
            WatchlistOverride.market_ticker == market_ticker,
        )
        .first()
    )
    if override:
        db.delete(override)
        db.commit()
    return {"status": "deleted"}


@router.get("/decision-trace")
async def decision_trace(current_user=Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    receipts = (
        db.query(DecisionReceipt)
        .filter(DecisionReceipt.user_id == current_user.id)
        .order_by(DecisionReceipt.ts.desc())
        .limit(50)
        .all()
    )
    return receipts
