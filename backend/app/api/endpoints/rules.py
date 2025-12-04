from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.endpoints.auth import get_current_user
from app.models.database import SessionLocal, get_db
from app.models.schemas import UserRules

router = APIRouter()


class RulePayload(BaseModel):
    alerts_enabled_default: bool | None = None
    edge_threshold_default: float | None = None
    max_alerts_per_day: int | None = None
    digest_mode: str | None = None
    digest_time: str | None = None
    channels_json: dict | None = None
    min_liquidity: float | None = None
    max_spread: float | None = None


@router.get("/")
async def get_rules(current_user=Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    rules = db.query(UserRules).filter(UserRules.user_id == current_user.id).first()
    if not rules:
        rules = UserRules(user_id=current_user.id)
        db.add(rules)
        db.commit()
        db.refresh(rules)
    return rules


@router.put("/")
async def update_rules(payload: RulePayload, current_user=Depends(get_current_user), db: SessionLocal = Depends(get_db)):
    rules = db.query(UserRules).filter(UserRules.user_id == current_user.id).first()
    if not rules:
        rules = UserRules(user_id=current_user.id)
        db.add(rules)
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(rules, field, value)
    db.commit()
    db.refresh(rules)
    return rules
