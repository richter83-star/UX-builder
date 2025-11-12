from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from app.core.analyzers.ensemble import ensemble_analyzer
from app.core.analyzers.sentiment import sentiment_analyzer
from app.core.analyzers.statistical import statistical_analyzer
from app.core.analyzers.ml_models import ml_models_analyzer
from app.core.kalshi_client import kalshi_client
from app.models.database import get_db, SessionLocal
from app.models.schemas import Market, AnalysisResult
from app.models.enums import AnalyzerType
from app.api.endpoints.auth import get_current_user
from app.models.schemas import User

router = APIRouter()

# Pydantic models
class OpportunityResponse(BaseModel):
    market_id: str
    market_title: str
    category: str
    ensemble_prediction: float
    confidence: float
    signal_classification: str
    expected_value: float
    current_price: Optional[float] = None
    volume: Optional[int] = None
    individual_predictions: Dict[str, Dict]
    risk_score: float
    recommendation: str
    last_updated: datetime

class AnalysisRequest(BaseModel):
    market_ids: List[str] = Field(..., min_items=1, max_items=50)
    force_refresh: bool = Field(False, description="Force re-analysis even if cached results exist")

class AnalysisResponse(BaseModel):
    market_id: str
    market_title: str
    ensemble_prediction: float
    confidence: float
    signal_classification: str
    individual_results: Dict[str, Dict]
    dynamic_weights: Dict[str, float]
    analysis_timestamp: datetime
    details: Dict[str, Any]

class AnalysisSummaryResponse(BaseModel):
    total_markets_analyzed: int
    successful_analyses: int
    failed_analyses: int
    average_confidence: float
    bullish_signals: int
    bearish_signals: int
    neutral_signals: int
    top_opportunities: List[OpportunityResponse]
    analysis_time_seconds: float

