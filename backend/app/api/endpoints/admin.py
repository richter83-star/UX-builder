from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.endpoints.auth import get_current_user
from app.models.database import SessionLocal, get_db
from app.models.enums import AccessSource, AccessStatus, MarketRequestStatus
from app.models.schemas import BaselineMarket, MarketAccess, MarketRequest

router = APIRouter()


class ApprovePayload(BaseModel):
    reviewer_id: str | None = None
    notes: str | None = None


@router.post("/baseline/seed")
async def seed_baseline(current_user=Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    existing = db.query(BaselineMarket).count()
    if existing:
        return {"status": "noop", "count": existing}
    sample_markets = [
        ("TICKER01", "Baseline Market 1"),
        ("TICKER02", "Baseline Market 2"),
        ("TICKER03", "Baseline Market 3"),
        ("TICKER04", "Baseline Market 4"),
        ("TICKER05", "Baseline Market 5"),
        ("TICKER06", "Baseline Market 6"),
        ("TICKER07", "Baseline Market 7"),
        ("TICKER08", "Baseline Market 8"),
        ("TICKER09", "Baseline Market 9"),
        ("TICKER10", "Baseline Market 10"),
    ]
    for idx, (ticker, name) in enumerate(sample_markets, start=1):
        db.add(
            BaselineMarket(
                market_ticker=ticker,
                name=name,
                enabled=True,
                priority=idx,
                seed_version="v1",
                seeded_at=datetime.utcnow(),
            )
        )
    db.commit()
    return {"status": "seeded", "count": 10}


@router.post("/market-requests/{request_id}/approve")
async def approve_request(
    request_id: str,
    payload: ApprovePayload,
    current_user=Depends(get_current_user),
    db: SessionLocal = Depends(get_db),
):
    req = db.query(MarketRequest).filter(MarketRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = MarketRequestStatus.APPROVED.value
    req.reviewer_id = payload.reviewer_id or str(current_user.id)
    req.reviewed_at = datetime.utcnow()
    req.notes = payload.notes
    db.commit()
    return req


@router.post("/market-requests/{request_id}/reject")
async def reject_request(
    request_id: str,
    payload: ApprovePayload,
    current_user=Depends(get_current_user),
    db: SessionLocal = Depends(get_db),
):
    req = db.query(MarketRequest).filter(MarketRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = MarketRequestStatus.REJECTED.value
    req.reviewer_id = payload.reviewer_id or str(current_user.id)
    req.reviewed_at = datetime.utcnow()
    req.notes = payload.notes
    db.commit()
    return req
