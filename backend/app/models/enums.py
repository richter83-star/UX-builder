from enum import Enum
from typing import List

class MarketCategory(str, Enum):
    POLITICS = "politics"
    FINANCE = "finance"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    TECHNOLOGY = "technology"
    WEATHER = "weather"
    OTHER = "other"

class MarketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"
    CANCELLED = "cancelled"

class TradeSide(str, Enum):
    YES = "yes"
    NO = "no"

class TradeStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class AnalyzerType(str, Enum):
    SENTIMENT = "sentiment"
    STATISTICAL = "statistical"
    ML_RANDOM_FOREST = "ml_random_forest"
    ML_GRADIENT_BOOSTING = "ml_gradient_boosting"
    ML_LSTM = "ml_lstm"
    ML_ARIMA = "ml_arima"
    ENSEMBLE = "ensemble"

class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class WebSocketEvent(str, Enum):
    MARKET_UPDATE = "market_update"
    ANALYSIS_UPDATE = "analysis_update"
    OPPORTUNITY_ALERT = "opportunity_alert"
    POSITION_UPDATE = "position_update"
    TRADE_EXECUTED = "trade_executed"
    RISK_ALERT = "risk_alert"
    CONNECTION_STATUS = "connection_status"

# Constants
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
MIN_CONFIDENCE_THRESHOLD = 50.0
MAX_CONFIDENCE_THRESHOLD = 100.0
MIN_TRADE_SIZE = 1
MAX_TRADE_SIZE = 10000

# Market categories for analysis
POLITICS_KEYWORDS = ["election", "president", "congress", "senate", "vote", "politics", "government"]
FINANCE_KEYWORDS = ["stock", "market", "economy", "fed", "inflation", "gdp", "finance", "trading"]
SPORTS_KEYWORDS = ["game", "team", "player", "sport", "match", "championship", "league"]
ENTERTAINMENT_KEYWORDS = ["movie", "music", "award", "celebrity", "entertainment", "show", "film"]
TECHNOLOGY_KEYWORDS = ["tech", "software", "ai", "startup", "apple", "google", "microsoft", "technology"]
WEATHER_KEYWORDS = ["weather", "temperature", "rain", "snow", "storm", "hurricane", "climate"]

# Risk management constants
MAX_POSITION_SIZE_PERCENT = 10.0
MAX_CATEGORY_EXPOSURE_PERCENT = 30.0
DAILY_LOSS_LIMIT_PERCENT = 5.0
DEFAULT_KELLY_FRACTION = 0.25
STOP_LOSS_PERCENT = 15.0
MAX_CORRELATION = 0.8
MAX_DAILY_TRADES = 20

# Analysis time windows
SHORT_TERM_WINDOW = 7  # days
MEDIUM_TERM_WINDOW = 30  # days
LONG_TERM_WINDOW = 90  # days

# Sentiment analysis thresholds
SENTIMENT_BULLISH_THRESHOLD = 0.1
SENTIMENT_BEARISH_THRESHOLD = -0.1
SENTIMENT_NEUTRAL_MIN = -0.1
SENTIMENT_NEUTRAL_MAX = 0.1

# Model performance thresholds
MIN_MODEL_ACCURACY = 0.55
MIN_ENSEMBLE_ACCURACY = 0.65
MIN_PROFIT_FACTOR = 1.2
MAX_SHARPE_RATIO = 3.0

# WebSocket configuration
WS_PING_INTERVAL = 30
WS_PONG_TIMEOUT = 10
WS_MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB
WS_CONNECTION_TIMEOUT = 60

# External API rate limits
TWITTER_RATE_LIMIT = 300  # requests per 15 minutes
REDDIT_RATE_LIMIT = 60  # requests per minute
NEWS_API_RATE_LIMIT = 1000  # requests per day
KALSHI_RATE_LIMIT = 100  # requests per minute