import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from loguru import logger

from app.core.kalshi_client import kalshi_client
from app.core.risk_manager import risk_manager
from app.models.database import SessionLocal
from app.models.schemas import Position, Trade, Market, MarketPrice
from app.models.enums import TradeSide, TradeStatus, MarketStatus

class PortfolioStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

@dataclass
class PositionSummary:
    position_id: str
    market_id: str
    market_title: str
    side: str
    count: int
    entry_price: float
    current_price: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    duration_hours: float
    risk_level: str

@dataclass
class PortfolioMetrics:
    total_value: float
    cash_balance: float
    positions_value: float
    total_pnl: float
    total_pnl_percent: float
    daily_pnl: float
    daily_pnl_percent: float
    number_of_positions: int
    number_of_winning_positions: int
    number_of_losing_positions: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    average_position_size: float

@dataclass
class TradeExecution:
    trade_id: str
    market_id: str
    side: str
    count: int
    price: float
    executed_at: datetime
    status: str
    fees: float

class PortfolioManager:
    """
    Portfolio management system that tracks positions, calculates performance metrics,
    and provides comprehensive portfolio analysis and reporting.
    """

    def __init__(self):
        self.portfolio_status = PortfolioStatus.ACTIVE
        self.positions_cache = {}
        self.last_update = datetime.utcnow()
        self.historical_values = []
        self.daily_returns = []

        # Performance tracking
        self.trades_today = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        # Portfolio metrics cache
        self._metrics_cache = None
        self._metrics_cache_time = None
        self._cache_ttl_seconds = 60  # Cache metrics for 1 minute

    async def update_positions(self) -> Dict[str, PositionSummary]:
        """Update all current positions with latest market data"""
        try:
            logger.info("Updating portfolio positions")

            db = SessionLocal()
            try:
                # Get all positions from database
                positions = db.query(Position).all()
                updated_positions = {}

                for position in positions:
                    try:
                        # Get current market price
                        current_price_info = kalshi_client.get_market_price(position.trade.market_id)
                        current_price = float(current_price_info.get('price', position.trade.price))

                        # Calculate current values
                        entry_price = float(position.trade.price)
                        count = position.trade.count
                        side = position.trade.side

                        if side == 'yes':
                            current_value = count * current_price
                            entry_value = count * entry_price
                        else:  # 'no'
                            current_value = count * (1 - current_price)
                            entry_value = count * (1 - entry_price)

                        unrealized_pnl = current_value - entry_value
                        unrealized_pnl_percent = (unrealized_pnl / entry_value) * 100 if entry_value > 0 else 0

                        # Calculate duration
                        duration = datetime.utcnow() - position.trade.created_at
                        duration_hours = duration.total_seconds() / 3600

                        # Get market title
                        market = db.query(Market).filter(Market.market_id == position.trade.market_id).first()
                        market_title = market.title if market else "Unknown Market"

                        # Determine risk level
                        risk_level = self._calculate_position_risk_level(unrealized_pnl_percent, duration_hours)

                        # Create position summary
                        position_summary = PositionSummary(
                            position_id=str(position.id),
                            market_id=position.trade.market_id,
                            market_title=market_title,
                            side=side,
                            count=count,
                            entry_price=entry_price,
                            current_price=current_price,
                            current_value=current_value,
                            unrealized_pnl=unrealized_pnl,
                            unrealized_pnl_percent=unrealized_pnl_percent,
                            duration_hours=duration_hours,
                            risk_level=risk_level
                        )

                        # Update database
                        position.current_value = current_value
                        position.unrealized_pnl = unrealized_pnl
                        position.updated_at = datetime.utcnow()

                        # Cache position
                        updated_positions[str(position.id)] = position_summary
                        self.positions_cache[str(position.id)] = position_summary

                    except Exception as e:
                        logger.error(f"Error updating position {position.id}: {str(e)}")
                        continue

                # Commit changes to database
                db.commit()

                # Update portfolio metrics
                await self._update_portfolio_metrics(updated_positions)

                self.last_update = datetime.utcnow()
                logger.info(f"Updated {len(updated_positions)} positions")

                return updated_positions

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error updating positions: {str(e)}")
            return {}

    def _calculate_position_risk_level(self, pnl_percent: float, duration_hours: float) -> str:
        """Calculate risk level for a position"""
        try:
            # Risk based on P&L and time held
            if pnl_percent < -20:
                return "critical"
            elif pnl_percent < -10:
                return "high"
            elif pnl_percent < -5:
                return "medium"
            elif duration_hours > 72:  # Positions held > 3 days
                return "medium"
            else:
                return "low"

        except Exception as e:
            logger.error(f"Error calculating position risk level: {str(e)}")
            return "unknown"

    async def _update_portfolio_metrics(self, positions: Dict[str, PositionSummary]):
        """Update portfolio performance metrics"""
        try:
            # Get account balance
            balance_info = kalshi_client.get_balance()
            cash_balance = float(balance_info.get('cash_balance', 0))

            # Calculate position values
            positions_value = sum(pos.current_value for pos in positions.values())
            total_value = cash_balance + positions_value

            # Calculate P&L
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions.values())
            realized_pnl = self._get_daily_realized_pnl()
            total_pnl = total_unrealized_pnl + realized_pnl

            # Calculate percentages
            total_pnl_percent = (total_pnl / (total_value - total_pnl)) * 100 if (total_value - total_pnl) > 0 else 0
            daily_pnl_percent = (realized_pnl / cash_balance) * 100 if cash_balance > 0 else 0

            # Calculate win rate
            winning_positions = sum(1 for pos in positions.values() if pos.unrealized_pnl > 0)
            losing_positions = sum(1 for pos in positions.values() if pos.unrealized_pnl < 0)
            win_rate = (winning_positions / len(positions)) * 100 if positions else 0

            # Calculate average position size
            avg_position_size = positions_value / len(positions) if positions else 0

            # Update historical values
            self.historical_values.append({
                'timestamp': datetime.utcnow(),
                'total_value': total_value,
                'cash_balance': cash_balance,
                'positions_value': positions_value,
                'pnl': total_pnl
            })

            # Keep only last 30 days of historical data
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            self.historical_values = [
                hv for hv in self.historical_values
                if hv['timestamp'] > cutoff_date
            ]

            # Update risk manager with portfolio value
            if hasattr(risk_manager, 'portfolio_value'):
                risk_manager.portfolio_value = total_value

            logger.debug(f"Portfolio metrics updated: ${total_value:.2f} total value")

        except Exception as e:
            logger.error(f"Error updating portfolio metrics: {str(e)}")

    def _get_daily_realized_pnl(self) -> float:
        """Get realized P&L for today"""
        try:
            db = SessionLocal()
            try:
                today = datetime.utcnow().date()
                today_start = datetime.combine(today, datetime.min.time())

                # Get filled trades from today
                trades = db.query(Trade).filter(
                    Trade.status == TradeStatus.FILLED,
                    Trade.filled_at >= today_start
                ).all()

                # This is simplified - in production, would track realized P&L more accurately
                # For now, return 0 as most P&L is unrealized
                return 0.0

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting daily realized P&L: {str(e)}")
            return 0.0

    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get comprehensive portfolio performance metrics"""
        try:
            # Check cache
            if (self._metrics_cache and
                self._metrics_cache_time and
                (datetime.utcnow() - self._metrics_cache_time).total_seconds() < self._cache_ttl_seconds):
                return self._metrics_cache

            # Update positions if stale
            if (datetime.utcnow() - self.last_update).total_seconds() > 300:  # 5 minutes
                await self.update_positions()

            # Get current data
            db = SessionLocal()
            try:
                # Get account balance
                balance_info = kalshi_client.get_balance()
                cash_balance = float(balance_info.get('cash_balance', 0))

                # Get positions
                positions = db.query(Position).all()
                positions_value = sum(float(p.current_value or 0) for p in positions)
                total_value = cash_balance + positions_value

                # Calculate P&L metrics
                total_unrealized_pnl = sum(float(p.unrealized_pnl or 0) for p in positions)
                daily_pnl = self._get_daily_realized_pnl()
                total_pnl = total_unrealized_pnl + daily_pnl

                # Calculate percentages
                invested_capital = total_value - total_pnl
                total_pnl_percent = (total_pnl / invested_capital) * 100 if invested_capital > 0 else 0
                daily_pnl_percent = (daily_pnl / cash_balance) * 100 if cash_balance > 0 else 0

                # Position statistics
                number_of_positions = len(positions)
                winning_positions = sum(1 for p in positions if (p.unrealized_pnl or 0) > 0)
                losing_positions = sum(1 for p in positions if (p.unrealized_pnl or 0) < 0)
                win_rate = (winning_positions / number_of_positions) * 100 if number_of_positions > 0 else 0

                # Risk metrics
                max_drawdown = risk_manager.current_drawdown if hasattr(risk_manager, 'current_drawdown') else 0

                # Sharpe ratio (simplified)
                sharpe_ratio = self._calculate_sharpe_ratio()

                # Average position size
                avg_position_size = positions_value / number_of_positions if number_of_positions > 0 else 0

                # Create metrics object
                metrics = PortfolioMetrics(
                    total_value=total_value,
                    cash_balance=cash_balance,
                    positions_value=positions_value,
                    total_pnl=total_pnl,
                    total_pnl_percent=total_pnl_percent,
                    daily_pnl=daily_pnl,
                    daily_pnl_percent=daily_pnl_percent,
                    number_of_positions=number_of_positions,
                    number_of_winning_positions=winning_positions,
                    number_of_losing_positions=losing_positions,
                    win_rate=win_rate,
                    max_drawdown=max_drawdown,
                    sharpe_ratio=sharpe_ratio,
                    average_position_size=avg_position_size
                )

                # Cache results
                self._metrics_cache = metrics
                self._metrics_cache_time = datetime.utcnow()

                return metrics

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting portfolio metrics: {str(e)}")
            return PortfolioMetrics(
                total_value=0, cash_balance=0, positions_value=0, total_pnl=0,
                total_pnl_percent=0, daily_pnl=0, daily_pnl_percent=0,
                number_of_positions=0, number_of_winning_positions=0,
                number_of_losing_positions=0, win_rate=0, max_drawdown=0,
                sharpe_ratio=0, average_position_size=0
            )

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio from historical returns"""
        try:
            if len(self.historical_values) < 30:  # Need at least 30 data points
                return 0.0

            # Calculate daily returns
            returns = []
            for i in range(1, len(self.historical_values)):
                prev_value = self.historical_values[i-1]['total_value']
                curr_value = self.historical_values[i]['total_value']
                if prev_value > 0:
                    daily_return = (curr_value - prev_value) / prev_value
                    returns.append(daily_return)

            if len(returns) < 10:
                return 0.0

            # Calculate Sharpe ratio
            returns_array = np.array(returns)
            excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate

            if np.std(excess_returns) > 0:
                sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0.0

            return sharpe_ratio

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0.0

    async def get_position_summaries(self) -> List[PositionSummary]:
        """Get summaries of all current positions"""
        try:
            # Update positions if stale
            if (datetime.utcnow() - self.last_update).total_seconds() > 300:  # 5 minutes
                await self.update_positions()

            return list(self.positions_cache.values())

        except Exception as e:
            logger.error(f"Error getting position summaries: {str(e)}")
            return []

    async def close_position(self, position_id: str, reason: str = "manual") -> Optional[Dict[str, Any]]:
        """Close a specific position"""
        try:
            logger.info(f"Closing position {position_id}: {reason}")

            db = SessionLocal()
            try:
                # Get position
                position = db.query(Position).filter(Position.id == position_id).first()
                if not position:
                    logger.error(f"Position {position_id} not found")
                    return None

                # Determine closing order
                market_id = position.trade.market_id
                original_side = position.trade.side
                close_side = 'no' if original_side == 'yes' else 'yes'
                close_count = position.trade.count

                # Get current market price
                price_info = kalshi_client.get_market_price(market_id)
                close_price = float(price_info.get('price', 0.5))

                # Place closing order
                try:
                    order_result = kalshi_client.place_order(
                        market_id=market_id,
                        side=close_side,
                        count=close_count,
                        price=close_price
                    )

                    # Update position status
                    # In a real implementation, you'd track the closing order
                    # For now, we'll simulate the position being closed

                    logger.info(f"Position {position_id} closed successfully")
                    return {
                        'position_id': position_id,
                        'closing_order': order_result,
                        'close_price': close_price,
                        'close_side': close_side,
                        'reason': reason
                    }

                except Exception as e:
                    logger.error(f"Failed to place closing order for position {position_id}: {str(e)}")
                    return None

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error closing position {position_id}: {str(e)}")
            return None

    async def get_portfolio_performance(self, days: int = 30) -> Dict[str, Any]:
        """Get portfolio performance over specified period"""
        try:
            # Filter historical values for the specified period
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            filtered_values = [
                hv for hv in self.historical_values
                if hv['timestamp'] > cutoff_date
            ]

            if not filtered_values:
                return {
                    'period_start': cutoff_date,
                    'period_end': datetime.utcnow(),
                    'starting_value': 0,
                    'ending_value': 0,
                    'total_return': 0,
                    'total_return_percent': 0,
                    'max_value': 0,
                    'min_value': 0,
                    'volatility': 0,
                    'data_points': 0
                }

            # Calculate performance metrics
            starting_value = filtered_values[0]['total_value']
            ending_value = filtered_values[-1]['total_value']
            total_return = ending_value - starting_value
            total_return_percent = (total_return / starting_value) * 100 if starting_value > 0 else 0

            max_value = max(hv['total_value'] for hv in filtered_values)
            min_value = min(hv['total_value'] for hv in filtered_values)

            # Calculate volatility
            values = [hv['total_value'] for hv in filtered_values]
            if len(values) > 1:
                returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
                volatility = np.std(returns) * np.sqrt(252) if returns else 0  # Annualized volatility
            else:
                volatility = 0

            return {
                'period_start': cutoff_date,
                'period_end': datetime.utcnow(),
                'starting_value': starting_value,
                'ending_value': ending_value,
                'total_return': total_return,
                'total_return_percent': total_return_percent,
                'max_value': max_value,
                'min_value': min_value,
                'volatility': volatility,
                'data_points': len(filtered_values),
                'daily_values': [
                    {
                        'date': hv['timestamp'].isoformat(),
                        'value': hv['total_value'],
                        'pnl': hv['pnl']
                    }
                    for hv in filtered_values
                ]
            }

        except Exception as e:
            logger.error(f"Error getting portfolio performance: {str(e)}")
            return {}

    def get_portfolio_allocation(self) -> Dict[str, Any]:
        """Get portfolio allocation by market category"""
        try:
            db = SessionLocal()
            try:
                # Get positions with market information
                positions = db.query(Position).join(Trade).join(Market).all()

                category_values = {}
                total_value = 0

                for position in positions:
                    category = position.trade.market.category
                    value = float(position.current_value or 0)

                    if category not in category_values:
                        category_values[category] = 0
                    category_values[category] += value
                    total_value += value

                # Calculate percentages
                category_allocation = {}
                for category, value in category_values.items():
                    percentage = (value / total_value) * 100 if total_value > 0 else 0
                    category_allocation[category] = {
                        'value': value,
                        'percentage': percentage,
                        'positions': len([p for p in positions if p.trade.market.category == category])
                    }

                # Add cash allocation
                balance_info = kalshi_client.get_balance()
                cash_balance = float(balance_info.get('cash_balance', 0))
                cash_percentage = (cash_balance / (total_value + cash_balance)) * 100 if (total_value + cash_balance) > 0 else 0

                category_allocation['cash'] = {
                    'value': cash_balance,
                    'percentage': cash_percentage,
                    'positions': 0
                }

                return {
                    'total_portfolio_value': total_value + cash_balance,
                    'category_allocation': category_allocation,
                    'total_categories': len([c for c in category_allocation.keys() if c != 'cash']),
                    'largest_category': max(category_allocation.keys(), key=lambda k: category_allocation[k]['value']) if category_allocation else None
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting portfolio allocation: {str(e)}")
            return {}

    async def execute_trade(self, market_id: str, side: str, count: int,
                          price: Optional[float] = None) -> Optional[TradeExecution]:
        """Execute a trade and update portfolio"""
        try:
            logger.info(f"Executing trade: {side} {count} contracts for market {market_id}")

            # Place order through Kalshi
            order_result = kalshi_client.place_order(
                market_id=market_id,
                side=side,
                count=count,
                price=price
            )

            # Create trade execution record
            execution = TradeExecution(
                trade_id=order_result.get('order_id', ''),
                market_id=market_id,
                side=side,
                count=count,
                price=float(order_result.get('price', price or 0)),
                executed_at=datetime.utcnow(),
                status=order_result.get('status', 'pending'),
                fees=float(order_result.get('fees', 0))
            )

            # Update trade counters
            self.total_trades += 1
            self.trades_today += 1

            # Update risk manager
            if hasattr(risk_manager, 'increment_daily_trades'):
                risk_manager.increment_daily_trades()

            logger.info(f"Trade executed successfully: {execution.trade_id}")
            return execution

        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return None

# Global portfolio manager instance
portfolio_manager = PortfolioManager()