class PerformanceMetricsResponse(BaseModel):
    analyzer: str
    total_predictions: int
    recent_accuracy: float
    overall_accuracy: float
    average_confidence: float
    last_updated: datetime

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Trigger new analysis for specified markets"""
    try:
        logger.info(f"Starting analysis refresh for {len(request.market_ids)} markets")

        # Validate market IDs
        valid_markets = []
        for market_id in request.market_ids:
            try:
                # Check if market exists
                market_data = kalshi_client.get_market_details(market_id)
                valid_markets.append({
                    'id': market_id,
                    'title': market_data['title'],
                    'subtitle': market_data.get('subtitle', ''),
                    'category': market_data.get('category', 'other')
                })
            except Exception as e:
                logger.warning(f"Invalid market ID {market_id}: {str(e)}")
                continue

        if not valid_markets:
            raise HTTPException(
                status_code=400,
                detail="No valid market IDs provided"
            )

        # Queue background analysis task
        background_tasks.add_task(
            _analyze_markets_background,
            valid_markets,
            request.force_refresh,
            str(current_user.id)
        )

        return {
            "message": f"Analysis queued for {len(valid_markets)} markets",
            "market_ids": [m['id'] for m in valid_markets],
            "estimated_time_minutes": len(valid_markets) * 2,  # Rough estimate
            "refresh_type": "forced" if request.force_refresh else "cached"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing analysis refresh: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to queue analysis refresh"
        )

async def _analyze_markets_background(markets: List[Dict], force_refresh: bool, user_id: str):
    """Background task to analyze markets"""
    try:
        logger.info(f"Background analysis started for {len(markets)} markets")

        for market in markets:
            try:
                # Perform ensemble analysis
                result = await ensemble_analyzer.analyze_market_ensemble(
                    market_id=market['id'],
                    market_title=market['title'],
                    market_subtitle=market['subtitle'],
                    market_category=market['category']
                )

                # Save results to database
                db = SessionLocal()
                try:
                    # Save ensemble result
                    ensemble_analysis = AnalysisResult(
                        market_id=market['id'],
                        analyzer_type='ensemble',
                        prediction=result['ensemble_prediction'],
                        confidence=result['confidence'],
                        details={
                            'signal_classification': result['signal_classification'],
                            'individual_results': result['individual_results'],
                            'dynamic_weights': result['dynamic_weights'],
                            'user_id': user_id
                        },
                        timestamp=datetime.utcnow()
                    )
                    db.add(ensemble_analysis)

                    # Save individual analyzer results
                    for analyzer_name, analyzer_result in result['individual_results'].items():
                        individual_analysis = AnalysisResult(
                            market_id=market['id'],
                            analyzer_type=analyzer_name,
                            prediction=analyzer_result['score'],
                            confidence=analyzer_result['confidence'],
                            details=analyzer_result['details'],
                            timestamp=datetime.utcnow()
                        )
                        db.add(individual_analysis)

                    db.commit()

                finally:
                    db.close()

                logger.debug(f"Analysis completed for market {market['id']}")

            except Exception as e:
                logger.error(f"Error analyzing market {market['id']}: {str(e)}")
                continue

        logger.info(f"Background analysis completed for {len(markets)} markets")

    except Exception as e:
        logger.error(f"Error in background analysis: {str(e)}")

@router.get("/opportunities", response_model=List[OpportunityResponse])
async def get_trading_opportunities(
    category: Optional[str] = Query(None, description="Filter by market category"),
    min_confidence: float = Query(60.0, ge=0, le=100, description="Minimum confidence threshold"),
    min_prediction: float = Query(10.0, ge=-100, le=100, description="Minimum prediction threshold"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of opportunities"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get ranked trading opportunities based on analysis results"""
    try:
        logger.info(f"Fetching trading opportunities - category: {category}, min_confidence: {min_confidence}")

        # Get recent analysis results from database
        recent_cutoff = datetime.utcnow() - timedelta(hours=6)  # Last 6 hours

        query = db.query(AnalysisResult).filter(
            AnalysisResult.analyzer_type == 'ensemble',
            AnalysisResult.confidence >= min_confidence,
            AnalysisResult.timestamp >= recent_cutoff
        )

        if category:
            # Join with Market table to filter by category
            query = query.join(Market).filter(Market.category == category)

        results = query.order_by(AnalysisResult.confidence.desc()).limit(limit * 2).all()  # Get more than needed for filtering

        opportunities = []
        for result in results:
            try:
                # Get market information
                market = db.query(Market).filter(Market.market_id == result.market_id).first()
                if not market:
                    continue

                # Filter by prediction threshold
                if abs(result.prediction) < min_prediction:
                    continue

                # Get current market price
                try:
                    price_info = kalshi_client.get_market_price(result.market_id)
                    current_price = float(price_info.get('price', 0))
                    volume = int(price_info.get('volume', 0))
                except:
                    current_price = None
                    volume = None

                # Calculate expected value (simplified)
                expected_value = result.prediction * 0.01 * (result.confidence / 100.0)

                # Calculate risk score
                risk_score = max(0, 100 - result.confidence + abs(result.prediction) * 0.5)

                # Generate recommendation
                if result.prediction > 15 and result.confidence > 75:
                    recommendation = "Strong Buy"
                elif result.prediction > 8 and result.confidence > 65:
                    recommendation = "Buy"
                elif result.prediction < -15 and result.confidence > 75:
                    recommendation = "Strong Sell"
                elif result.prediction < -8 and result.confidence > 65:
                    recommendation = "Sell"
                else:
                    recommendation = "Hold"

                # Get individual predictions from details
                individual_predictions = result.details.get('individual_results', {})

                opportunity = OpportunityResponse(
                    market_id=result.market_id,
                    market_title=market.title,
                    category=market.category,
                    ensemble_prediction=result.prediction,
                    confidence=result.confidence,
                    signal_classification=result.details.get('signal_classification', 'hold'),
                    expected_value=expected_value,
                    current_price=current_price,
                    volume=volume,
                    individual_predictions=individual_predictions,
                    risk_score=risk_score,
                    recommendation=recommendation,
                    last_updated=result.timestamp
                )

                opportunities.append(opportunity)

            except Exception as e:
                logger.error(f"Error processing opportunity for market {result.market_id}: {str(e)}")
                continue

        # Sort by expected value and confidence
        opportunities.sort(key=lambda x: (x.expected_value * x.confidence), reverse=True)

        return opportunities[:limit]

    except Exception as e:
        logger.error(f"Error fetching trading opportunities: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch trading opportunities"
        )

