from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from app.core.portfolio import portfolio_manager, TradeExecution
from app.core.risk_manager import risk_manager, TradeRiskAssessment
from app.core.kalshi_client import kalshi_client
from app.models.database import get_db, SessionLocal
from app.models.schemas import Trade, Position, Market
from app.models.enums import TradeSide, TradeStatus
from app.api.endpoints.auth import get_current_user
from app.models.schemas import User

router = APIRouter()

# Pydantic models
class OrderRequest(BaseModel):
    market_id: str = Field(..., description="Market ID to trade")
    side: TradeSide = Field(..., description="Trade side: 'yes' or 'no'")
    count: int = Field(..., gt=0, le=10000, description="Number of contracts")
    price: Optional[float] = Field(None, ge=0, le=1, description="Price per contract (uses market price if not specified)")
    expected_return: Optional[float] = Field(0, description="Expected return percentage for risk assessment")
    win_probability: Optional[float] = Field(0.5, ge=0, le=1, description="Win probability for risk assessment")

class OrderResponse(BaseModel):
    order_id: str
    market_id: str
    side: str
    count: int
    price: float
    status: str
    executed_at: datetime
    fees: float
    risk_assessment: Optional[Dict[str, Any]] = None
    message: str

class PositionResponse(BaseModel):
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
    created_at: datetime
    updated_at: datetime

class TradeResponse(BaseModel):
    trade_id: str
    market_id: str
    market_title: str
    side: str
    count: int
    price: float
    status: str
    filled_at: Optional[datetime] = None
    created_at: datetime
    fees: float
    realized_pnl: Optional[float] = None

class RiskAssessmentRequest(BaseModel):
    market_id: str
    side: TradeSide
    count: int
    price: Optional[float] = None
    expected_return: Optional[float] = 0
    win_probability: Optional[float] = 0.5

class RiskAssessmentResponse(BaseModel):
    approved: bool
    risk_level: str
    risk_score: float
    position_size: float
    max_loss: float
    risk_checks: List[Dict[str, Any]]
    recommendations: List[str]
    user_risk_profile: str

