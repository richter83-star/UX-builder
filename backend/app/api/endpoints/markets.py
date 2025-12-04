from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger

from app.core.kalshi_client import kalshi_client
from app.models.database import get_db, SessionLocal
from app.models.schemas import Market, MarketPrice, MarketAccess
from app.models.enums import MarketCategory, MarketStatus
from app.api.endpoints.auth import get_current_user
from app.models.schemas import User

router = APIRouter()

# Pydantic models
class MarketResponse(BaseModel):
    market_id: str
    title: str
    category: str
    subtitle: Optional[str] = None
    settle_date: Optional[datetime] = None
    status: str
    current_price: Optional[float] = None
    volume: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    access_status: Optional[str] = None
    can_track: bool = False

class MarketDetailResponse(MarketResponse):
    description: Optional[str] = None
    rules: Optional[str] = None
    order_book: Optional[dict] = None
    price_history: Optional[List[dict]] = None

class MarketPriceResponse(BaseModel):
    price: float
    volume: Optional[int] = None
    timestamp: datetime

class MarketHistoryResponse(BaseModel):
    market_id: str
    start_date: datetime
    end_date: datetime
    price_points: List[MarketPriceResponse]
    total_points: int

class MarketSeriesResponse(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    markets_count: int
    active_markets: int

@router.get("/", response_model=List[MarketResponse])
async def get_markets(
    category: Optional[str] = Query(None, description="Filter by market category"),
    status: Optional[str] = Query(None, description="Filter by market status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of markets to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Search term in market titles"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get list of available markets with optional filtering"""
    try:
        logger.info(f"Fetching markets - category: {category}, status: {status}, limit: {limit}")

        # Get markets from Kalshi API
        kalshi_markets = kalshi_client.get_markets(
            category=category,
            status=status,
            limit=limit,
            offset=offset
        )

        # If search term provided, filter results
        if search:
            search_lower = search.lower()
            kalshi_markets = [
                market for market in kalshi_markets
                if search_lower in market.get('title', '').lower() or
                   search_lower in market.get('subtitle', '').lower()
            ]

        # Save markets to database if not exists
        saved_markets = []
        for market_data in kalshi_markets[:limit]:
            try:
                # Check if market already exists
                existing_market = db.query(Market).filter(
                    Market.market_id == market_data['id']
                ).first()

                if not existing_market:
                    # Create new market record
                    new_market = Market(
                        market_id=market_data['id'],
                        title=market_data['title'],
                        category=market_data.get('category', 'other'),
                        subtitle=market_data.get('subtitle'),
                        settle_date=datetime.fromisoformat(market_data['resolve_time']) if market_data.get('resolve_time') else None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(new_market)
                    db.commit()
                    db.refresh(new_market)
                    existing_market = new_market
                else:
                    # Update existing market
                    existing_market.updated_at = datetime.utcnow()
                    db.commit()

                # Get current price
                try:
                    price_info = kalshi_client.get_market_price(market_data['id'])
                    current_price = float(price_info.get('price', 0))
                    volume = int(price_info.get('volume', 0))
                except Exception as e:
                    logger.warning(f"Failed to get price for market {market_data['id']}: {str(e)}")
                    current_price = None
                    volume = None

                access = db.query(MarketAccess).filter(
                    MarketAccess.user_id == current_user.id,
                    MarketAccess.market_ticker == existing_market.market_id
                ).first()

                saved_markets.append(MarketResponse(
                    market_id=existing_market.market_id,
                    title=existing_market.title,
                    category=existing_market.category,
                    subtitle=existing_market.subtitle,
                    settle_date=existing_market.settle_date,
                    status=market_data.get('status', 'unknown'),
                    current_price=current_price,
                    volume=volume,
                    created_at=existing_market.created_at,
                    updated_at=existing_market.updated_at,
                    access_status=access.status if access else None,
                    can_track=bool(access and access.status == 'active')
                ))

            except Exception as e:
                logger.error(f"Error saving market {market_data.get('id', 'unknown')}: {str(e)}")
                continue

        logger.info(f"Returned {len(saved_markets)} markets")
        return saved_markets

    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch markets"
        )

@router.get("/{market_id}", response_model=MarketDetailResponse)
async def get_market_detail(
    market_id: str,
    include_history: bool = Query(False, description="Include price history"),
    history_days: int = Query(30, ge=1, le=365, description="Days of history to include"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get detailed information for a specific market"""
    try:
        logger.info(f"Fetching market details for: {market_id}")

        # Get market from Kalshi API
        market_data = kalshi_client.get_market_details(market_id)

        # Get or create market in database
        db_market = db.query(Market).filter(Market.market_id == market_id).first()
        if not db_market:
            db_market = Market(
                market_id=market_id,
                title=market_data['title'],
                category=market_data.get('category', 'other'),
                subtitle=market_data.get('subtitle'),
                settle_date=datetime.fromisoformat(market_data['resolve_time']) if market_data.get('resolve_time') else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(db_market)
            db.commit()
            db.refresh(db_market)

        # Get current price and order book
        try:
            price_info = kalshi_client.get_market_price(market_id)
            current_price = float(price_info.get('price', 0))
            volume = int(price_info.get('volume', 0))
            order_book = price_info.get('order_book', {})
        except Exception as e:
            logger.warning(f"Failed to get price info for market {market_id}: {str(e)}")
            current_price = None
            volume = None
            order_book = {}

        # Get price history if requested
        price_history = []
        if include_history:
            try:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=history_days)

                historical_data = kalshi_client.get_market_history(
                    market_id=market_id,
                    start_date=start_date,
                    end_date=end_date
                )

                price_history = [
                    MarketPriceResponse(
                        price=float(point.get('price', 0)),
                        volume=int(point.get('volume', 0)) if point.get('volume') else None,
                        timestamp=datetime.fromisoformat(point['timestamp']) if point.get('timestamp') else datetime.utcnow()
                    )
                    for point in historical_data
                ]

                # Save to database
                for point in historical_data:
                    existing_price = db.query(MarketPrice).filter(
                        MarketPrice.market_id == market_id,
                        MarketPrice.timestamp == datetime.fromisoformat(point['timestamp'])
                    ).first()

                    if not existing_price:
                        new_price = MarketPrice(
                            market_id=market_id,
                            price=float(point.get('price', 0)),
                            volume=int(point.get('volume', 0)) if point.get('volume') else None,
                            timestamp=datetime.fromisoformat(point['timestamp'])
                        )
                        db.add(new_price)

                db.commit()

            except Exception as e:
                logger.warning(f"Failed to get price history for market {market_id}: {str(e)}")

        return MarketDetailResponse(
            market_id=db_market.market_id,
            title=db_market.title,
            category=db_market.category,
            subtitle=db_market.subtitle,
            settle_date=db_market.settle_date,
            status=market_data.get('status', 'unknown'),
            current_price=current_price,
            volume=volume,
            created_at=db_market.created_at,
            updated_at=db_market.updated_at,
            description=market_data.get('description'),
            rules=market_data.get('rules'),
            order_book=order_book,
            price_history=price_history
        )

    except Exception as e:
        logger.error(f"Error fetching market details for {market_id}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Market {market_id} not found or failed to fetch details"
        )

@router.get("/{market_id}/history", response_model=MarketHistoryResponse)
async def get_market_history(
    market_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for history"),
    end_date: Optional[datetime] = Query(None, description="End date for history"),
    interval: str = Query("1h", description="Data interval (1m, 5m, 1h, 1d)"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get historical price data for a market"""
    try:
        logger.info(f"Fetching market history for: {market_id}")

        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get historical data from Kalshi
        historical_data = kalshi_client.get_market_history(
            market_id=market_id,
            start_date=start_date,
            end_date=end_date
        )

        # Convert to response format
        price_points = [
            MarketPriceResponse(
                price=float(point.get('price', 0)),
                volume=int(point.get('volume', 0)) if point.get('volume') else None,
                timestamp=datetime.fromisoformat(point['timestamp']) if point.get('timestamp') else datetime.utcnow()
            )
            for point in historical_data
        ]

        return MarketHistoryResponse(
            market_id=market_id,
            start_date=start_date,
            end_date=end_date,
            price_points=price_points,
            total_points=len(price_points)
        )

    except Exception as e:
        logger.error(f"Error fetching market history for {market_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market history for {market_id}"
        )

@router.get("/{market_id}/price")
async def get_market_price(
    market_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get current market price and order book"""
    try:
        logger.info(f"Fetching market price for: {market_id}")

        price_info = kalshi_client.get_market_price(market_id)

        return {
            "market_id": market_id,
            "price": float(price_info.get('price', 0)),
            "volume": int(price_info.get('volume', 0)),
            "order_book": price_info.get('order_book', {}),
            "timestamp": datetime.utcnow().isoformat(),
            "bid": price_info.get('bid'),
            "ask": price_info.get('ask'),
            "bid_size": price_info.get('bid_size'),
            "ask_size": price_info.get('ask_size')
        }

    except Exception as e:
        logger.error(f"Error fetching market price for {market_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market price for {market_id}"
        )

@router.get("/series/list", response_model=List[MarketSeriesResponse])
async def get_market_series(
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user)
):
    """Get available market series"""
    try:
        logger.info("Fetching market series")

        # Get series from Kalshi API
        series_data = kalshi_client.get_market_series(category=category)

        series_list = []
        for series in series_data:
            series_list.append(MarketSeriesResponse(
                name=series.get('name', ''),
                category=series.get('category', 'other'),
                description=series.get('description'),
                markets_count=int(series.get('markets_count', 0)),
                active_markets=int(series.get('active_markets', 0))
            ))

        return series_list

    except Exception as e:
        logger.error(f"Error fetching market series: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch market series"
        )

@router.get("/categories/list")
async def get_market_categories(current_user: User = Depends(get_current_user)):
    """Get list of available market categories"""
    try:
        categories = [
            {"value": category.value, "label": category.value.title()}
            for category in MarketCategory
        ]

        return {
            "categories": categories,
            "total_categories": len(categories)
        }

    except Exception as e:
        logger.error(f"Error fetching market categories: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch market categories"
        )

@router.get("/search")
async def search_markets(
    query: str = Query(..., min_length=2, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Search markets by title or subtitle"""
    try:
        logger.info(f"Searching markets with query: {query}")

        # Get markets and filter by search term
        all_markets = kalshi_client.get_markets(category=category, limit=500)
        search_lower = query.lower()

        # Filter markets
        filtered_markets = []
        for market in all_markets:
            title = market.get('title', '').lower()
            subtitle = market.get('subtitle', '').lower()

            if search_lower in title or search_lower in subtitle:
                filtered_markets.append(market)

            if len(filtered_markets) >= limit:
                break

        # Convert to response format
        results = []
        for market_data in filtered_markets:
            try:
                # Get current price
                price_info = kalshi_client.get_market_price(market_data['id'])
                current_price = float(price_info.get('price', 0))
                volume = int(price_info.get('volume', 0))
            except:
                current_price = None
                volume = None

            results.append(MarketResponse(
                market_id=market_data['id'],
                title=market_data['title'],
                category=market_data.get('category', 'other'),
                subtitle=market_data.get('subtitle'),
                settle_date=datetime.fromisoformat(market_data['resolve_time']) if market_data.get('resolve_time') else None,
                status=market_data.get('status', 'unknown'),
                current_price=current_price,
                volume=volume,
                created_at=datetime.utcnow(),  # Would get from DB in production
                updated_at=datetime.utcnow()
            ))

        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "category_filter": category
        }

    except Exception as e:
        logger.error(f"Error searching markets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to search markets"
        )