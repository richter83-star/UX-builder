import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
from loguru import logger

from .sentiment import sentiment_analyzer
from .statistical import statistical_analyzer
from .ml_models import ml_models_analyzer
from app.core.kalshi_client import kalshi_client
from app.models.enums import MarketCategory, AnalyzerType

class EnsembleAnalyzer:
    """
    Ensemble analysis engine that combines multiple analysis methods to provide
    optimal probability predictions through dynamic weight optimization and
    confidence-weighted averaging.
    """

    def __init__(self):
        # Base weights for different analyzers
        self.base_weights = {
            'sentiment': 0.25,
            'statistical': 0.35,
            'ml_models': 0.40
        }

        # Performance tracking for dynamic weight adjustment
        self.analyzer_performance = defaultdict(lambda: {
            'predictions': deque(maxlen=100),  # Track last 100 predictions
            'accuracy': 0.0,
            'recent_accuracy': deque(maxlen=20),  # Last 20 predictions accuracy
            'confidence_avg': 0.0,
            'last_updated': datetime.utcnow()
        })

        # Model performance by market category
        self.category_performance = defaultdict(lambda: {
            'sentiment': {'accuracy': 0.5, 'predictions': 0},
            'statistical': {'accuracy': 0.5, 'predictions': 0},
            'ml_models': {'accuracy': 0.5, 'predictions': 0}
        })

        # Ensemble configuration
        self.min_confidence_threshold = 30.0  # Minimum confidence to consider prediction
        self.max_weight_imbalance = 3.0  # Maximum ratio between highest and lowest weights
        self.rebalance_frequency = 7  # Days between weight rebalancing
        self.last_rebalance = datetime.utcnow()

        # Prediction tracking
        self.prediction_history = defaultdict(list)  # Track predictions by market
        self.outcome_history = {}  # Track actual outcomes for accuracy calculation

    def _determine_market_category(self, market_title: str, subtitle: str = "") -> str:
        """Determine market category from title and subtitle"""
        text = f"{market_title} {subtitle}".lower()

        # Category keywords
        category_keywords = {
            'politics': ['election', 'president', 'congress', 'senate', 'vote', 'politics', 'government', 'policy'],
            'finance': ['stock', 'market', 'economy', 'fed', 'inflation', 'gdp', 'finance', 'trading', 'interest'],
            'sports': ['game', 'team', 'player', 'sport', 'match', 'championship', 'league', 'season'],
            'entertainment': ['movie', 'music', 'award', 'celebrity', 'entertainment', 'show', 'film', 'oscar'],
            'technology': ['tech', 'software', 'ai', 'startup', 'apple', 'google', 'microsoft', 'technology'],
            'weather': ['weather', 'temperature', 'rain', 'snow', 'storm', 'hurricane', 'climate', 'forecast']
        }

        # Count keyword matches for each category
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            category_scores[category] = score

        # Return category with highest score, or 'other' if no matches
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            return best_category if category_scores[best_category] > 0 else 'other'
        else:
            return 'other'

    def _get_category_specific_weights(self, category: str) -> Dict[str, float]:
        """Get category-specific analyzer weights"""
        category_weights = {
            'politics': {'sentiment': 0.35, 'statistical': 0.25, 'ml_models': 0.40},
            'finance': {'sentiment': 0.20, 'statistical': 0.45, 'ml_models': 0.35},
            'sports': {'sentiment': 0.25, 'statistical': 0.30, 'ml_models': 0.45},
            'entertainment': {'sentiment': 0.40, 'statistical': 0.20, 'ml_models': 0.40},
            'technology': {'sentiment': 0.30, 'statistical': 0.25, 'ml_models': 0.45},
            'weather': {'sentiment': 0.15, 'statistical': 0.60, 'ml_models': 0.25},
            'other': self.base_weights.copy()
        }

        return category_weights.get(category, self.base_weights.copy())

    def _update_analyzer_performance(self, analyzer: str, prediction: float,
                                   actual_outcome: float, confidence: float):
        """Update performance metrics for an analyzer"""
        try:
            performance = self.analyzer_performance[analyzer]

            # Determine if prediction was correct (within reasonable margin)
            prediction_correct = abs(prediction - actual_outcome) < 10.0  # Within 10% points

            # Update prediction history
            performance['predictions'].append({
                'prediction': prediction,
                'actual': actual_outcome,
                'confidence': confidence,
                'correct': prediction_correct,
                'timestamp': datetime.utcnow()
            })

            # Update recent accuracy
            performance['recent_accuracy'].append(1 if prediction_correct else 0)

            # Calculate overall accuracy
            if len(performance['predictions']) >= 5:
                correct_predictions = sum(1 for p in performance['predictions'] if p['correct'])
                performance['accuracy'] = correct_predictions / len(performance['predictions'])

            # Update average confidence
            if len(performance['predictions']) >= 1:
                performance['confidence_avg'] = np.mean([p['confidence'] for p in performance['predictions']])

            performance['last_updated'] = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error updating analyzer performance for {analyzer}: {str(e)}")

    def _calculate_dynamic_weights(self, category: str, current_predictions: Dict[str, Dict]) -> Dict[str, float]:
        """Calculate dynamic weights based on recent performance"""
        try:
            # Start with category-specific base weights
            weights = self._get_category_specific_weights(category)

            # Adjust weights based on recent performance
            for analyzer, prediction_data in current_predictions.items():
                if analyzer in weights:
                    performance = self.analyzer_performance[analyzer]

                    # Performance bonus/penalty
                    if performance['accuracy'] > 0:
                        performance_multiplier = performance['accuracy'] / 0.5  # Relative to 50% baseline
                        performance_multiplier = np.clip(performance_multiplier, 0.5, 2.0)  # Limit adjustment
                        weights[analyzer] *= performance_multiplier

                    # Confidence adjustment
                    confidence = prediction_data.get('confidence', 0) / 100.0
                    confidence_multiplier = 0.5 + confidence  # Range: 0.5 to 1.5
                    weights[analyzer] *= confidence_multiplier

            # Normalize weights
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {k: v / total_weight for k, v in weights.items()}

            # Apply weight imbalance limits
            if weights:
                max_weight = max(weights.values())
                min_weight = min(weights.values())

                if max_weight / min_weight > self.max_weight_imbalance:
                    # Rescale to within limits
                    scale_factor = self.max_weight_imbalance / (max_weight / min_weight)
                    for analyzer in weights:
                        if weights[analyzer] > 1.0 / len(weights):
                            weights[analyzer] *= scale_factor

                    # Re-normalize
                    total_weight = sum(weights.values())
                    if total_weight > 0:
                        weights = {k: v / total_weight for k, v in weights.items()}

            return weights

        except Exception as e:
            logger.error(f"Error calculating dynamic weights: {str(e)}")
            return self._get_category_specific_weights(category)

    def _calculate_ensemble_confidence(self, predictions: Dict[str, Dict],
                                     weights: Dict[str, float]) -> float:
        """Calculate ensemble confidence score"""
        try:
            if not predictions:
                return 0.0

            # Weighted average of individual confidences
            weighted_confidence = 0.0
            total_weight = 0.0

            for analyzer, prediction_data in predictions.items():
                if analyzer in weights:
                    confidence = prediction_data.get('confidence', 0)
                    weight = weights[analyzer]

                    weighted_confidence += confidence * weight
                    total_weight += weight

            if total_weight > 0:
                base_confidence = weighted_confidence / total_weight
            else:
                base_confidence = 0.0

            # Consensus bonus - higher confidence when analyzers agree
            if len(predictions) > 1:
                predictions_values = [pred.get('score', 0) for pred in predictions.values()]
                if predictions_values:
                    consensus_strength = 1.0 - (np.std(predictions_values) / 100.0)  # Normalize by 100 point scale
                    consensus_bonus = consensus_strength * 15  # Up to 15 point bonus
                    base_confidence += consensus_bonus

            # Data quality bonus
            data_points_available = sum(
                pred.get('details', {}).get('data_points', 0)
                for pred in predictions.values()
            )
            if data_points_available > 100:
                data_quality_bonus = 10
            elif data_points_available > 50:
                data_quality_bonus = 5
            else:
                data_quality_bonus = 0

            final_confidence = base_confidence + data_quality_bonus
            return min(final_confidence, 100.0)

        except Exception as e:
            logger.error(f"Error calculating ensemble confidence: {str(e)}")
            return 50.0

    def _calculate_ensemble_prediction(self, predictions: Dict[str, Dict],
                                     weights: Dict[str, float]) -> float:
        """Calculate ensemble prediction using confidence-weighted averaging"""
        try:
            if not predictions:
                return 0.0

            weighted_prediction = 0.0
            total_weight = 0.0

            for analyzer, prediction_data in predictions.items():
                if analyzer in weights:
                    score = prediction_data.get('score', 0)
                    confidence = prediction_data.get('confidence', 0) / 100.0
                    weight = weights[analyzer]

                    # Confidence-weighted prediction
                    adjusted_weight = weight * (0.5 + confidence * 0.5)  # Range: 0.5x to 1.0x weight
                    weighted_prediction += score * adjusted_weight
                    total_weight += adjusted_weight

            if total_weight > 0:
                return weighted_prediction / total_weight
            else:
                return 0.0

        except Exception as e:
            logger.error(f"Error calculating ensemble prediction: {str(e)}")
            return 0.0

    def _determine_signal_classification(self, prediction: float, confidence: float) -> str:
        """Determine signal classification based on prediction and confidence"""
        try:
            # Adjust thresholds based on confidence
            if confidence >= 80:
                # High confidence - use standard thresholds
                strong_threshold = 15
                moderate_threshold = 8
            elif confidence >= 60:
                # Medium confidence - wider thresholds
                strong_threshold = 20
                moderate_threshold = 12
            else:
                # Low confidence - very wide thresholds
                strong_threshold = 25
                moderate_threshold = 15

            if prediction > strong_threshold:
                return "strong_buy"
            elif prediction > moderate_threshold:
                return "buy"
            elif prediction > -moderate_threshold:
                return "hold"
            elif prediction > -strong_threshold:
                return "sell"
            else:
                return "strong_sell"

        except Exception as e:
            logger.error(f"Error determining signal classification: {str(e)}")
            return "hold"

    async def analyze_market_ensemble(self, market_id: str, market_title: str,
                                    market_subtitle: str = "", market_category: str = None) -> Dict[str, Any]:
        """
        Perform comprehensive ensemble analysis of a market

        Args:
            market_id: Unique identifier for the market
            market_title: Title of the market
            market_subtitle: Subtitle or description of the market
            market_category: Category of the market (optional - will be inferred if not provided)

        Returns:
            Dictionary containing ensemble analysis results
        """
        try:
            start_time = datetime.utcnow()

            logger.info(f"Starting ensemble analysis for market: {market_title[:50]}...")

            # Determine market category if not provided
            if market_category is None:
                market_category = self._determine_market_category(market_title, market_subtitle)

            # Get recent market data for ML models
            recent_data = []
            historical_data = []

            try:
                # Get historical data
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=90)

                historical_data = kalshi_client.get_market_history(
                    market_id=market_id,
                    start_date=start_date,
                    end_date=end_date
                )

                if historical_data:
                    # Recent data for predictions (last 30 points)
                    recent_data = historical_data[-30:] if len(historical_data) >= 30 else historical_data

            except Exception as e:
                logger.warning(f"Error fetching market data for {market_id}: {str(e)}")

            # Initialize results dictionary
            individual_results = {}
            successful_analyzers = []

            # Run sentiment analysis
            try:
                sentiment_result = await sentiment_analyzer.analyze_market_sentiment(
                    market_title, market_subtitle, market_category
                )
                individual_results['sentiment'] = {
                    'score': sentiment_result.get('sentiment_score', 0),
                    'confidence': sentiment_result.get('confidence', 0),
                    'signal': sentiment_result.get('sentiment_classification', 'neutral'),
                    'details': sentiment_result.get('details', {})
                }
                successful_analyzers.append('sentiment')
                logger.debug(f"Sentiment analysis completed: {sentiment_result.get('sentiment_score', 0):.2f}")

            except Exception as e:
                logger.warning(f"Sentiment analysis failed: {str(e)}")

            # Run statistical analysis
            try:
                statistical_result = await statistical_analyzer.analyze_market_statistical(
                    market_id, market_title
                )
                individual_results['statistical'] = {
                    'score': statistical_result.get('statistical_score', 0),
                    'confidence': statistical_result.get('confidence', 0),
                    'signal': statistical_result.get('signal_classification', 'hold'),
                    'details': statistical_result.get('details', {})
                }
                successful_analyzers.append('statistical')
                logger.debug(f"Statistical analysis completed: {statistical_result.get('statistical_score', 0):.2f}")

            except Exception as e:
                logger.warning(f"Statistical analysis failed: {str(e)}")

            # Run ML models analysis (if sufficient data)
            try:
                if len(historical_data) >= 50:
                    # Train models if needed
                    training_info = await ml_models_analyzer.train_models(market_id, historical_data)

                    # Make predictions
                    ml_result = await ml_models_analyzer.predict_with_models(market_id, recent_data)
                    individual_results['ml_models'] = {
                        'score': ml_result.get('ensemble_prediction', 0),
                        'confidence': ml_result.get('confidence', 0),
                        'signal': ml_result.get('signal_classification', 'hold'),
                        'details': ml_result.get('details', {})
                    }
                    successful_analyzers.append('ml_models')
                    logger.debug(f"ML models analysis completed: {ml_result.get('ensemble_prediction', 0):.2f}")
                else:
                    logger.info(f"Insufficient data for ML models: {len(historical_data)} points")

            except Exception as e:
                logger.warning(f"ML models analysis failed: {str(e)}")

            # Check if we have any successful analyses
            if not individual_results:
                return self._empty_ensemble_result("All analyzers failed")

            # Calculate dynamic weights
            weights = self._calculate_dynamic_weights(market_category, individual_results)

            # Calculate ensemble prediction and confidence
            ensemble_prediction = self._calculate_ensemble_prediction(individual_results, weights)
            ensemble_confidence = self._calculate_ensemble_confidence(individual_results, weights)

            # Determine signal classification
            signal_classification = self._determine_signal_classification(
                ensemble_prediction, ensemble_confidence
            )

            # Calculate additional metrics
            prediction_range = {
                'min': min([r['score'] for r in individual_results.values()]),
                'max': max([r['score'] for r in individual_results.values()]),
                'spread': max([r['score'] for r in individual_results.values()]) -
                         min([r['score'] for r in individual_results.values()])
            } if len(individual_results) > 1 else {'min': 0, 'max': 0, 'spread': 0}

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            result = {
                'ensemble_prediction': ensemble_prediction,
                'confidence': ensemble_confidence,
                'signal_classification': signal_classification,
                'individual_results': individual_results,
                'dynamic_weights': weights,
                'details': {
                    'market_category': market_category,
                    'analyzers_used': successful_analyzers,
                    'analyzers_failed': list(set(['sentiment', 'statistical', 'ml_models']) - set(successful_analyzers)),
                    'data_points': len(historical_data),
                    'recent_points': len(recent_data),
                    'prediction_range': prediction_range,
                    'weight_distribution': {k: f"{v:.1%}" for k, v in weights.items()},
                    'processing_time_seconds': processing_time,
                    'market_id': market_id,
                    'market_title': market_title
                }
            }

            logger.info(f"Ensemble analysis completed: {ensemble_prediction:.2f} ({signal_classification}) with {ensemble_confidence:.1f}% confidence")
            return result

        except Exception as e:
            logger.error(f"Error in ensemble analysis: {str(e)}")
            return self._empty_ensemble_result(f"Analysis error: {str(e)}")

    def _empty_ensemble_result(self, error_message: str) -> Dict[str, Any]:
        """Return empty ensemble result with error"""
        return {
            'ensemble_prediction': 0.0,
            'confidence': 0.0,
            'signal_classification': 'error',
            'individual_results': {},
            'dynamic_weights': {},
            'details': {
                'error': error_message,
                'processing_failed': True
            }
        }

    async def update_prediction_outcome(self, market_id: str, prediction_id: str,
                                      actual_outcome: float):
        """Update actual outcomes for prediction accuracy tracking"""
        try:
            # Find the prediction in history
            if market_id in self.prediction_history:
                for prediction in self.prediction_history[market_id]:
                    if prediction.get('id') == prediction_id:
                        prediction['actual_outcome'] = actual_outcome
                        prediction['outcome_updated'] = datetime.utcnow()

                        # Update individual analyzer performance
                        for analyzer, result in prediction.get('individual_results', {}).items():
                            self._update_analyzer_performance(
                                analyzer,
                                result.get('score', 0),
                                actual_outcome,
                                result.get('confidence', 0)
                            )

                        logger.info(f"Updated outcome for prediction {prediction_id}: {actual_outcome:.2f}")
                        break

        except Exception as e:
            logger.error(f"Error updating prediction outcome: {str(e)}")

    def get_analyzer_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all analyzers"""
        try:
            metrics = {}

            for analyzer, performance in self.analyzer_performance.items():
                predictions = list(performance['predictions'])

                if predictions:
                    recent_accuracy = np.mean([p['correct'] for p in predictions[-20:]])
                    overall_accuracy = np.mean([p['correct'] for p in predictions])
                    avg_confidence = np.mean([p['confidence'] for p in predictions])

                    metrics[analyzer] = {
                        'total_predictions': len(predictions),
                        'recent_accuracy': recent_accuracy,
                        'overall_accuracy': overall_accuracy,
                        'average_confidence': avg_confidence,
                        'last_updated': performance['last_updated']
                    }
                else:
                    metrics[analyzer] = {
                        'total_predictions': 0,
                        'recent_accuracy': 0.0,
                        'overall_accuracy': 0.0,
                        'average_confidence': 0.0,
                        'last_updated': performance['last_updated']
                    }

            return metrics

        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {}

# Global ensemble analyzer instance
ensemble_analyzer = EnsembleAnalyzer()