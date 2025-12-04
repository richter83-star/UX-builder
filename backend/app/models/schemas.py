from sqlalchemy import (
    Column,
    String,
    DateTime,
    Integer,
    BigInteger,
    Text,
    Boolean,
    JSON,
    Index,
    ForeignKey,
    Numeric,
    Date,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .database import Base
from .enums import AccessSource, AccessStatus, MarketRequestStatus, KillState

# SQLAlchemy Models
class Market(Base):
    __tablename__ = "markets"

    market_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    subtitle = Column(Text)
    settle_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    prices = relationship("MarketPrice", back_populates="market")
    analysis_results = relationship("AnalysisResult", back_populates="market")
    trades = relationship("Trade", back_populates="market")

    __table_args__ = (
        Index('idx_category_created', 'category', 'created_at'),
    )

class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(BigInteger, primary_key=True)
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.market_id"), nullable=False)
    price = Column(Numeric(10, 4), nullable=False)
    volume = Column(BigInteger)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    market = relationship("Market", back_populates="prices")

    __table_args__ = (
        Index('idx_market_time', 'market_id', 'timestamp'),
    )

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(BigInteger, primary_key=True)
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.market_id"), nullable=False)
    analyzer_type = Column(String(50), nullable=False)
    prediction = Column(Numeric(10, 4), nullable=False)
    confidence = Column(Numeric(5, 2), nullable=False)
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    market = relationship("Market", back_populates="analysis_results")

    __table_args__ = (
        Index('idx_market_analyzer', 'market_id', 'analyzer_type'),
        Index('idx_analyzer_timestamp', 'analyzer_type', 'timestamp'),
    )

class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.market_id"), nullable=False)
    side = Column(String(10), nullable=False)  # 'yes' or 'no'
    count = Column(Integer, nullable=False)
    price = Column(Numeric(10, 4), nullable=False)
    status = Column(String(20), default='pending')  # 'pending', 'filled', 'cancelled'
    filled_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    market = relationship("Market", back_populates="trades")
    position = relationship("Position", back_populates="trade", uselist=False)

    __table_args__ = (
        Index('idx_market_status', 'market_id', 'status'),
        Index('idx_created_status', 'created_at', 'status'),
    )

class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.id"), nullable=False)
    current_value = Column(Numeric(10, 4))
    unrealized_pnl = Column(Numeric(10, 4))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trade = relationship("Trade", back_populates="position")

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    kalshi_api_key = Column(String(255))
    kalshi_private_key = Column(Text)
    risk_profile = Column(String(20), default='moderate')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(BigInteger, primary_key=True)
    level = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index('idx_level_timestamp', 'level', 'timestamp'),
    )


class BaselineMarket(Base):
    __tablename__ = "baseline_markets"

    market_ticker = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=1)
    seeded_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    seed_version = Column(String, default="v1")


class MarketAccess(Base):
    __tablename__ = "market_access"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    market_ticker = Column(String, primary_key=True)
    source = Column(String, default=AccessSource.BASELINE.value)
    status = Column(String, default=AccessStatus.ACTIVE.value)
    requested_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    approved_at = Column(DateTime(timezone=True))


class Watchlist(Base):
    __tablename__ = "watchlists"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    market_ticker = Column(String, primary_key=True)
    is_tracking = Column(Boolean, default=True)
    tracked_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    alerts_enabled = Column(Boolean, default=True)


class UserRules(Base):
    __tablename__ = "user_rules"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    alerts_enabled_default = Column(Boolean, default=True)
    edge_threshold_default = Column(Numeric(10, 4), default=0.03)
    max_alerts_per_day = Column(Integer, default=10)
    digest_mode = Column(String, default="daily")
    digest_time = Column(Time, nullable=True)
    channels_json = Column(JSON, default=lambda: {"email": True})
    min_liquidity = Column(Numeric(10, 4))
    max_spread = Column(Numeric(10, 4))


class WatchlistOverride(Base):
    __tablename__ = "watchlist_overrides"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    market_ticker = Column(String, primary_key=True)
    alerts_enabled = Column(Boolean, nullable=True)
    edge_threshold = Column(Numeric(10, 4), nullable=True)
    min_liquidity = Column(Numeric(10, 4), nullable=True)
    max_spread = Column(Numeric(10, 4), nullable=True)
    channels_json = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketRequest(Base):
    __tablename__ = "market_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    market_ticker = Column(String, nullable=True)
    query_text = Column(Text, nullable=True)
    reason_text = Column(Text, nullable=True)
    status = Column(String, default=MarketRequestStatus.PENDING.value)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    reviewed_at = Column(DateTime(timezone=True))
    reviewer_id = Column(UUID(as_uuid=True))
    notes = Column(Text)


class AlertLog(Base):
    __tablename__ = "alerts_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    market_ticker = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    delivered_at = Column(DateTime(timezone=True))
    status = Column(String, default="queued")
    reason_code = Column(String)
    payload_json = Column(JSON)


class DayState(Base):
    __tablename__ = "day_state"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    date_local = Column(String, primary_key=True)
    start_equity = Column(Numeric(12, 2), nullable=False)
    realized_pnl_today = Column(Numeric(12, 2), default=0)
    daily_spend = Column(Numeric(12, 2), default=0)
    kill_state = Column(String, default=KillState.NONE.value)
    kill_reason = Column(String)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class PNLLedger(Base):
    __tablename__ = "pnl_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    market_ticker = Column(String, nullable=False)
    opened_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    qty = Column(Integer)
    entry_price = Column(Numeric(10, 4))
    exit_price = Column(Numeric(10, 4))
    fees = Column(Numeric(10, 4), default=0)
    realized_pnl = Column(Numeric(12, 2))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class DecisionReceipt(Base):
    __tablename__ = "decision_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    market_ticker = Column(String, nullable=False)
    ts = Column(DateTime(timezone=True), default=datetime.utcnow)
    p_market = Column(Numeric(10, 4))
    p_model = Column(Numeric(10, 4))
    edge = Column(Numeric(10, 4))
    intended_action = Column(String)
    allowed = Column(Boolean, default=False)
    reason_code = Column(String)
    kill_state = Column(String, default=KillState.NONE.value)
    spend_snapshot = Column(JSON)
    model_version = Column(String)