@router.get("/{market_id}", response_model=AnalysisResponse)
async def get_market_analysis(
    market_id: str,
    analyzer: Optional[str] = Query(None, description="Specific analyzer (sentiment, statistical, ml_models, ensemble)"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get analysis for a specific market"""
    try:
        logger.info(f"Fetching analysis for market {market_id}")

        # Get market information
        try:
            market_data = kalshi_client.get_market_details(market_id)
            market_title = market_data['title']
            market_subtitle = market_data.get('subtitle', '')
            market_category = market_data.get('category', 'other')
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Market {market_id} not found"
            )

        # Perform analysis
        if analyzer == 'sentiment':
            result = await sentiment_analyzer.analyze_market_sentiment(market_title, market_subtitle, market_category)
            # Format response
            analysis_data = {
                'market_id': market_id,
                'market_title': market_title,
                'sentiment_score': result['sentiment_score'],
                'confidence': result['confidence'],
                'signal_classification': result['sentiment_classification'],
                'individual_results': {'sentiment': result},
                'dynamic_weights': {'sentiment': 1.0},
                'analysis_timestamp': datetime.utcnow(),
                'details': result['details']
            }
        elif analyzer == 'statistical':
            result = await statistical_analyzer.analyze_market_statistical(market_id, market_title)
            analysis_data = {
                'market_id': market_id,
                'market_title': market_title,
                'statistical_score': result['statistical_score'],
                'confidence': result['confidence'],
                'signal_classification': result['signal_classification'],
                'individual_results': {'statistical': result},
                'dynamic_weights': {'statistical': 1.0},
                'analysis_timestamp': datetime.utcnow(),
                'details': result['details']
            }
        elif analyzer == 'ml_models':
            # Get historical data for ML models
            historical_data = kalshi_client.get_market_history(market_id)
            if len(historical_data) >= 50:
                result = await ml_models_analyzer.predict_with_models(market_id, historical_data[-30:])
                analysis_data = {
                    'market_id': market_id,
                    'market_title': market_title,
                    'ensemble_prediction': result['ensemble_prediction'],
                    'confidence': result['confidence'],
                    'signal_classification': result['signal_classification'],
                    'individual_results': result['individual_predictions'],
                    'dynamic_weights': result.get('details', {}).get('model_weights', {}),
                    'analysis_timestamp': datetime.utcnow(),
                    'details': result['details']
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Insufficient historical data for ML analysis"
                )
        else:
            # Default to ensemble analysis
            result = await ensemble_analyzer.analyze_market_ensemble(
                market_id, market_title, market_subtitle, market_category
            )
            analysis_data = {
                'market_id': market_id,
                'market_title': market_title,
                'ensemble_prediction': result['ensemble_prediction'],
                'confidence': result['confidence'],
                'signal_classification': result['signal_classification'],
                'individual_results': result['individual_results'],
                'dynamic_weights': result['dynamic_weights'],
                'analysis_timestamp': datetime.utcnow(),
                'details': result['details']
            }

        # Save analysis to database
        try:
            analysis_record = AnalysisResult(
                market_id=market_id,
                analyzer_type=analyzer or 'ensemble',
                prediction=analysis_data.get('ensemble_prediction') or analysis_data.get('sentiment_score') or analysis_data.get('statistical_score', 0),
                confidence=analysis_data['confidence'],
                details=analysis_data,
                timestamp=datetime.utcnow()
            )
            db.add(analysis_record)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to save analysis to database: {str(e)}")

        return AnalysisResponse(**analysis_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analysis for market {market_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch analysis for market {market_id}"
        )

@router.get("/summary/recent", response_model=AnalysisSummaryResponse)
async def get_recent_analysis_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get summary of recent analysis results"""
    try:
        logger.info(f"Fetching analysis summary for last {hours} hours")

        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Get recent ensemble analyses
        query = db.query(AnalysisResult).filter(
            AnalysisResult.analyzer_type == 'ensemble',
            AnalysisResult.timestamp >= start_time
        )

        if category:
            query = query.join(Market).filter(Market.category == category)

        analyses = query.all()

        if not analyses:
            return AnalysisSummaryResponse(
                total_markets_analyzed=0,
                successful_analyses=0,
                failed_analyses=0,
                average_confidence=0.0,
                bullish_signals=0,
                bearish_signals=0,
                neutral_signals=0,
                top_opportunities=[],
                analysis_time_seconds=0.0
            )

        # Calculate summary metrics
        successful_analyses = len([a for a in analyses if a.confidence > 0])
        failed_analyses = len(analyses) - successful_analyses
        avg_confidence = sum(a.confidence for a in analyses) / len(analyses)

        # Count signals
        bullish_signals = len([a for a in analyses if a.prediction > 5])
        bearish_signals = len([a for a in analyses if a.prediction < -5])
        neutral_signals = len(analyses) - bullish_signals - bearish_signals

        # Get top opportunities
        top_analyses = sorted(analyses, key=lambda x: x.confidence * abs(x.prediction), reverse=True)[:5]

        top_opportunities = []
        for analysis in top_analyses:
            try:
                market = db.query(Market).filter(Market.market_id == analysis.market_id).first()
                if market:
                    expected_value = analysis.prediction * 0.01 * (analysis.confidence / 100.0)

                    opportunity = OpportunityResponse(
                        market_id=analysis.market_id,
                        market_title=market.title,
                        category=market.category,
                        ensemble_prediction=analysis.prediction,
                        confidence=analysis.confidence,
                        signal_classification=analysis.details.get('signal_classification', 'hold'),
                        expected_value=expected_value,
                        individual_predictions=analysis.details.get('individual_results', {}),
                        risk_score=max(0, 100 - analysis.confidence + abs(analysis.prediction) * 0.5),
                        recommendation="Analyze" if abs(analysis.prediction) > 10 else "Hold",
                        last_updated=analysis.timestamp
                    )
                    top_opportunities.append(opportunity)
            except Exception as e:
                logger.error(f"Error processing top opportunity: {str(e)}")
                continue

        return AnalysisSummaryResponse(
            total_markets_analyzed=len(analyses),
            successful_analyses=successful_analyses,
            failed_analyses=failed_analyses,
            average_confidence=avg_confidence,
            bullish_signals=bullish_signals,
            bearish_signals=bearish_signals,
            neutral_signals=neutral_signals,
            top_opportunities=top_opportunities,
            analysis_time_seconds=0.0  # Would track actual analysis time
        )

    except Exception as e:
        logger.error(f"Error fetching analysis summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch analysis summary"
        )

@router.get("/performance/metrics", response_model=List[PerformanceMetricsResponse])
async def get_analyzer_performance(
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for all analyzers"""
    try:
        logger.info("Fetching analyzer performance metrics")

        # Get performance metrics from ensemble analyzer
        metrics = ensemble_analyzer.get_analyzer_performance_metrics()

        performance_responses = []
        for analyzer_name, metric_data in metrics.items():
            performance_responses.append(PerformanceMetricsResponse(
                analyzer=analyzer_name,
                total_predictions=metric_data['total_predictions'],
                recent_accuracy=metric_data['recent_accuracy'],
                overall_accuracy=metric_data['overall_accuracy'],
                average_confidence=metric_data['average_confidence'],
                last_updated=metric_data['last_updated']
            ))

        return performance_responses

    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch performance metrics"
        )

@router.delete("/cache")
async def clear_analysis_cache(
    market_id: Optional[str] = Query(None, description="Specific market ID to clear, or all if not provided"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Clear analysis cache for specific market or all markets"""
    try:
        if market_id:
            # Clear cache for specific market
            deleted_count = db.query(AnalysisResult).filter(
                AnalysisResult.market_id == market_id
            ).delete()
            message = f"Cleared cache for market {market_id}"
        else:
            # Clear all cache (older than 24 hours)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            deleted_count = db.query(AnalysisResult).filter(
                AnalysisResult.timestamp < cutoff
            ).delete()
            message = f"Cleared {deleted_count} old analysis records"

        db.commit()

        logger.info(f"Cache cleared: {message}")

        return {
            "message": message,
            "deleted_records": deleted_count
        }

    except Exception as e:
        logger.error(f"Error clearing analysis cache: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to clear analysis cache"
        )