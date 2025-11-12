import kalshi
import requests
import json
import time
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import base64
import websockets
from loguru import logger

from app.utils.config import settings
from app.models.enums import MarketCategory, MarketStatus, TradeSide, TradeStatus

class KalshiClient:
    """
    Kalshi API client with RSA-PSS authentication and comprehensive error handling.
    Handles all communication with Kalshi API for market data, trading, and WebSocket connections.
    """

    def __init__(self):
        self.api_key = settings.KALSHI_API_KEY
        self.private_key = settings.KALSHI_PRIVATE_KEY
        self.environment = settings.KALSHI_ENVIRONMENT
        self.base_url = settings.KALSHI_BASE_URL

        # Initialize official Kalshi Python SDK
        self.kalshi_api = None
        self.session = requests.Session()
        self.websocket_url = self.base_url.replace('https://', 'wss://').replace('/v1', '/stream') if self.environment == 'production' else 'wss://demo-api.kalshi.co/stream'

        # Rate limiting
        self.rate_limit_remaining = 100
        self.rate_limit_reset = time.time()
        self.last_request_time = 0
        self.min_request_interval = 0.6  # 100 requests per minute max

        # Circuit breaker for API failures
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        self.circuit_breaker_last_failure = 0

        # Initialize connection
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize Kalshi API connection"""
        try:
            # Use official SDK with proper authentication
            config = kalshi.Configuration(
                host=self.base_url,
                api_key=self.api_key,
                private_key=self.private_key
            )

            self.kalshi_api = kalshi.ApiClient(config)
            logger.info(f"Successfully initialized Kalshi API connection to {self.environment}")

        except Exception as e:
            logger.error(f"Failed to initialize Kalshi API connection: {str(e)}")
            raise

    def _check_circuit_breaker(self):
        """Check if circuit breaker is open"""
        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            if time.time() - self.circuit_breaker_last_failure < self.circuit_breaker_timeout:
                raise Exception("Circuit breaker is open - API temporarily unavailable")
            else:
                # Reset circuit breaker after timeout
                self.circuit_breaker_failures = 0
                logger.info("Circuit breaker reset after timeout")

    def _update_circuit_breaker(self, success: bool):
        """Update circuit breaker state based on request success"""
        if success:
            self.circuit_breaker_failures = 0
        else:
            self.circuit_breaker_failures += 1
            self.circuit_breaker_last_failure = time.time()

    def _rate_limit_check(self):
        """Implement rate limiting with exponential backoff"""
        current_time = time.time()

        # Respect minimum request interval
        if current_time - self.last_request_time < self.min_request_interval:
            sleep_time = self.min_request_interval - (current_time - self.last_request_time)
            time.sleep(sleep_time)

        # Check rate limit headers
        if self.rate_limit_remaining <= 1 and current_time < self.rate_limit_reset:
            sleep_time = self.rate_limit_reset - current_time
            logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request_with_retry(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make HTTP request with retry logic and comprehensive error handling"""
        self._check_circuit_breaker()
        self._rate_limit_check()

        max_retries = 3
        base_delay = 1

        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}{endpoint}"

                if method.upper() == 'GET':
                    response = self.session.get(url, timeout=30, **kwargs)
                elif method.upper() == 'POST':
                    response = self.session.post(url, timeout=30, **kwargs)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, timeout=30, **kwargs)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, timeout=30, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Update rate limit information
                if 'X-RateLimit-Remaining' in response.headers:
                    self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                if 'X-RateLimit-Reset' in response.headers:
                    self.rate_limit_reset = float(response.headers['X-RateLimit-Reset'])

                if response.status_code == 200:
                    self._update_circuit_breaker(True)
                    return response.json()
                elif response.status_code == 429:
                    # Rate limit exceeded - implement exponential backoff
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Server error {response.status_code}, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    # Client error - don't retry
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    logger.error(f"API request failed with status {response.status_code}: {error_data}")
                    self._update_circuit_breaker(False)
                    raise Exception(f"API request failed: {response.status_code} - {error_data}")

            except requests.exceptions.Timeout:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Request timeout, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            except requests.exceptions.ConnectionError:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Connection error, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Unexpected error in API request: {str(e)}")
                self._update_circuit_breaker(False)
                raise

        # All retries failed
        self._update_circuit_breaker(False)
        raise Exception(f"API request failed after {max_retries} attempts")

    def get_markets(self, category: Optional[str] = None, status: Optional[str] = None,
                   limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch available markets from Kalshi

        Args:
            category: Filter by market category
            status: Filter by market status
            limit: Maximum number of markets to return
            offset: Offset for pagination

        Returns:
            List of market objects
        """
        try:
            params = {
                "limit": limit,
                "offset": offset
            }

            if category:
                params["category"] = category
            if status:
                params["status"] = status

            # Use official SDK if available, otherwise fallback to REST API
            if self.kalshi_api:
                markets_api = kalshi.MarketsApi(self.kalshi_api)
                result = markets_api.get_markets(**params)
                return result.get('markets', [])
            else:
                return self._make_request_with_retry('GET', '/markets', params=params).get('markets', [])

        except Exception as e:
            logger.error(f"Failed to fetch markets: {str(e)}")
            raise

    def get_market_details(self, market_id: str) -> Dict:
        """
        Get detailed information for a specific market

        Args:
            market_id: The unique identifier for the market

        Returns:
            Market details object
        """
        try:
            if self.kalshi_api:
                markets_api = kalshi.MarketsApi(self.kalshi_api)
                return markets_api.get_market(market_id)
            else:
                return self._make_request_with_retry('GET', f'/markets/{market_id}')

        except Exception as e:
            logger.error(f"Failed to get market details for {market_id}: {str(e)}")
            raise

    def get_market_price(self, market_id: str) -> Dict:
        """
        Get current market price and order book

        Args:
            market_id: The unique identifier for the market

        Returns:
            Market price and order book data
        """
        try:
            if self.kalshi_api:
                markets_api = kalshi.MarketsApi(self.kalshi_api)
                return markets_api.get_market_orderbook(market_id)
            else:
                return self._make_request_with_retry('GET', f'/markets/{market_id}/orderbook')

        except Exception as e:
            logger.error(f"Failed to get market price for {market_id}: {str(e)}")
            raise

    def get_market_history(self, market_id: str, start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Get historical price data for a market

        Args:
            market_id: The unique identifier for the market
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of historical price data points
        """
        try:
            params = {}
            if start_date:
                params["start_ts"] = int(start_date.timestamp())
            if end_date:
                params["end_ts"] = int(end_date.timestamp())

            if self.kalshi_api:
                markets_api = kalshi.MarketsApi(self.kalshi_api)
                result = markets_api.get_market_history(market_id, **params)
                return result.get('history', [])
            else:
                return self._make_request_with_retry('GET', f'/markets/{market_id}/history', params=params).get('history', [])

        except Exception as e:
            logger.error(f"Failed to get market history for {market_id}: {str(e)}")
            raise

    def place_order(self, market_id: str, side: str, count: int, price: Optional[float] = None,
                   expiration: Optional[str] = None) -> Dict:
        """
        Place a new order on Kalshi

        Args:
            market_id: The unique identifier for the market
            side: 'yes' or 'no'
            count: Number of contracts to trade
            price: Price per contract (if None, uses market price)
            expiration: Order expiration time

        Returns:
            Order confirmation object
        """
        try:
            order_data = {
                "market_id": market_id,
                "side": side,
                "count": count
            }

            if price:
                order_data["price"] = price
            if expiration:
                order_data["expiration"] = expiration

            if self.kalshi_api:
                portfolio_api = kalshi.PortfolioApi(self.kalshi_api)
                return portfolio_api.create_order(order_data)
            else:
                return self._make_request_with_retry('POST', '/portfolio/orders', json=order_data)

        except Exception as e:
            logger.error(f"Failed to place order for {market_id}: {str(e)}")
            raise

    def get_positions(self) -> List[Dict]:
        """
        Retrieve current open positions

        Returns:
            List of position objects
        """
        try:
            if self.kalshi_api:
                portfolio_api = kalshi.PortfolioApi(self.kalshi_api)
                return portfolio_api.get_positions().get('positions', [])
            else:
                return self._make_request_with_retry('GET', '/portfolio/positions').get('positions', [])

        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            raise

    def get_balance(self) -> Dict:
        """
        Get account balance information

        Returns:
            Account balance object
        """
        try:
            if self.kalshi_api:
                portfolio_api = kalshi.PortfolioApi(self.kalshi_api)
                return portfolio_api.get_balance()
            else:
                return self._make_request_with_retry('GET', '/portfolio/balance')

        except Exception as e:
            logger.error(f"Failed to get account balance: {str(e)}")
            raise

    def get_order_history(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get trading history

        Args:
            limit: Maximum number of orders to return
            offset: Offset for pagination

        Returns:
            List of order objects
        """
        try:
            params = {"limit": limit, "offset": offset}

            if self.kalshi_api:
                portfolio_api = kalshi.PortfolioApi(self.kalshi_api)
                return portfolio_api.get_order_history(**params).get('orders', [])
            else:
                return self._make_request_with_retry('GET', '/portfolio/orders', params=params).get('orders', [])

        except Exception as e:
            logger.error(f"Failed to get order history: {str(e)}")
            raise

    async def subscribe_market_updates(self, market_ids: List[str], callback):
        """
        Subscribe to real-time market updates via WebSocket

        Args:
            market_ids: List of market IDs to subscribe to
            callback: Callback function for market updates
        """
        try:
            subscription_msg = {
                "id": str(int(time.time())),
                "action": "subscribe",
                "market_ids": market_ids
            }

            async with websockets.connect(
                self.websocket_url,
                ping_interval=self.__class__.WS_PING_INTERVAL,
                ping_timeout=self.__class__.WS_PONG_TIMEOUT,
                max_size=self.__class__.WS_MAX_MESSAGE_SIZE
            ) as websocket:

                # Send subscription message
                await websocket.send(json.dumps(subscription_msg))
                logger.info(f"Subscribed to market updates for {len(market_ids)} markets")

                # Listen for messages
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await callback(data)
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to subscribe to market updates: {str(e)}")
            raise

    def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel an existing order

        Args:
            order_id: The unique identifier for the order

        Returns:
            Cancellation confirmation object
        """
        try:
            if self.kalshi_api:
                portfolio_api = kalshi.PortfolioApi(self.kalshi_api)
                return portfolio_api.cancel_order(order_id)
            else:
                return self._make_request_with_retry('DELETE', f'/portfolio/orders/{order_id}')

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {str(e)}")
            raise

    def get_market_series(self, category: Optional[str] = None) -> List[Dict]:
        """
        Get available market series (categories)

        Args:
            category: Filter by specific category

        Returns:
            List of market series objects
        """
        try:
            params = {}
            if category:
                params["category"] = category

            return self._make_request_with_retry('GET', '/series', params=params).get('series', [])

        except Exception as e:
            logger.error(f"Failed to get market series: {str(e)}")
            raise

# Global Kalshi client instance
kalshi_client = KalshiClient()