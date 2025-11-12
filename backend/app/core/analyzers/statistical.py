import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
from scipy.signal import find_peaks
import talib
from loguru import logger

from app.core.kalshi_client import kalshi_client
from app.models.enums import MarketCategory, AnalyzerType

class StatisticalAnalyzer:
    """
    Statistical analysis engine that applies technical analysis and statistical
    pattern recognition to identify trading opportunities in market data.
    """

    def __init__(self):
        # Technical indicator parameters
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2

        # Pattern recognition parameters
        self.min_pattern_samples = 20
        self.similarity_threshold = 0.85
        self.lookback_days = 90

        # Statistical model parameters
        self.mean_reversion_window = 30
        self.momentum_window = 14
        self.volatility_window = 20

    def _calculate_price_changes(self, prices: List[float]) -> List[float]:
        """Calculate price changes for statistical analysis"""
        if len(prices) < 2:
            return []
        return [prices[i] - prices[i-1] for i in range(1, len(prices))]

    def _calculate_returns(self, prices: List[float]) -> List[float]:
        """Calculate percentage returns"""
        if len(prices) < 2:
            return []
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
            else:
                returns.append(0.0)
        return returns

    def _calculate_rsi(self, prices: List[float]) -> float:
        """Calculate Relative Strength Index"""
        try:
            if len(prices) < self.rsi_period + 1:
                return 50.0  # Neutral RSI

            prices_array = np.array(prices)
            deltas = np.diff(prices_array)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            avg_gain = np.mean(gains[-self.rsi_period:])
            avg_loss = np.mean(losses[-self.rsi_period:])

            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

        except Exception as e:
            logger.warning(f"Error calculating RSI: {str(e)}")
            return 50.0

    def _calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            if len(prices) < self.macd_slow:
                return {
                    'macd': 0.0,
                    'signal': 0.0,
                    'histogram': 0.0,
                    'macd_signal': 'neutral'
                }

            prices_array = np.array(prices)

            # Calculate EMAs
            ema_fast = self._calculate_ema(prices_array, self.macd_fast)
            ema_slow = self._calculate_ema(prices_array, self.macd_slow)
            ema_signal = self._calculate_ema(ema_fast - ema_slow, self.macd_signal)

            macd_line = ema_fast[-1] - ema_slow[-1]
            signal_line = ema_signal[-1]
            histogram = macd_line - signal_line

            # Determine MACD signal
            if macd_line > signal_line and histogram > 0:
                macd_signal = 'bullish'
            elif macd_line < signal_line and histogram < 0:
                macd_signal = 'bearish'
            else:
                macd_signal = 'neutral'

            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram,
                'macd_signal': macd_signal
            }

        except Exception as e:
            logger.warning(f"Error calculating MACD: {str(e)}")
            return {
                'macd': 0.0,
                'signal': 0.0,
                'histogram': 0.0,
                'macd_signal': 'neutral'
            }

    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        try:
            if len(data) < period:
                return np.full(len(data), data[0] if len(data) > 0 else 0)

            alpha = 2 / (period + 1)
            ema = np.zeros_like(data)
            ema[0] = data[0]

            for i in range(1, len(data)):
                ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]

            return ema

        except Exception as e:
            logger.warning(f"Error calculating EMA: {str(e)}")
            return np.zeros_like(data)

    def _calculate_bollinger_bands(self, prices: List[float]) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        try:
            if len(prices) < self.bb_period:
                return {
                    'upper_band': 0.0,
                    'middle_band': 0.0,
                    'lower_band': 0.0,
                    'bandwidth': 0.0,
                    'bb_position': 0.5
                }

            prices_array = np.array(prices[-self.bb_period:])
            middle_band = np.mean(prices_array)
            std_dev = np.std(prices_array)

            upper_band = middle_band + (self.bb_std * std_dev)
            lower_band = middle_band - (self.bb_std * std_dev)
            bandwidth = (upper_band - lower_band) / middle_band if middle_band != 0 else 0

            current_price = prices[-1]
            if upper_band != lower_band:
                bb_position = (current_price - lower_band) / (upper_band - lower_band)
            else:
                bb_position = 0.5

            return {
                'upper_band': upper_band,
                'middle_band': middle_band,
                'lower_band': lower_band,
                'bandwidth': bandwidth,
                'bb_position': bb_position
            }

        except Exception as e:
            logger.warning(f"Error calculating Bollinger Bands: {str(e)}")
            return {
                'upper_band': 0.0,
                'middle_band': 0.0,
                'lower_band': 0.0,
                'bandwidth': 0.0,
                'bb_position': 0.5
            }

    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate price volatility"""
        try:
            if len(returns) < 2:
                return 0.0

            returns_array = np.array(returns)
            volatility = np.std(returns_array) * np.sqrt(252)  # Annualized volatility
            return volatility

        except Exception as e:
            logger.warning(f"Error calculating volatility: {str(e)}")
            return 0.0

    def _detect_mean_reversion(self, prices: List[float]) -> Tuple[float, float]:
        """Detect mean reversion patterns and calculate z-score"""
        try:
            if len(prices) < self.mean_reversion_window:
                return 0.0, 0.0

            recent_prices = np.array(prices[-self.mean_reversion_window:])
            mean_price = np.mean(recent_prices)
            std_price = np.std(recent_prices)

            if std_price == 0:
                return 0.0, 0.0

            current_price = prices[-1]
            z_score = (current_price - mean_price) / std_price

            # Mean reversion signal (negative z-score suggests price is below mean)
            mean_reversion_signal = -z_score / 2  # Normalize to reasonable range

            return mean_reversion_signal, z_score

        except Exception as e:
            logger.warning(f"Error detecting mean reversion: {str(e)}")
            return 0.0, 0.0

    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum"""
        try:
            if len(prices) < self.momentum_window:
                return 0.0

            current_price = prices[-1]
            past_price = prices[-self.momentum_window]

            if past_price == 0:
                return 0.0

            momentum = (current_price - past_price) / past_price
            return momentum * 100  # Convert to percentage

        except Exception as e:
            logger.warning(f"Error calculating momentum: {str(e)}")
            return 0.0

    def _find_price_patterns(self, prices: List[float]) -> Dict[str, any]:
        """Identify common chart patterns"""
        try:
            if len(prices) < 20:
                return {
                    'pattern_found': False,
                    'pattern_type': None,
                    'pattern_strength': 0.0
                }

            prices_array = np.array(prices)

            # Find peaks and troughs
            peaks, _ = find_peaks(prices_array, distance=5)
            troughs, _ = find_peaks(-prices_array, distance=5)

            # Simple pattern detection
            pattern_found = False
            pattern_type = None
            pattern_strength = 0.0

            # Head and shoulders pattern detection (simplified)
            if len(peaks) >= 3 and len(troughs) >= 2:
                peak_prices = prices_array[peaks]
                trough_prices = prices_array[troughs]

                # Check for head and shoulders
                if len(peak_prices) >= 3:
                    if (peak_prices[1] > peak_prices[0] and peak_prices[1] > peak_prices[2] and
                        abs(peak_prices[0] - peak_prices[2]) / peak_prices[1] < 0.1):
                        pattern_found = True
                        pattern_type = 'head_and_shoulders'
                        pattern_strength = 0.7

            # Double top/bottom detection (simplified)
            if not pattern_found and len(peaks) >= 2:
                peak_prices = prices_array[peaks]
                if len(peak_prices) >= 2:
                    price_diff = abs(peak_prices[-1] - peak_prices[-2])
                    avg_price = (peak_prices[-1] + peak_prices[-2]) / 2
                    if avg_price > 0 and price_diff / avg_price < 0.05:
                        pattern_found = True
                        pattern_type = 'double_top'
                        pattern_strength = 0.6

            if not pattern_found and len(troughs) >= 2:
                trough_prices = prices_array[troughs]
                if len(trough_prices) >= 2:
                    price_diff = abs(trough_prices[-1] - trough_prices[-2])
                    avg_price = (trough_prices[-1] + trough_prices[-2]) / 2
                    if avg_price > 0 and price_diff / avg_price < 0.05:
                        pattern_found = True
                        pattern_type = 'double_bottom'
                        pattern_strength = 0.6

            return {
                'pattern_found': pattern_found,
                'pattern_type': pattern_type,
                'pattern_strength': pattern_strength
            }

        except Exception as e:
            logger.warning(f"Error finding price patterns: {str(e)}")
            return {
                'pattern_found': False,
                'pattern_type': None,
                'pattern_strength': 0.0
            }

    def _calculate_support_resistance(self, prices: List[float]) -> Dict[str, float]:
        """Calculate support and resistance levels"""
        try:
            if len(prices) < 20:
                return {
                    'support_level': 0.0,
                    'resistance_level': 0.0,
                    'current_vs_support': 0.0,
                    'current_vs_resistance': 0.0
                }

            prices_array = np.array(prices)

            # Find local minima and maxima for support/resistance
            window = 5
            local_minima = []
            local_maxima = []

            for i in range(window, len(prices_array) - window):
                # Check for local minimum (support)
                if prices_array[i] == min(prices_array[i-window:i+window+1]):
                    local_minima.append(prices_array[i])

                # Check for local maximum (resistance)
                if prices_array[i] == max(prices_array[i-window:i+window+1]):
                    local_maxima.append(prices_array[i])

            # Calculate support and resistance levels
            support_level = np.mean(local_minima) if local_minima else prices_array[-1] * 0.95
            resistance_level = np.mean(local_maxima) if local_maxima else prices_array[-1] * 1.05

            current_price = prices_array[-1]

            current_vs_support = (current_price - support_level) / support_level if support_level > 0 else 0
            current_vs_resistance = (resistance_level - current_price) / resistance_level if resistance_level > 0 else 0

            return {
                'support_level': support_level,
                'resistance_level': resistance_level,
                'current_vs_support': current_vs_support,
                'current_vs_resistance': current_vs_resistance
            }

        except Exception as e:
            logger.warning(f"Error calculating support/resistance: {str(e)}")
            return {
                'support_level': 0.0,
                'resistance_level': 0.0,
                'current_vs_support': 0.0,
                'current_vs_resistance': 0.0
            }

    def _calculate_statistical_score(self, indicators: Dict) -> float:
        """Combine statistical indicators into single score"""
        try:
            score = 0.0
            weight_sum = 0.0

            # RSI contribution
            rsi = indicators.get('rsi', 50)
            if rsi < 30:
                score += (30 - rsi) * 2  # Oversold signal (positive)
                weight_sum += 2
            elif rsi > 70:
                score += (70 - rsi) * 2  # Overbought signal (negative)
                weight_sum += 2

            # MACD contribution
            macd_signal = indicators.get('macd', {}).get('macd_signal', 'neutral')
            if macd_signal == 'bullish':
                score += 15
                weight_sum += 1
            elif macd_signal == 'bearish':
                score -= 15
                weight_sum += 1

            # Bollinger Bands contribution
            bb_position = indicators.get('bollinger_bands', {}).get('bb_position', 0.5)
            if bb_position < 0.2:  # Near lower band (potential buy)
                score += (0.2 - bb_position) * 50
                weight_sum += 1
            elif bb_position > 0.8:  # Near upper band (potential sell)
                score -= (bb_position - 0.8) * 50
                weight_sum += 1

            # Mean reversion contribution
            mean_reversion = indicators.get('mean_reversion_signal', 0.0)
            score += mean_reversion * 10
            weight_sum += 1

            # Momentum contribution
            momentum = indicators.get('momentum', 0.0)
            score += momentum
            weight_sum += 0.5

            # Support/Resistance contribution
            support_dist = indicators.get('support_resistance', {}).get('current_vs_support', 0.0)
            resistance_dist = indicators.get('support_resistance', {}).get('current_vs_resistance', 0.0)

            if support_dist > 0.05:  # Well above support (positive)
                score += support_dist * 20
            if resistance_dist < 0.02:  # Close to resistance (negative)
                score -= resistance_dist * 50

            weight_sum += 1

            # Normalize score
            if weight_sum > 0:
                normalized_score = score / weight_sum
            else:
                normalized_score = 0.0

            return max(-100, min(100, normalized_score))

        except Exception as e:
            logger.warning(f"Error calculating statistical score: {str(e)}")
            return 0.0

    def _calculate_confidence(self, indicators: Dict, data_quality: float) -> float:
        """Calculate confidence in statistical analysis"""
        try:
            base_confidence = data_quality * 60  # Up to 60 from data quality

            # Confidence from indicator consensus
            indicator_signals = []

            # RSI signal
            rsi = indicators.get('rsi', 50)
            if rsi < 30:
                indicator_signals.append('bullish')
            elif rsi > 70:
                indicator_signals.append('bearish')

            # MACD signal
            macd_signal = indicators.get('macd', {}).get('macd_signal', 'neutral')
            if macd_signal != 'neutral':
                indicator_signals.append(macd_signal)

            # Bollinger Bands signal
            bb_position = indicators.get('bollinger_bands', {}).get('bb_position', 0.5)
            if bb_position < 0.2:
                indicator_signals.append('bullish')
            elif bb_position > 0.8:
                indicator_signals.append('bearish')

            # Calculate consensus strength
            if len(indicator_signals) >= 2:
                consensus_strength = max(indicator_signals.count('bullish'), indicator_signals.count('bearish')) / len(indicator_signals)
                consensus_confidence = consensus_strength * 30
            else:
                consensus_confidence = 10

            # Pattern confidence bonus
            pattern_found = indicators.get('price_patterns', {}).get('pattern_found', False)
            pattern_bonus = 10 if pattern_found else 0

            total_confidence = base_confidence + consensus_confidence + pattern_bonus
            return min(total_confidence, 100.0)

        except Exception as e:
            logger.warning(f"Error calculating confidence: {str(e)}")
            return 50.0

    async def analyze_market_statistical(self, market_id: str, market_title: str = "") -> Dict:
        """
        Perform comprehensive statistical analysis of a market

        Args:
            market_id: Unique identifier for the market
            market_title: Title of the market (for context)

        Returns:
            Dictionary containing statistical analysis results
        """
        try:
            start_time = datetime.utcnow()

            logger.info(f"Starting statistical analysis for market: {market_id}")

            # Get historical price data from Kalshi
            try:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=self.lookback_days)

                historical_data = kalshi_client.get_market_history(
                    market_id=market_id,
                    start_date=start_date,
                    end_date=end_date
                )

                if not historical_data:
                    logger.warning(f"No historical data available for market {market_id}")
                    return self._empty_statistical_result("No historical data available")

                # Extract price data
                prices = [float(point.get('price', 0)) for point in historical_data if point.get('price')]
                timestamps = [point.get('timestamp') for point in historical_data if point.get('timestamp')]

                if len(prices) < 10:
                    return self._empty_statistical_result("Insufficient historical data")

            except Exception as e:
                logger.error(f"Error fetching historical data for market {market_id}: {str(e)}")
                return self._empty_statistical_result(f"Data fetch error: {str(e)}")

            # Calculate technical indicators
            indicators = {}

            # Basic statistics
            indicators['current_price'] = prices[-1]
            indicators['price_change_1d'] = ((prices[-1] - prices[-2]) / prices[-2]) * 100 if len(prices) > 1 else 0
            indicators['price_change_7d'] = ((prices[-1] - prices[-7]) / prices[-7]) * 100 if len(prices) > 7 else 0
            indicators['volatility'] = self._calculate_volatility(self._calculate_returns(prices))

            # Technical indicators
            indicators['rsi'] = self._calculate_rsi(prices)
            indicators['macd'] = self._calculate_macd(prices)
            indicators['bollinger_bands'] = self._calculate_bollinger_bands(prices)

            # Statistical patterns
            indicators['mean_reversion_signal'], indicators['z_score'] = self._detect_mean_reversion(prices)
            indicators['momentum'] = self._calculate_momentum(prices)
            indicators['price_patterns'] = self._find_price_patterns(prices)
            indicators['support_resistance'] = self._calculate_support_resistance(prices)

            # Calculate overall statistical score
            statistical_score = self._calculate_statistical_score(indicators)

            # Calculate confidence
            data_quality = min(len(prices) / 30, 1.0)  # Quality based on data points
            confidence = self._calculate_confidence(indicators, data_quality)

            # Determine signal classification
            if statistical_score > 15:
                signal_classification = "strong_buy"
            elif statistical_score > 5:
                signal_classification = "buy"
            elif statistical_score > -5:
                signal_classification = "hold"
            elif statistical_score > -15:
                signal_classification = "sell"
            else:
                signal_classification = "strong_sell"

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            result = {
                'statistical_score': statistical_score,
                'confidence': confidence,
                'signal_classification': signal_classification,
                'indicators': indicators,
                'details': {
                    'data_points': len(prices),
                    'date_range': {
                        'start': timestamps[0] if timestamps else None,
                        'end': timestamps[-1] if timestamps else None
                    },
                    'data_quality': data_quality,
                    'processing_time_seconds': processing_time,
                    'market_id': market_id,
                    'market_title': market_title
                }
            }

            logger.info(f"Statistical analysis completed: {statistical_score:.2f} ({signal_classification}) with {confidence:.1f}% confidence")
            return result

        except Exception as e:
            logger.error(f"Error in statistical analysis: {str(e)}")
            return self._empty_statistical_result(f"Analysis error: {str(e)}")

    def _empty_statistical_result(self, error_message: str) -> Dict:
        """Return empty statistical result with error"""
        return {
            'statistical_score': 0.0,
            'confidence': 0.0,
            'signal_classification': 'error',
            'indicators': {},
            'details': {
                'error': error_message,
                'processing_failed': True
            }
        }

# Global statistical analyzer instance
statistical_analyzer = StatisticalAnalyzer()