@router.post("/orders", response_model=OrderResponse)
async def place_order(
    order: OrderRequest,
    background_tasks: BackgroundTasks,
    auto_risk_check: bool = Query(True, description="Perform automatic risk assessment"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Place a new trading order with optional risk assessment"""
    try:
        logger.info(f"Placing order: {order.side} {order.count} contracts for market {order.market_id}")

        # Validate market exists
        try:
            market_data = kalshi_client.get_market_details(order.market_id)
            market_title = market_data['title']
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Market {order.market_id} not found or unavailable"
            )

        # Get current price if not specified
        if order.price is None:
            try:
                price_info = kalshi_client.get_market_price(order.market_id)
                order.price = float(price_info.get('price', 0.5))
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get market price"
                )

        # Calculate trade size
        trade_size = order.count * order.price

        # Perform risk assessment if requested
        risk_assessment = None
        if auto_risk_check:
            try:
                risk_assessment_result = risk_manager.assess_trade_risk(
                    market_id=order.market_id,
                    side=order.side,
                    count=order.count,
                    price=order.price,
                    expected_return=order.expected_return,
                    win_probability=order.win_probability,
                    user_risk_profile=current_user.risk_profile
                )

                # Convert to dict for response
                risk_assessment = {
                    'approved': risk_assessment_result.approved,
                    'risk_level': risk_assessment_result.risk_level.value,
                    'risk_score': risk_assessment_result.risk_score,
                    'position_size': risk_assessment_result.position_size,
                    'max_loss': risk_assessment_result.max_loss,
                    'risk_checks': [
                        {
                            'passed': check.passed,
                            'level': check.level.value,
                            'message': check.message,
                            'details': check.details
                        }
                        for check in risk_assessment_result.risk_checks
                    ],
                    'recommendations': risk_assessment_result.recommendations
                }

                # Check if trade is approved by risk manager
                if not risk_assessment_result.approved:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "Trade rejected by risk management",
                            "risk_assessment": risk_assessment
                        }
                    )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Risk assessment failed: {str(e)}")
                # Continue with trade if risk assessment fails, but log warning
                logger.warning("Proceeding with trade without risk assessment")

        # Execute the trade
        trade_execution = await portfolio_manager.execute_trade(
            market_id=order.market_id,
            side=order.side,
            count=order.count,
            price=order.price
        )

        if not trade_execution:
            raise HTTPException(
                status_code=500,
                detail="Failed to execute trade"
            )

        # Save trade to database
        try:
            new_trade = Trade(
                market_id=order.market_id,
                side=order.side,
                count=order.count,
                price=order.price,
                status=TradeStatus.PENDING,  # Will be updated by background task
                created_at=trade_execution.executed_at
            )
            db.add(new_trade)
            db.commit()
            db.refresh(new_trade)

            # Update trade execution with database ID
            trade_execution.trade_id = str(new_trade.id)

        except Exception as e:
            logger.error(f"Failed to save trade to database: {str(e)}")
            # Continue anyway as trade was executed

        # Queue background task to monitor trade status
        background_tasks.add_task(
            _monitor_trade_status,
            str(new_trade.id) if 'new_trade' in locals() else trade_execution.trade_id,
            order.market_id
        )

        # Update risk manager
        risk_manager.update_daily_pnl(-trade_execution.fees)  # Fees are immediate cost
        risk_manager.increment_daily_trades()

        logger.info(f"Order placed successfully: {trade_execution.trade_id}")

        return OrderResponse(
            order_id=trade_execution.trade_id,
            market_id=order.market_id,
            side=order.side,
            count=order.count,
            price=order.price,
            status=trade_execution.status,
            executed_at=trade_execution.executed_at,
            fees=trade_execution.fees,
            risk_assessment=risk_assessment,
            message="Order placed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to place order: {str(e)}"
        )

async def _monitor_trade_status(trade_id: str, market_id: str):
    """Background task to monitor trade status and create position"""
    try:
        logger.info(f"Monitoring trade status for {trade_id}")

        # In a real implementation, you would poll the Kalshi API for trade status
        # For now, we'll simulate the trade being filled after a short delay

        await asyncio.sleep(5)  # Simulate processing time

        db = SessionLocal()
        try:
            # Update trade status
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.status = TradeStatus.FILLED
                trade.filled_at = datetime.utcnow()
                db.commit()

                # Create position record
                new_position = Position(
                    trade_id=trade_id,
                    current_value=trade.count * trade.price,
                    unrealized_pnl=0.0,
                    updated_at=datetime.utcnow()
                )
                db.add(new_position)
                db.commit()

                logger.info(f"Trade {trade_id} filled and position created")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error monitoring trade status for {trade_id}: {str(e)}")

@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    market_id: Optional[str] = Query(None, description="Filter by specific market"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(50, ge=1, le=500, description="Maximum positions to return"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get current open positions"""
    try:
        logger.info("Fetching current positions")

        # Update positions with latest market data
        await portfolio_manager.update_positions()

        # Get positions from portfolio manager
        position_summaries = await portfolio_manager.get_position_summaries()

        # Apply filters
        filtered_positions = position_summaries

        if market_id:
            filtered_positions = [p for p in filtered_positions if p.market_id == market_id]

        if risk_level:
            filtered_positions = [p for p in filtered_positions if p.risk_level == risk_level]

        # Apply limit
        filtered_positions = filtered_positions[:limit]

        # Convert to response format
        positions_response = []
        for position in filtered_positions:
            try:
                # Get created_at from database
                db_position = db.query(Position).filter(
                    Position.id == position.position_id
                ).first()

                positions_response.append(PositionResponse(
                    position_id=position.position_id,
                    market_id=position.market_id,
                    market_title=position.market_title,
                    side=position.side,
                    count=position.count,
                    entry_price=position.entry_price,
                    current_price=position.current_price,
                    current_value=position.current_value,
                    unrealized_pnl=position.unrealized_pnl,
                    unrealized_pnl_percent=position.unrealized_pnl_percent,
                    duration_hours=position.duration_hours,
                    risk_level=position.risk_level,
                    created_at=db_position.trade.created_at if db_position else datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ))

            except Exception as e:
                logger.error(f"Error processing position {position.position_id}: {str(e)}")
                continue

        return positions_response

    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch positions"
        )

@router.get("/positions/{position_id}", response_model=PositionResponse)
async def get_position_detail(
    position_id: str,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get detailed information for a specific position"""
    try:
        logger.info(f"Fetching position detail for {position_id}")

        # Update positions to get latest data
        await portfolio_manager.update_positions()

        # Get position from portfolio manager
        position_summaries = await portfolio_manager.get_position_summaries()
        position = next((p for p in position_summaries if p.position_id == position_id), None)

        if not position:
            raise HTTPException(
                status_code=404,
                detail=f"Position {position_id} not found"
            )

        # Get additional details from database
        db_position = db.query(Position).filter(Position.id == position_id).first()

        return PositionResponse(
            position_id=position.position_id,
            market_id=position.market_id,
            market_title=position.market_title,
            side=position.side,
            count=position.count,
            entry_price=position.entry_price,
            current_price=position.current_price,
            current_value=position.current_value,
            unrealized_pnl=position.unrealized_pnl,
            unrealized_pnl_percent=position.unrealized_pnl_percent,
            duration_hours=position.duration_hours,
            risk_level=position.risk_level,
            created_at=db_position.trade.created_at if db_position else datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching position detail for {position_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch position detail"
        )

@router.post("/positions/{position_id}/close")
async def close_position(
    position_id: str,
    reason: str = Query("manual", description="Reason for closing position"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Close a specific position"""
    try:
        logger.info(f"Closing position {position_id}: {reason}")

        # Close position through portfolio manager
        close_result = await portfolio_manager.close_position(position_id, reason)

        if not close_result:
            raise HTTPException(
                status_code=404,
                detail=f"Position {position_id} not found or could not be closed"
            )

        # Update position in database
        position = db.query(Position).filter(Position.id == position_id).first()
        if position:
            # Mark position as closed (simplified - would track closing trade properly)
            position.updated_at = datetime.utcnow()
            db.commit()

        return {
            "message": f"Position {position_id} closed successfully",
            "position_id": position_id,
            "close_result": close_result,
            "reason": reason,
            "closed_at": datetime.utcnow()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing position {position_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to close position: {str(e)}"
        )

@router.get("/history", response_model=List[TradeResponse])
async def get_trade_history(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    status: Optional[str] = Query(None, description="Filter by trade status"),
    market_id: Optional[str] = Query(None, description="Filter by market"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum trades to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get trading history"""
    try:
        logger.info(f"Fetching trade history - limit: {limit}, offset: {offset}")

        # Build query
        query = db.query(Trade).join(Market)

        if start_date:
            query = query.filter(Trade.created_at >= start_date)
        if end_date:
            query = query.filter(Trade.created_at <= end_date)
        if status:
            query = query.filter(Trade.status == status)
        if market_id:
            query = query.filter(Trade.market_id == market_id)

        # Order by creation date (newest first) and apply pagination
        trades = query.order_by(Trade.created_at.desc()).offset(offset).limit(limit).all()

        # Convert to response format
        trade_responses = []
        for trade in trades:
            # Calculate realized P&L for closed positions
            realized_pnl = None
            if trade.status == TradeStatus.FILLED:
                try:
                    position = db.query(Position).filter(Position.trade_id == trade.id).first()
                    if position and position.unrealized_pnl is not None:
                        # This is simplified - proper P&L calculation would consider closing price
                        realized_pnl = position.unrealized_pnl
                except:
                    pass

            trade_responses.append(TradeResponse(
                trade_id=str(trade.id),
                market_id=trade.market_id,
                market_title=trade.market.title if trade.market else "Unknown Market",
                side=trade.side,
                count=trade.count,
                price=float(trade.price),
                status=trade.status,
                filled_at=trade.filled_at,
                created_at=trade.created_at,
                fees=0.0,  # Would track actual fees
                realized_pnl=realized_pnl
            ))

        return trade_responses

    except Exception as e:
        logger.error(f"Error fetching trade history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch trade history"
        )

@router.get("/portfolio/metrics")
async def get_portfolio_metrics(current_user: User = Depends(get_current_user)):
    """Get comprehensive portfolio performance metrics"""
    try:
        logger.info("Fetching portfolio metrics")

        metrics = await portfolio_manager.get_portfolio_metrics()

        return {
            "total_value": metrics.total_value,
            "cash_balance": metrics.cash_balance,
            "positions_value": metrics.positions_value,
            "total_pnl": metrics.total_pnl,
            "total_pnl_percent": metrics.total_pnl_percent,
            "daily_pnl": metrics.daily_pnl,
            "daily_pnl_percent": metrics.daily_pnl_percent,
            "number_of_positions": metrics.number_of_positions,
            "number_of_winning_positions": metrics.number_of_winning_positions,
            "number_of_losing_positions": metrics.number_of_losing_positions,
            "win_rate": metrics.win_rate,
            "max_drawdown": metrics.max_drawdown,
            "sharpe_ratio": metrics.sharpe_ratio,
            "average_position_size": metrics.average_position_size,
            "last_updated": datetime.utcnow()
        }

    except Exception as e:
        logger.error(f"Error fetching portfolio metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch portfolio metrics"
        )

@router.get("/portfolio/performance")
async def get_portfolio_performance(
    days: int = Query(30, ge=1, le=365, description="Days of performance data"),
    current_user: User = Depends(get_current_user)
):
    """Get portfolio performance over specified period"""
    try:
        logger.info(f"Fetching portfolio performance for last {days} days")

        performance = await portfolio_manager.get_portfolio_performance(days)

        return performance

    except Exception as e:
        logger.error(f"Error fetching portfolio performance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch portfolio performance"
        )

@router.get("/portfolio/allocation")
async def get_portfolio_allocation(current_user: User = Depends(get_current_user)):
    """Get portfolio allocation by market category"""
    try:
        logger.info("Fetching portfolio allocation")

        allocation = portfolio_manager.get_portfolio_allocation()

        return allocation

    except Exception as e:
        logger.error(f"Error fetching portfolio allocation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch portfolio allocation"
        )

@router.post("/risk/assess", response_model=RiskAssessmentResponse)
async def assess_trade_risk(
    request: RiskAssessmentRequest,
    current_user: User = Depends(get_current_user)
):
    """Perform risk assessment for a potential trade without executing it"""
    try:
        logger.info(f"Performing risk assessment for market {request.market_id}")

        # Get current price if not specified
        if request.price is None:
            try:
                price_info = kalshi_client.get_market_price(request.market_id)
                request.price = float(price_info.get('price', 0.5))
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get market price"
                )

        # Perform risk assessment
        risk_assessment = risk_manager.assess_trade_risk(
            market_id=request.market_id,
            side=request.side,
            count=request.count,
            price=request.price,
            expected_return=request.expected_return,
            win_probability=request.win_probability,
            user_risk_profile=current_user.risk_profile
        )

        return RiskAssessmentResponse(
            approved=risk_assessment.approved,
            risk_level=risk_assessment.risk_level.value,
            risk_score=risk_assessment.risk_score,
            position_size=risk_assessment.position_size,
            max_loss=risk_assessment.max_loss,
            risk_checks=[
                {
                    'passed': check.passed,
                    'level': check.level.value,
                    'message': check.message,
                    'details': check.details
                }
                for check in risk_assessment.risk_checks
            ],
            recommendations=risk_assessment.recommendations,
            user_risk_profile=current_user.risk_profile
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing risk assessment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to perform risk assessment"
        )

@router.get("/risk/metrics")
async def get_risk_metrics(current_user: User = Depends(get_current_user)):
    """Get current risk management metrics"""
    try:
        logger.info("Fetching risk metrics")

        metrics = risk_manager.get_risk_metrics()

        return metrics

    except Exception as e:
        logger.error(f"Error fetching risk metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch risk metrics"
        )

@router.post("/risk/emergency-stop")
async def toggle_emergency_stop(
    active: bool = Query(..., description="Activate or deactivate emergency stop"),
    reason: str = Query("", description="Reason for emergency stop"),
    current_user: User = Depends(get_current_user)
):
    """Toggle emergency stop to halt all automated trading"""
    try:
        logger.info(f"Emergency stop toggle: {active} - {reason}")

        risk_manager.set_emergency_stop(active, reason)

        return {
            "message": f"Emergency stop {'activated' if active else 'deactivated'}",
            "active": active,
            "reason": reason,
            "timestamp": datetime.utcnow()
        }

    except Exception as e:
        logger.error(f"Error toggling emergency stop: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to toggle emergency stop"
        )