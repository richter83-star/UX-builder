import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
from loguru import logger

from app.core.kalshi_client import kalshi_client
from app.models.database import SessionLocal
from app.models.schemas import Position, Trade, Market
from app.models.enums import MarketCategory, TradeSide, RiskProfile
from app.utils.config import settings

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskAlertType(Enum):
    POSITION_SIZE_EXCEEDED = "position_size_exceeded"
    CATEGORY_EXPOSURE_EXCEEDED = "category_exposure_exceeded"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    CORRELATION_RISK = "correlation_risk"
    MARGIN_WARNING = "margin_warning"
    DRAWDOWN_ALERT = "drawdown_alert"
    VOLATILITY_SPIKE = "volatility_spike"

@dataclass
class RiskCheck:
    passed: bool
    level: RiskLevel
    message: str
    details: Dict[str, Any]

@dataclass
class PositionRisk:
    position_id: str
    risk_score: float
    risk_level: RiskLevel
    current_pnl: float
    max_loss_potential: float
    risk_checks: List[RiskCheck]

@dataclass
class TradeRiskAssessment:
    approved: bool
    risk_level: RiskLevel
    risk_score: float
    position_size: float
    max_loss: float
    risk_checks: List[RiskCheck]
    recommendations: List[str]

class RiskManager:
    """
    Advanced risk management system that ensures responsible trading behavior
    and capital preservation through comprehensive risk monitoring and controls.
    """

    def __init__(self):
        # Risk configuration
        self.config = settings.DEFAULT_RISK_CONFIG.copy()
        self.user_profiles = settings.RISK_PROFILES.copy()

        # Risk tracking
        self.daily_pnl = 0.0
        self.daily_trades_count = 0
        self.last_reset_date = datetime.utcnow().date()
        self.current_positions = {}
        self.risk_alerts = []
        self.portfolio_value = 10000.0  # Default starting value

        # Correlation tracking
        self.correlation_matrix = {}
        self.category_exposures = defaultdict(float)

        # Performance tracking
        self.max_portfolio_value = self.portfolio_value
        self.current_drawdown = 0.0
        self.daily_returns = []

        # Risk monitoring
        self.risk_checks_enabled = True
        self.emergency_stop_active = False

        # Initialize risk metrics
        self._initialize_risk_metrics()

    def _initialize_risk_metrics(self):
        """Initialize risk tracking metrics"""
        try:
            # Load current positions from database
            self._load_current_positions()
            self._update_portfolio_value()
            self._calculate_category_exposures()

            logger.info("Risk manager initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing risk manager: {str(e)}")

    def _load_current_positions(self):
        """Load current positions from database"""
        try:
            db = SessionLocal()
            try:
                positions = db.query(Position).all()
                for position in positions:
                    self.current_positions[position.id] = {
                        'market_id': position.trade.market_id,
                        'side': position.trade.side,
                        'count': position.trade.count,
                        'price': position.trade.price,
                        'current_value': position.current_value or 0,
                        'unrealized_pnl': position.unrealized_pnl or 0,
                        'updated_at': position.updated_at
                    }
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error loading current positions: {str(e)}")

    def _update_portfolio_value(self):
        """Update current portfolio value"""
        try:
            # Get account balance from Kalshi
            balance_info = kalshi_client.get_balance()
            account_balance = float(balance_info.get('total_balance', 0))

            # Calculate unrealized P&L from positions
            total_unrealized_pnl = sum(
                position['unrealized_pnl']
                for position in self.current_positions.values()
            )

            self.portfolio_value = account_balance + total_unrealized_pnl

            # Update maximum portfolio value for drawdown calculation
            if self.portfolio_value > self.max_portfolio_value:
                self.max_portfolio_value = self.portfolio_value

            # Calculate current drawdown
            if self.max_portfolio_value > 0:
                self.current_drawdown = (self.max_portfolio_value - self.portfolio_value) / self.max_portfolio_value * 100

        except Exception as e:
            logger.warning(f"Error updating portfolio value: {str(e)}")

    def _calculate_category_exposures(self):
        """Calculate exposure by market category"""
        try:
            # Reset category exposures
            self.category_exposures.clear()

            db = SessionLocal()
            try:
                for position_id, position_data in self.current_positions.items():
                    # Get market category
                    market = db.query(Market).filter(
                        Market.market_id == position_data['market_id']
                    ).first()

                    if market:
                        category = market.category
                        position_value = position_data['current_value'] or position_data['price'] * position_data['count']
                        self.category_exposures[category] += position_value

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error calculating category exposures: {str(e)}")

    def _reset_daily_metrics(self):
        """Reset daily metrics if new day"""
        current_date = datetime.utcnow().date()
        if current_date > self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trades_count = 0
            self.last_reset_date = current_date
            logger.info("Daily risk metrics reset")

    def _calculate_kelly_position_size(self, expected_return: float, win_probability: float,
                                     user_risk_profile: str = 'moderate') -> float:
        """
        Calculate optimal position size using Kelly Criterion
        Kelly % = W - [(1 - W) / R]
        Where W = win probability, R = win/loss ratio
        """
        try:
            # Get user's Kelly fraction based on risk profile
            kelly_fraction = self.user_profiles.get(user_risk_profile, {}).get('kelly_fraction', 0.25)

            # Calculate Kelly percentage
            if win_probability <= 0 or win_probability >= 1:
                return 0.0

            # Estimate average win/loss ratio (simplified)
            win_loss_ratio = abs(expected_return) / 0.05 if expected_return != 0 else 1.0  # Assume 5% average loss

            kelly_percentage = win_probability - ((1 - win_probability) / win_loss_ratio)
            kelly_percentage = max(0, kelly_percentage)  # Can't be negative

            # Apply fractional Kelly and convert to portfolio percentage
            position_size_percentage = kelly_percentage * kelly_fraction * 100

            return min(position_size_percentage, self.config['max_position_size_percent'])

        except Exception as e:
            logger.error(f"Error calculating Kelly position size: {str(e)}")
            return self.config['max_position_size_percent'] * 0.5  # Conservative fallback

    def _check_position_size_risk(self, trade_size: float, market_id: str) -> RiskCheck:
        """Check if position size exceeds limits"""
        try:
            position_percentage = (trade_size / self.portfolio_value) * 100

            max_position_size = self.config['max_position_size_percent']

            if position_percentage > max_position_size * 1.5:
                return RiskCheck(
                    passed=False,
                    level=RiskLevel.CRITICAL,
                    message=f"Position size {position_percentage:.2f}% far exceeds limit of {max_position_size}%",
                    details={
                        'position_percentage': position_percentage,
                        'max_allowed': max_position_size,
                        'excess_by': position_percentage - max_position_size
                    }
                )
            elif position_percentage > max_position_size:
                return RiskCheck(
                    passed=False,
                    level=RiskLevel.HIGH,
                    message=f"Position size {position_percentage:.2f}% exceeds limit of {max_position_size}%",
                    details={
                        'position_percentage': position_percentage,
                        'max_allowed': max_position_size,
                        'excess_by': position_percentage - max_position_size
                    }
                )
            else:
                return RiskCheck(
                    passed=True,
                    level=RiskLevel.LOW,
                    message=f"Position size {position_percentage:.2f}% within limits",
                    details={
                        'position_percentage': position_percentage,
                        'max_allowed': max_position_size
                    }
                )

        except Exception as e:
            return RiskCheck(
                passed=False,
                level=RiskLevel.HIGH,
                message=f"Error checking position size: {str(e)}",
                details={'error': str(e)}
            )

    def _check_category_exposure_risk(self, market_id: str, trade_size: float) -> RiskCheck:
        """Check if category exposure exceeds limits"""
        try:
            # Get market category
            db = SessionLocal()
            try:
                market = db.query(Market).filter(Market.market_id == market_id).first()
                if not market:
                    return RiskCheck(
                        passed=True,
                        level=RiskLevel.LOW,
                        message="Market not found - cannot check category exposure",
                        details={'market_id': market_id}
                    )

                category = market.category
                current_exposure = self.category_exposures.get(category, 0)
                new_exposure = current_exposure + trade_size
                exposure_percentage = (new_exposure / self.portfolio_value) * 100

                max_category_exposure = self.config['max_category_exposure_percent']

                if exposure_percentage > max_category_exposure:
                    return RiskCheck(
                        passed=False,
                        level=RiskLevel.HIGH,
                        message=f"Category {category} exposure {exposure_percentage:.2f}% exceeds limit of {max_category_exposure}%",
                        details={
                            'category': category,
                            'current_exposure': current_exposure,
                            'new_exposure': new_exposure,
                            'exposure_percentage': exposure_percentage,
                            'max_allowed': max_category_exposure
                        }
                    )
                else:
                    return RiskCheck(
                        passed=True,
                        level=RiskLevel.LOW,
                        message=f"Category {category} exposure {exposure_percentage:.2f}% within limits",
                        details={
                            'category': category,
                            'exposure_percentage': exposure_percentage,
                            'max_allowed': max_category_exposure
                        }
                    )

            finally:
                db.close()

        except Exception as e:
            return RiskCheck(
                passed=False,
                level=RiskLevel.HIGH,
                message=f"Error checking category exposure: {str(e)}",
                details={'error': str(e)}
            )

    def _check_daily_loss_limit(self) -> RiskCheck:
        """Check if daily loss limit is exceeded"""
        try:
            self._reset_daily_metrics()

            daily_loss_percentage = abs(self.daily_pnl) / self.portfolio_value * 100 if self.daily_pnl < 0 else 0
            daily_loss_limit = self.config['daily_loss_limit_percent']

            if daily_loss_percentage > daily_loss_limit * 1.5:
                return RiskCheck(
                    passed=False,
                    level=RiskLevel.CRITICAL,
                    message=f"Daily loss {daily_loss_percentage:.2f}% critically exceeds limit of {daily_loss_limit}%",
                    details={
                        'daily_loss': self.daily_pnl,
                        'daily_loss_percentage': daily_loss_percentage,
                        'limit_percentage': daily_loss_limit,
                        'excess_by': daily_loss_percentage - daily_loss_limit
                    }
                )
            elif daily_loss_percentage > daily_loss_limit:
                return RiskCheck(
                    passed=False,
                    level=RiskLevel.HIGH,
                    message=f"Daily loss {daily_loss_percentage:.2f}% exceeds limit of {daily_loss_limit}%",
                    details={
                        'daily_loss': self.daily_pnl,
                        'daily_loss_percentage': daily_loss_percentage,
                        'limit_percentage': daily_loss_limit,
                        'excess_by': daily_loss_percentage - daily_loss_limit
                    }
                )
            else:
                return RiskCheck(
                    passed=True,
                    level=RiskLevel.LOW,
                    message=f"Daily loss {daily_loss_percentage:.2f}% within limit of {daily_loss_limit}%",
                    details={
                        'daily_loss': self.daily_pnl,
                        'daily_loss_percentage': daily_loss_percentage,
                        'limit_percentage': daily_loss_limit
                    }
                )

        except Exception as e:
            return RiskCheck(
                passed=False,
                level=RiskLevel.MEDIUM,
                message=f"Error checking daily loss limit: {str(e)}",
                details={'error': str(e)}
            )

    def _check_correlation_risk(self, market_id: str, trade_size: float) -> RiskCheck:
        """Check correlation risk with existing positions"""
        try:
            # Simplified correlation check based on market categories
            # In production, this would use actual price correlation calculations

            db = SessionLocal()
            try:
                market = db.query(Market).filter(Market.market_id == market_id).first()
                if not market:
                    return RiskCheck(
                        passed=True,
                        level=RiskLevel.LOW,
                        message="Cannot check correlation - market not found",
                        details={'market_id': market_id}
                    )

                new_category = market.category
                max_correlation = self.config['max_correlation']

                # Check exposure to similar categories
                similar_categories = {
                    'politics': ['government'],
                    'finance': ['economy', 'banking'],
                    'sports': ['entertainment'],
                    'technology': ['innovation']
                }

                total_similar_exposure = 0
                for category, similar in similar_categories.items():
                    if new_category == category or new_category in similar:
                        total_similar_exposure += self.category_exposures.get(category, 0)
                        for sim_category in similar:
                            total_similar_exposure += self.category_exposures.get(sim_category, 0)

                total_similar_exposure += trade_size
                correlation_ratio = total_similar_exposure / self.portfolio_value

                if correlation_ratio > max_correlation:
                    return RiskCheck(
                        passed=False,
                        level=RiskLevel.MEDIUM,
                        message=f"High correlation risk: {correlation_ratio:.2f} exposure to similar markets",
                        details={
                            'market_category': new_category,
                            'similar_exposure': total_similar_exposure,
                            'correlation_ratio': correlation_ratio,
                            'max_allowed': max_correlation
                        }
                    )
                else:
                    return RiskCheck(
                        passed=True,
                        level=RiskLevel.LOW,
                        message=f"Correlation risk acceptable: {correlation_ratio:.2f}",
                        details={
                            'correlation_ratio': correlation_ratio,
                            'max_allowed': max_correlation
                        }
                    )

            finally:
                db.close()

        except Exception as e:
            return RiskCheck(
                passed=False,
                level=RiskLevel.MEDIUM,
                message=f"Error checking correlation risk: {str(e)}",
                details={'error': str(e)}
            )

    def _check_drawdown_limit(self) -> RiskCheck:
        """Check if drawdown exceeds warning limits"""
        try:
            drawdown_warning = 10.0  # 10% drawdown warning
            drawdown_critical = 15.0  # 15% drawdown critical

            if self.current_drawdown > drawdown_critical:
                return RiskCheck(
                    passed=False,
                    level=RiskLevel.CRITICAL,
                    message=f"Critical drawdown: {self.current_drawdown:.2f}% exceeds limit of {drawdown_critical}%",
                    details={
                        'current_drawdown': self.current_drawdown,
                        'warning_threshold': drawdown_warning,
                        'critical_threshold': drawdown_critical,
                        'max_portfolio_value': self.max_portfolio_value,
                        'current_value': self.portfolio_value
                    }
                )
            elif self.current_drawdown > drawdown_warning:
                return RiskCheck(
                    passed=True,  # Warning only, not blocking
                    level=RiskLevel.HIGH,
                    message=f"Drawdown warning: {self.current_drawdown:.2f}% exceeds warning threshold of {drawdown_warning}%",
                    details={
                        'current_drawdown': self.current_drawdown,
                        'warning_threshold': drawdown_warning,
                        'critical_threshold': drawdown_critical
                    }
                )
            else:
                return RiskCheck(
                    passed=True,
                    level=RiskLevel.LOW,
                    message=f"Drawdown {self.current_drawdown:.2f}% within acceptable limits",
                    details={
                        'current_drawdown': self.current_drawdown,
                        'warning_threshold': drawdown_warning
                    }
                )

        except Exception as e:
            return RiskCheck(
                passed=False,
                level=RiskLevel.MEDIUM,
                message=f"Error checking drawdown: {str(e)}",
                details={'error': str(e)}
            )

    def assess_trade_risk(self, market_id: str, side: str, count: int, price: float,
                         expected_return: float = 0, win_probability: float = 0.5,
                         user_risk_profile: str = 'moderate') -> TradeRiskAssessment:
        """
        Comprehensive risk assessment for a potential trade

        Args:
            market_id: Unique identifier for the market
            side: 'yes' or 'no'
            count: Number of contracts
            price: Price per contract
            expected_return: Expected return percentage
            win_probability: Probability of winning (0-1)
            user_risk_profile: User's risk profile

        Returns:
            TradeRiskAssessment with detailed risk analysis
        """
        try:
            logger.info(f"Assessing trade risk for market {market_id}: {side} {count} @ {price}")

            # Calculate trade size
            trade_size = count * price

            # Initialize risk checks
            risk_checks = []
            overall_risk_level = RiskLevel.LOW
            critical_issues = []

            # Check if risk management is enabled
            if self.emergency_stop_active:
                critical_issues.append("Emergency stop is active - all trading halted")

            if not self.risk_checks_enabled:
                critical_issues.append("Risk checks are disabled")

            # Daily loss limit check
            daily_loss_check = self._check_daily_loss_limit()
            risk_checks.append(daily_loss_check)
            if not daily_loss_check.passed and daily_loss_check.level == RiskLevel.CRITICAL:
                critical_issues.append(daily_loss_check.message)

            # Drawdown check
            drawdown_check = self._check_drawdown_limit()
            risk_checks.append(drawdown_check)
            if not drawdown_check.passed and drawdown_check.level == RiskLevel.CRITICAL:
                critical_issues.append(drawdown_check.message)

            # Position size risk
            position_size_check = self._check_position_size_risk(trade_size, market_id)
            risk_checks.append(position_size_check)
            if not position_size_check.passed:
                overall_risk_level = max(overall_risk_level, position_size_check.level, key=lambda x: list(RiskLevel).index(x))

            # Category exposure risk
            category_risk = self._check_category_exposure_risk(market_id, trade_size)
            risk_checks.append(category_risk)
            if not category_risk.passed:
                overall_risk_level = max(overall_risk_level, category_risk.level, key=lambda x: list(RiskLevel).index(x))

            # Correlation risk
            correlation_risk = self._check_correlation_risk(market_id, trade_size)
            risk_checks.append(correlation_risk)
            if not correlation_risk.passed:
                overall_risk_level = max(overall_risk_level, correlation_risk.level, key=lambda x: list(RiskLevel).index(x))

            # Calculate optimal position size using Kelly Criterion
            kelly_recommended_size = self._calculate_kelly_position_size(
                expected_return, win_probability, user_risk_profile
            )

            # Determine if trade should be approved
            approved = len(critical_issues) == 0 and all(check.passed for check in risk_checks)

            # Additional checks for user profile
            if user_risk_profile in self.user_profiles:
                profile_config = self.user_profiles[user_risk_profile]

                # Check confidence threshold
                min_confidence = profile_config.get('min_confidence_threshold', 60.0)
                if win_probability * 100 < min_confidence:
                    approved = False
                    critical_issues.append(f"Win probability {win_probability*100:.1f}% below minimum {min_confidence}% for {user_risk_profile} profile")

            # Calculate risk score
            risk_score = self._calculate_trade_risk_score(risk_checks, trade_size, expected_return)

            # Calculate maximum potential loss
            max_loss = trade_size if side == 'yes' else trade_size * (1 - price)

            # Generate recommendations
            recommendations = self._generate_trade_recommendations(
                risk_checks, trade_size, kelly_recommended_size, expected_return
            )

            # Create assessment result
            assessment = TradeRiskAssessment(
                approved=approved,
                risk_level=overall_risk_level,
                risk_score=risk_score,
                position_size=trade_size,
                max_loss=max_loss,
                risk_checks=risk_checks,
                recommendations=recommendations
            )

            logger.info(f"Trade risk assessment completed: {'APPROVED' if approved else 'REJECTED'} - Risk level: {overall_risk_level.value}")
            return assessment

        except Exception as e:
            logger.error(f"Error in trade risk assessment: {str(e)}")
            return TradeRiskAssessment(
                approved=False,
                risk_level=RiskLevel.CRITICAL,
                risk_score=100.0,
                position_size=0,
                max_loss=0,
                risk_checks=[RiskCheck(
                    passed=False,
                    level=RiskLevel.CRITICAL,
                    message=f"Risk assessment error: {str(e)}",
                    details={'error': str(e)}
                )],
                recommendations=["Fix risk assessment system before trading"]
            )

    def _calculate_trade_risk_score(self, risk_checks: List[RiskCheck], trade_size: float,
                                  expected_return: float) -> float:
        """Calculate overall risk score for the trade (0-100)"""
        try:
            base_score = 30.0  # Base risk score

            # Position size risk
            size_score = (trade_size / self.portfolio_value) * 100 * 2  # Scale position size impact
            base_score += min(size_score, 40.0)  # Cap at 40 points

            # Failed risk checks
            for check in risk_checks:
                if not check.passed:
                    if check.level == RiskLevel.CRITICAL:
                        base_score += 30
                    elif check.level == RiskLevel.HIGH:
                        base_score += 20
                    elif check.level == RiskLevel.MEDIUM:
                        base_score += 10

            # Expected return adjustment (lower return = higher risk)
            if expected_return < 0:
                base_score += 15
            elif expected_return > 0.1:  # >10% expected return
                base_score -= 10

            return min(max(base_score, 0), 100)

        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 50.0  # Default medium risk

    def _generate_trade_recommendations(self, risk_checks: List[RiskCheck], trade_size: float,
                                      kelly_recommended_size: float, expected_return: float) -> List[str]:
        """Generate recommendations based on risk assessment"""
        recommendations = []

        try:
            # Position size recommendations
            size_percentage = (trade_size / self.portfolio_value) * 100
            if size_percentage > 5:
                recommendations.append(f"Consider reducing position size from {size_percentage:.1f}% to under 5% of portfolio")

            if kelly_recommended_size > 0 and size_percentage > kelly_recommended_size:
                recommendations.append(f"Kelly Criterion recommends {kelly_recommended_size:.1f}% position size vs current {size_percentage:.1f}%")

            # Risk level recommendations
            failed_checks = [check for check in risk_checks if not check.passed]
            if failed_checks:
                for check in failed_checks:
                    if check.level == RiskLevel.HIGH:
                        recommendations.append(f"High priority: {check.message}")

            # Expected return recommendations
            if expected_return < 0.05:  # Less than 5% expected return
                recommendations.append("Expected return is low - consider waiting for better opportunity")

            # General recommendations
            if len(failed_checks) > 2:
                recommendations.append("Multiple risk issues detected - consider reducing risk or skipping this trade")

            if not recommendations:
                recommendations.append("Trade appears acceptable within risk parameters")

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            recommendations.append("Error generating recommendations - proceed with caution")

        return recommendations

    def update_daily_pnl(self, pnl_change: float):
        """Update daily P&L tracking"""
        try:
            self.daily_pnl += pnl_change
            logger.info(f"Daily P&L updated: {self.daily_pnl:.2f}")

        except Exception as e:
            logger.error(f"Error updating daily P&L: {str(e)}")

    def increment_daily_trades(self):
        """Increment daily trade count"""
        try:
            self._reset_daily_metrics()
            self.daily_trades_count += 1
            logger.info(f"Daily trades count: {self.daily_trades_count}")

        except Exception as e:
            logger.error(f"Error incrementing daily trades: {str(e)}")

    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get comprehensive risk metrics"""
        try:
            self._update_portfolio_value()
            self._calculate_category_exposures()

            return {
                'portfolio_value': self.portfolio_value,
                'daily_pnl': self.daily_pnl,
                'daily_trades_count': self.daily_trades_count,
                'current_drawdown': self.current_drawdown,
                'max_portfolio_value': self.max_portfolio_value,
                'category_exposures': dict(self.category_exposures),
                'total_positions': len(self.current_positions),
                'risk_checks_enabled': self.risk_checks_enabled,
                'emergency_stop_active': self.emergency_stop_active,
                'last_updated': datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Error getting risk metrics: {str(e)}")
            return {}

    def set_emergency_stop(self, active: bool, reason: str = ""):
        """Activate or deactivate emergency stop"""
        try:
            self.emergency_stop_active = active
            if active:
                logger.warning(f"EMERGENCY STOP ACTIVATED: {reason}")
                # Could add logic to close all positions here
            else:
                logger.info("Emergency stop deactivated")

        except Exception as e:
            logger.error(f"Error setting emergency stop: {str(e)}")

    def update_risk_config(self, new_config: Dict[str, Any]):
        """Update risk management configuration"""
        try:
            self.config.update(new_config)
            logger.info(f"Risk configuration updated: {new_config}")

        except Exception as e:
            logger.error(f"Error updating risk config: {str(e)}")

# Global risk manager instance
risk_manager = RiskManager()