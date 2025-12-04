from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import DecisionReason, KillState
from app.models.schemas import DayState, PNLLedger, Position
from app.utils.config import settings

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")
SOFT_DRAWDOWN = Decimal("-0.02")
HARD_DRAWDOWN = Decimal("-0.03")
DAILY_SPEND_CAP = Decimal("100")
PER_MARKET_SPEND_CAP = Decimal("40")
MAX_OPEN_POSITIONS = 8
SOFT_MAX_POSITIONS = 5
BREACH_HYSTERESIS_SECONDS = 60


@dataclass
class GateResult:
    allow_new_open: bool
    size_multiplier: float
    effective_limits: Dict[str, Decimal | int]
    reason_code: str
    kill_state: KillState


def _local_day(now: datetime) -> str:
    return now.astimezone(PACIFIC_TZ).strftime("%Y-%m-%d")


def _get_day_state(db: Session, user_id, now: datetime) -> DayState:
    date_key = _local_day(now)
    day_state = (
        db.query(DayState)
        .filter(DayState.user_id == user_id, DayState.date_local == date_key)
        .first()
    )
    if not day_state:
        day_state = DayState(
            user_id=user_id,
            date_local=date_key,
            start_equity=Decimal("10000"),
            realized_pnl_today=Decimal("0"),
            daily_spend=Decimal("0"),
            kill_state=KillState.NONE.value,
            kill_reason=None,
            updated_at=now,
        )
        db.add(day_state)
        db.commit()
        db.refresh(day_state)
    return day_state


def _aggregate_realized(db: Session, user_id, now: datetime) -> Decimal:
    date_key = _local_day(now)
    start_of_day = datetime.strptime(date_key, "%Y-%m-%d").replace(tzinfo=PACIFIC_TZ)
    result = (
        db.query(func.coalesce(func.sum(PNLLedger.realized_pnl), 0))
        .filter(PNLLedger.user_id == user_id, PNLLedger.closed_at >= start_of_day)
        .scalar()
    )
    return Decimal(result)


def _aggregate_spend(db: Session, user_id, now: datetime, market_ticker: Optional[str]) -> Decimal:
    date_key = _local_day(now)
    start_of_day = datetime.strptime(date_key, "%Y-%m-%d").replace(tzinfo=PACIFIC_TZ)
    query = db.query(
        func.coalesce(func.sum(PNLLedger.entry_price * PNLLedger.qty), 0)
    ).filter(PNLLedger.user_id == user_id, PNLLedger.opened_at >= start_of_day)
    if market_ticker:
        query = query.filter(PNLLedger.market_ticker == market_ticker)
    return Decimal(query.scalar())


def _count_open_positions(db: Session, user_id) -> int:
    # Existing schema does not explicitly store user on positions, so we fallback to counting all
    # open positions. In a fuller implementation we would join trades owned by the user.
    return db.query(Position).count()


def _update_hysteresis(day_state: DayState, breach_level: KillState, now: datetime):
    if breach_level == KillState.NONE:
        return day_state.kill_state
    marker = f"{breach_level.value}_breach"
    existing = day_state.kill_reason or ""
    ts_map: Dict[str, datetime] = {}
    for token in existing.split("|"):
        if not token:
            continue
        label, _, ts = token.partition(":")
        try:
            ts_map[label] = datetime.fromisoformat(ts)
        except ValueError:
            continue
    last = ts_map.get(marker)
    ts_map[marker] = now
    day_state.kill_reason = "|".join(f"{k}:{v.isoformat()}" for k, v in ts_map.items())
    if last and (now - last) >= timedelta(seconds=BREACH_HYSTERESIS_SECONDS):
        day_state.kill_state = breach_level.value
    return day_state.kill_state


def risk_gate(
    db: Session,
    user_id,
    market_ticker: str,
    intended_action: str,
    intended_spend: Decimal,
    now: Optional[datetime] = None,
) -> GateResult:
    now = now or datetime.utcnow()
    day_state = _get_day_state(db, user_id, now)

    if settings.TRADING_MODE != "live":
        return GateResult(
            allow_new_open=False,
            size_multiplier=0,
            effective_limits={},
            reason_code=DecisionReason.TRADING_DISABLED.value,
            kill_state=KillState.NONE,
        )

    realized_today = _aggregate_realized(db, user_id, now)
    day_state.realized_pnl_today = realized_today
    db.commit()

    drawdown_pct = (min(realized_today, Decimal("0")) / Decimal(day_state.start_equity)).quantize(Decimal("0.0001"))
    breach_state = KillState.NONE
    if drawdown_pct <= HARD_DRAWDOWN:
        breach_state = KillState.HARD
    elif drawdown_pct <= SOFT_DRAWDOWN:
        breach_state = KillState.SOFT
    kill_state_value = _update_hysteresis(day_state, breach_state, now)
    db.commit()

    kill_state = KillState(kill_state_value)

    daily_spend = day_state.daily_spend or Decimal("0")
    per_market_spend = _aggregate_spend(db, user_id, now, market_ticker)

    allow_new_open = True
    size_multiplier = 1.0
    reason = DecisionReason.ALLOWED
    max_positions_allowed = SOFT_MAX_POSITIONS if kill_state == KillState.SOFT else MAX_OPEN_POSITIONS

    if intended_action == "open":
        if daily_spend + intended_spend > DAILY_SPEND_CAP:
            allow_new_open = False
            reason = DecisionReason.DAILY_CAP_REACHED
        elif per_market_spend + intended_spend > PER_MARKET_SPEND_CAP:
            allow_new_open = False
            reason = DecisionReason.PER_MARKET_CAP_REACHED

        open_positions = _count_open_positions(db, user_id)
        if open_positions >= max_positions_allowed:
            allow_new_open = False
            reason = DecisionReason.TOO_MANY_POSITIONS

        if kill_state == KillState.HARD:
            allow_new_open = False
            reason = DecisionReason.KILL_HARD
        elif kill_state == KillState.SOFT and allow_new_open:
            size_multiplier = 0.5
            reason = DecisionReason.SOFT_THROTTLE

    day_state.updated_at = now
    db.commit()

    effective_limits = {
        "daily_remaining": DAILY_SPEND_CAP - daily_spend,
        "per_market_remaining": PER_MARKET_SPEND_CAP - per_market_spend,
        "max_positions": max_positions_allowed if intended_action == "open" else max_positions_allowed,
    }

    return GateResult(
        allow_new_open=allow_new_open,
        size_multiplier=float(size_multiplier),
        effective_limits=effective_limits,
        reason_code=reason.value if isinstance(reason, DecisionReason) else reason,
        kill_state=kill_state,
    )
