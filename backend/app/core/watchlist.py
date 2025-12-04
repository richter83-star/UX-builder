from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.enums import AccessStatus, DecisionReason
from app.models.schemas import (
    AlertLog,
    BaselineMarket,
    DecisionReceipt,
    MarketAccess,
    MarketRequest,
    UserRules,
    Watchlist,
    WatchlistOverride,
)

DEFAULT_WATCHLIST_CAP = 25
DEFAULT_ALERTS_CAP = 10


def compute_expiry(close_time: Optional[datetime]) -> datetime:
    base = close_time or datetime.utcnow()
    return base + timedelta(hours=24)


def ensure_access(db: Session, user_id, market_ticker: str) -> bool:
    record = (
        db.query(MarketAccess)
        .filter(
            MarketAccess.user_id == user_id,
            MarketAccess.market_ticker == market_ticker,
            MarketAccess.status == AccessStatus.ACTIVE.value,
        )
        .first()
    )
    return record is not None


def merge_effective_rules(user_rules: UserRules, override: Optional[WatchlistOverride]) -> Dict:
    override = override or WatchlistOverride(
        user_id=user_rules.user_id,
        market_ticker="",
    )
    return {
        "alerts_enabled": override.alerts_enabled
        if override.alerts_enabled is not None
        else user_rules.alerts_enabled_default,
        "edge_threshold": float(override.edge_threshold)
        if override.edge_threshold is not None
        else float(user_rules.edge_threshold_default),
        "min_liquidity": float(override.min_liquidity)
        if override.min_liquidity is not None
        else (float(user_rules.min_liquidity) if user_rules.min_liquidity is not None else None),
        "max_spread": float(override.max_spread)
        if override.max_spread is not None
        else (float(user_rules.max_spread) if user_rules.max_spread is not None else None),
        "channels": override.channels_json if override.channels_json is not None else user_rules.channels_json,
    }


def add_to_watchlist(
    db: Session,
    user_id,
    market_ticker: str,
    close_time: Optional[datetime] = None,
    alerts_enabled: bool = True,
):
    if not ensure_access(db, user_id, market_ticker):
        raise PermissionError("Market access inactive")

    current_count = db.query(Watchlist).filter(Watchlist.user_id == user_id, Watchlist.is_tracking == True).count()
    if current_count >= DEFAULT_WATCHLIST_CAP:
        raise ValueError("Watchlist cap reached")

    expiry = compute_expiry(close_time)
    entry = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.market_ticker == market_ticker)
        .first()
    )
    if entry:
        entry.is_tracking = True
        entry.tracked_at = datetime.utcnow()
        entry.expires_at = expiry
        entry.alerts_enabled = alerts_enabled
    else:
        entry = Watchlist(
            user_id=user_id,
            market_ticker=market_ticker,
            tracked_at=datetime.utcnow(),
            expires_at=expiry,
            alerts_enabled=alerts_enabled,
        )
        db.add(entry)
    db.commit()
    return entry


def remove_from_watchlist(db: Session, user_id, market_ticker: str):
    entry = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.market_ticker == market_ticker)
        .first()
    )
    if entry:
        db.delete(entry)
        db.commit()


def cleanup_expired(db: Session, now: Optional[datetime] = None) -> int:
    now = now or datetime.utcnow()
    expired = (
        db.query(Watchlist)
        .filter(Watchlist.expires_at <= now)
        .all()
    )
    count = len(expired)
    for row in expired:
        db.delete(row)
    if expired:
        db.commit()
    return count


def latest_decision(db: Session, user_id, market_ticker: str) -> Optional[DecisionReceipt]:
    return (
        db.query(DecisionReceipt)
        .filter(
            DecisionReceipt.user_id == user_id,
            DecisionReceipt.market_ticker == market_ticker,
        )
        .order_by(DecisionReceipt.ts.desc())
        .first()
    )


def watchlist_payload(db: Session, user_id) -> List[Dict]:
    rules = db.query(UserRules).filter(UserRules.user_id == user_id).first()
    if not rules:
        rules = UserRules(user_id=user_id)
        db.add(rules)
        db.commit()
        db.refresh(rules)

    entries = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.is_tracking == True)
        .filter(Watchlist.expires_at > datetime.utcnow())
        .all()
    )
    payload: List[Dict] = []
    for entry in entries:
        override = (
            db.query(WatchlistOverride)
            .filter(
                WatchlistOverride.user_id == user_id,
                WatchlistOverride.market_ticker == entry.market_ticker,
            )
            .first()
        )
        effective = merge_effective_rules(rules, override)
        decision = latest_decision(db, user_id, entry.market_ticker)
        payload.append(
            {
                "market_ticker": entry.market_ticker,
                "tracked_at": entry.tracked_at,
                "expires_at": entry.expires_at,
                "alerts_enabled": entry.alerts_enabled,
                "override": override,
                "effective_rules": effective,
                "decision_trace": decision.reason_code if decision else DecisionReason.HEARTBEAT_ONLY.value,
            }
        )
    return payload
