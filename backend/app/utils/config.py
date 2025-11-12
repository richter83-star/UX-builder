from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Application configuration settings"""

    # Kalshi API Configuration
    KALSHI_API_KEY: str
    KALSHI_PRIVATE_KEY: str
    KALSHI_ENVIRONMENT: str = "sandbox"
    KALSHI_BASE_URL: str = "https://demo-api.kalshi.co/v1" if KALSHI_ENVIRONMENT == "sandbox" else "https://trading-api.kalshi.co/v1"

    # Database Configuration
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # External API Keys
    NEWS_API_KEY: Optional[str] = None
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    TWITTER_ACCESS_TOKEN: Optional[str] = None
    TWITTER_ACCESS_TOKEN_SECRET: Optional[str] = None
    TWITTER_BEARER_TOKEN: Optional[str] = None

    # Reddit API
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "kalshi_agent/1.0"

    # Risk Management
    DEFAULT_RISK_PROFILE: str = "moderate"
    MAX_DAILY_TRADES: int = 10
    ENABLE_AUTO_TRADING: bool = False
    MIN_CONFIDENCE_THRESHOLD: float = 60.0

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 100

    # Analysis Configuration
    MODEL_RETRAIN_INTERVAL: int = 7  # days
    ENSEMBLE_WEIGHT_UPDATE_INTERVAL: int = 1  # day
    MAX_HISTORICAL_DAYS: int = 365

    # Risk Profiles Configuration
    RISK_PROFILES = {
        "conservative": {
            "max_position_size_percent": 2.0,
            "kelly_fraction": 0.1,
            "min_confidence_threshold": 75.0
        },
        "moderate": {
            "max_position_size_percent": 5.0,
            "kelly_fraction": 0.25,
            "min_confidence_threshold": 60.0
        },
        "aggressive": {
            "max_position_size_percent": 10.0,
            "kelly_fraction": 0.5,
            "min_confidence_threshold": 50.0
        }
    }

    DEFAULT_RISK_CONFIG = {
        "max_position_size_percent": 5.0,
        "max_category_exposure_percent": 20.0,
        "daily_loss_limit_percent": 2.0,
        "kelly_fraction": 0.25,
        "stop_loss_percent": 10.0,
        "max_correlation": 0.7,
        "max_daily_trades": 10,
        "min_confidence_threshold": 60.0
    }

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)