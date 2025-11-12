from sqlalchemy import Column, String, DateTime, Integer, Decimal, BigInteger, Text, Boolean, JSON, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .database import Base

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
    price = Column(Decimal(10, 4), nullable=False)
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
    prediction = Column(Decimal(10, 4), nullable=False)
    confidence = Column(Decimal(5, 2), nullable=False)
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
    price = Column(Decimal(10, 4), nullable=False)
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
    current_value = Column(Decimal(10, 4))
    unrealized_pnl = Column(Decimal(10, 4))
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