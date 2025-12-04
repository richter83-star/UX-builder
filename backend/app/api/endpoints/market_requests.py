from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.endpoints.auth import get_current_user
from app.models.database import SessionLocal, get_db
from app.models.enums import MarketRequestStatus
from app.models.schemas import MarketRequest

router = APIRouter()


class MarketRequestPayload(BaseModel):
    market_ticker: Optional[str] = None
    query_text: Optional[str] = None
    reason_text: Optional[str] = None


@router.post("/")
async def create_request(payload: MarketRequestPayload, current_user=Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    if not payload.market_ticker and not payload.query_text:
        raise HTTPException(status_code=400, detail="Ticker or query_text required")
    request = MarketRequest(
        user_id=current_user.id,
        market_ticker=payload.market_ticker,
        query_text=payload.query_text,
        reason_text=payload.reason_text,
        status=MarketRequestStatus.PENDING.value,
        created_at=datetime.utcnow(),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request
