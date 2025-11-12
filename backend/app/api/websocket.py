from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Dict, List, Optional, Any, Set
import json
import asyncio
from datetime import datetime, timedelta
import uuid
from collections import defaultdict
from loguru import logger

from app.core.kalshi_client import kalshi_client
from app.core.portfolio import portfolio_manager
from app.core.risk_manager import risk_manager
from app.models.database import SessionLocal
from app.models.schemas import Market, Position, Trade
from app.models.enums import WebSocketEvent
from app.api.endpoints.auth import get_current_user_ws

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""

    def __init__(self):
        # Active connections by user
        self.active_connections: Dict[str, WebSocket] = {}
        # User subscriptions
        self.user_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        # Market subscriptions (for broadcasting to interested users)
        self.market_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        # Connection metadata
        self.connection_metadata: Dict[str, Dict] = {}
        # Last heartbeat times
        self.last_heartbeat: Dict[str, datetime] = {}

    async def connect(self, websocket: WebSocket, user_id: str, token: str):
        """Accept WebSocket connection and register user"""
        try:
            await websocket.accept()

            # Store connection
            self.active_connections[user_id] = websocket
            self.user_subscriptions[user_id] = set()
            self.connection_metadata[user_id] = {
                'connected_at': datetime.utcnow(),
                'token': token,
                'last_activity': datetime.utcnow()
            }
            self.last_heartbeat[user_id] = datetime.utcnow()

            logger.info(f"WebSocket connected for user {user_id}")

            # Send welcome message
            await self.send_personal_message(user_id, {
                'type': WebSocketEvent.CONNECTION_STATUS.value,
                'data': {
                    'status': 'connected',
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
            })

        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {str(e)}")
            await websocket.close(code=1000)

    def disconnect(self, user_id: str):
        """Remove WebSocket connection"""
        try:
            # Remove from all subscriptions
            if user_id in self.user_subscriptions:
                for market_id in self.user_subscriptions[user_id]:
                    if user_id in self.market_subscriptions[market_id]:
                        self.market_subscriptions[market_id].remove(user_id)

            # Clean up connection data
            self.active_connections.pop(user_id, None)
            self.user_subscriptions.pop(user_id, None)
            self.connection_metadata.pop(user_id, None)
            self.last_heartbeat.pop(user_id, None)

            logger.info(f"WebSocket disconnected for user {user_id}")

        except Exception as e:
            logger.error(f"Error cleaning up WebSocket connection: {str(e)}")

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_text(json.dumps(message))
                self.connection_metadata[user_id]['last_activity'] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error sending personal message to {user_id}: {str(e)}")
                # Connection might be dead, remove it
                self.disconnect(user_id)

    async def broadcast_to_market(self, market_id: str, message: Dict[str, Any]):
        """Broadcast message to all users subscribed to a market"""
        if market_id in self.market_subscriptions:
            disconnected_users = []

            for user_id in self.market_subscriptions[market_id].copy():
                if user_id in self.active_connections:
                    try:
                        websocket = self.active_connections[user_id]
                        await websocket.send_text(json.dumps(message))
                        self.connection_metadata[user_id]['last_activity'] = datetime.utcnow()
                    except Exception as e:
                        logger.error(f"Error broadcasting to user {user_id}: {str(e)}")
                        disconnected_users.append(user_id)
                else:
                    disconnected_users.append(user_id)

            # Clean up disconnected users
            for user_id in disconnected_users:
                self.disconnect(user_id)

    async def subscribe_to_market(self, user_id: str, market_id: str):
        """Subscribe user to market updates"""
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].add(market_id)
            self.market_subscriptions[market_id].add(user_id)

            # Send current market data
            try:
                price_info = kalshi_client.get_market_price(market_id)
                await self.send_personal_message(user_id, {
                    'type': WebSocketEvent.MARKET_UPDATE.value,
                    'data': {
                        'market_id': market_id,
                        'price': price_info.get('price'),
                        'volume': price_info.get('volume'),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to send initial market data for {market_id}: {str(e)}")

    async def unsubscribe_from_market(self, user_id: str, market_id: str):
        """Unsubscribe user from market updates"""
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(market_id)

        if market_id in self.market_subscriptions:
            self.market_subscriptions[market_id].discard(user_id)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            'active_connections': len(self.active_connections),
            'total_subscriptions': sum(len(subs) for subs in self.user_subscriptions.values()),
            'markets_with_subscribers': len(self.market_subscriptions),
            'connections_by_age': {
                user_id: (datetime.utcnow() - metadata['connected_at']).total_seconds()
                for user_id, metadata in self.connection_metadata.items()
            }
        }

    async def heartbeat_check(self):
        """Check for dead connections and remove them"""
        try:
            current_time = datetime.utcnow()
            dead_connections = []

            for user_id, last_beat in self.last_heartbeat.items():
                if (current_time - last_beat).total_seconds() > 90:  # 90 second timeout
                    dead_connections.append(user_id)

            for user_id in dead_connections:
                logger.info(f"Removing dead connection: {user_id}")
                self.disconnect(user_id)

            if dead_connections:
                logger.info(f"Cleaned up {len(dead_connections)} dead connections")

        except Exception as e:
            logger.error(f"Error in heartbeat check: {str(e)}")

# Global connection manager
manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
    user_id: Optional[str] = Query(None, description="User ID")
):
    """Main WebSocket endpoint for real-time updates"""

    # Authenticate user (simplified - in production, validate JWT token)
    if not user_id:
        await websocket.close(code=4001, reason="User ID required")
        return

    try:
        # Establish connection
        await manager.connect(websocket, user_id, token)

        # Start background tasks
        heartbeat_task = asyncio.create_task(send_heartbeat(user_id))
        receive_task = asyncio.create_task(receive_messages(user_id))

        # Wait for tasks to complete
        done, pending = await asyncio.wait(
            [heartbeat_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
    finally:
        manager.disconnect(user_id)

async def send_heartbeat(user_id: str):
    """Send periodic heartbeat messages"""
    try:
        while True:
            await asyncio.sleep(30)  # 30 second intervals

            # Send ping
            await manager.send_personal_message(user_id, {
                'type': 'ping',
                'timestamp': datetime.utcnow().isoformat()
            })

            # Update heartbeat timestamp
            manager.last_heartbeat[user_id] = datetime.utcnow()

    except Exception as e:
        logger.error(f"Error in heartbeat for {user_id}: {str(e)}")

async def receive_messages(user_id: str):
    """Receive and handle messages from client"""
    try:
        websocket = manager.active_connections[user_id]

        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)

            # Update activity timestamp
            manager.connection_metadata[user_id]['last_activity'] = datetime.utcnow()

            # Handle message
            await handle_client_message(user_id, message)

    except WebSocketDisconnect:
        logger.info(f"Client {user_id} disconnected")
    except Exception as e:
        logger.error(f"Error receiving message from {user_id}: {str(e)}")

async def handle_client_message(user_id: str, message: Dict[str, Any]):
    """Handle incoming messages from clients"""
    try:
        message_type = message.get('type')
        data = message.get('data', {})

        if message_type == 'pong':
            # Respond to ping
            manager.last_heartbeat[user_id] = datetime.utcnow()

        elif message_type == 'subscribe':
            # Subscribe to market updates
            market_id = data.get('market_id')
            if market_id:
                await manager.subscribe_to_market(user_id, market_id)
                await manager.send_personal_message(user_id, {
                    'type': 'subscription_confirmed',
                    'data': {
                        'market_id': market_id,
                        'action': 'subscribed',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                })

        elif message_type == 'unsubscribe':
            # Unsubscribe from market updates
            market_id = data.get('market_id')
            if market_id:
                await manager.unsubscribe_from_market(user_id, market_id)
                await manager.send_personal_message(user_id, {
                    'type': 'subscription_confirmed',
                    'data': {
                        'market_id': market_id,
                        'action': 'unsubscribed',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                })

        elif message_type == 'get_portfolio':
            # Send current portfolio status
            try:
                metrics = await portfolio_manager.get_portfolio_metrics()
                await manager.send_personal_message(user_id, {
                    'type': WebSocketEvent.POSITION_UPDATE.value,
                    'data': {
                        'portfolio_metrics': {
                            'total_value': metrics.total_value,
                            'daily_pnl': metrics.daily_pnl,
                            'win_rate': metrics.win_rate,
                            'number_of_positions': metrics.number_of_positions
                        },
                        'timestamp': datetime.utcnow().isoformat()
                    }
                })
            except Exception as e:
                logger.error(f"Error sending portfolio data: {str(e)}")

        elif message_type == 'get_risk_metrics':
            # Send current risk metrics
            try:
                risk_metrics = risk_manager.get_risk_metrics()
                await manager.send_personal_message(user_id, {
                    'type': WebSocketEvent.RISK_ALERT.value,
                    'data': {
                        'risk_metrics': risk_metrics,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                })
            except Exception as e:
                logger.error(f"Error sending risk metrics: {str(e)}")

        else:
            logger.warning(f"Unknown message type from client {user_id}: {message_type}")

    except Exception as e:
        logger.error(f"Error handling client message: {str(e)}")

# Background tasks for real-time data updates

async def start_background_tasks():
    """Start background tasks for real-time data updates"""
    try:
        # Start market data updates
        asyncio.create_task(market_data_updater())

        # Start portfolio updates
        asyncio.create_task(portfolio_updater())

        # Start risk monitoring
        asyncio.create_task(risk_monitor())

        # Start heartbeat checker
        asyncio.create_task(heartbeat_checker())

        logger.info("Background WebSocket tasks started")

    except Exception as e:
        logger.error(f"Error starting background tasks: {str(e)}")

async def market_data_updater():
    """Periodically update market data and broadcast to subscribers"""
    while True:
        try:
            await asyncio.sleep(60)  # Update every minute

            # Get markets with active subscribers
            markets_to_update = list(manager.market_subscriptions.keys())[:20]  # Limit to 20 markets

            for market_id in markets_to_update:
                try:
                    # Get current market data
                    price_info = kalshi_client.get_market_price(market_id)

                    # Broadcast to subscribers
                    await manager.broadcast_to_market(market_id, {
                        'type': WebSocketEvent.MARKET_UPDATE.value,
                        'data': {
                            'market_id': market_id,
                            'price': price_info.get('price'),
                            'volume': price_info.get('volume'),
                            'bid': price_info.get('bid'),
                            'ask': price_info.get('ask'),
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    })

                except Exception as e:
                    logger.warning(f"Error updating market {market_id}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error in market data updater: {str(e)}")
            await asyncio.sleep(60)  # Wait before retrying

async def portfolio_updater():
    """Periodically update portfolio data and broadcast to all users"""
    while True:
        try:
            await asyncio.sleep(300)  # Update every 5 minutes

            if manager.active_connections:
                try:
                    # Get portfolio metrics
                    metrics = await portfolio_manager.get_portfolio_metrics()

                    # Get position summaries
                    positions = await portfolio_manager.get_position_summaries()

                    # Broadcast to all connected users
                    message = {
                        'type': WebSocketEvent.POSITION_UPDATE.value,
                        'data': {
                            'portfolio_metrics': {
                                'total_value': metrics.total_value,
                                'cash_balance': metrics.cash_balance,
                                'positions_value': metrics.positions_value,
                                'daily_pnl': metrics.daily_pnl,
                                'daily_pnl_percent': metrics.daily_pnl_percent,
                                'win_rate': metrics.win_rate,
                                'number_of_positions': metrics.number_of_positions,
                                'max_drawdown': metrics.max_drawdown
                            },
                            'positions': [
                                {
                                    'position_id': pos.position_id,
                                    'market_id': pos.market_id,
                                    'market_title': pos.market_title,
                                    'unrealized_pnl': pos.unrealized_pnl,
                                    'unrealized_pnl_percent': pos.unrealized_pnl_percent,
                                    'risk_level': pos.risk_level
                                }
                                for pos in positions[:10]  # Send top 10 positions
                            ],
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    }

                    for user_id in manager.active_connections:
                        await manager.send_personal_message(user_id, message)

                except Exception as e:
                    logger.error(f"Error updating portfolio data: {str(e)}")

        except Exception as e:
            logger.error(f"Error in portfolio updater: {str(e)}")
            await asyncio.sleep(300)

async def risk_monitor():
    """Monitor risk metrics and send alerts"""
    while True:
        try:
            await asyncio.sleep(180)  # Check every 3 minutes

            if manager.active_connections:
                try:
                    # Get risk metrics
                    risk_metrics = risk_manager.get_risk_metrics()

                    # Check for risk alerts
                    alerts = []

                    if risk_metrics.get('current_drawdown', 0) > 10:
                        alerts.append({
                            'type': 'drawdown_warning',
                            'message': f"Portfolio drawdown: {risk_metrics['current_drawdown']:.1f}%",
                            'severity': 'high' if risk_metrics['current_drawdown'] > 15 else 'medium'
                        })

                    if risk_metrics.get('daily_pnl', 0) < -risk_metrics.get('portfolio_value', 10000) * 0.02:
                        alerts.append({
                            'type': 'daily_loss_warning',
                            'message': f"Daily loss: ${abs(risk_metrics['daily_pnl']):.2f}",
                            'severity': 'high'
                        })

                    if risk_metrics.get('emergency_stop_active', False):
                        alerts.append({
                            'type': 'emergency_stop_active',
                            'message': "Emergency stop is active - all trading halted",
                            'severity': 'critical'
                        })

                    # Send alerts if any
                    if alerts:
                        message = {
                            'type': WebSocketEvent.RISK_ALERT.value,
                            'data': {
                                'alerts': alerts,
                                'risk_metrics': risk_metrics,
                                'timestamp': datetime.utcnow().isoformat()
                            }
                        }

                        for user_id in manager.active_connections:
                            await manager.send_personal_message(user_id, message)

                except Exception as e:
                    logger.error(f"Error in risk monitor: {str(e)}")

        except Exception as e:
            logger.error(f"Error in risk monitoring: {str(e)}")
            await asyncio.sleep(180)

async def heartbeat_checker():
    """Periodically check for dead connections"""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            await manager.heartbeat_check()

        except Exception as e:
            logger.error(f"Error in heartbeat checker: {str(e)}")
            await asyncio.sleep(60)

# Utility function to send opportunity alerts
async def send_opportunity_alert(market_id: str, analysis_result: Dict[str, Any]):
    """Send opportunity alert to all users"""
    try:
        message = {
            'type': WebSocketEvent.OPPORTUNITY_ALERT.value,
            'data': {
                'market_id': market_id,
                'prediction': analysis_result.get('ensemble_prediction', 0),
                'confidence': analysis_result.get('confidence', 0),
                'signal_classification': analysis_result.get('signal_classification', 'hold'),
                'expected_value': analysis_result.get('expected_value', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
        }

        # Send to all active users
        for user_id in manager.active_connections:
            await manager.send_personal_message(user_id, message)

    except Exception as e:
        logger.error(f"Error sending opportunity alert: {str(e)}")

# Utility function to send trade execution notifications
async def send_trade_notification(user_id: str, trade_result: Dict[str, Any]):
    """Send trade execution notification to specific user"""
    try:
        message = {
            'type': WebSocketEvent.TRADE_EXECUTED.value,
            'data': {
                'trade_id': trade_result.get('trade_id'),
                'market_id': trade_result.get('market_id'),
                'side': trade_result.get('side'),
                'count': trade_result.get('count'),
                'price': trade_result.get('price'),
                'status': trade_result.get('status'),
                'fees': trade_result.get('fees', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
        }

        await manager.send_personal_message(user_id, message)

    except Exception as e:
        logger.error(f"Error sending trade notification: {str(e)}")

@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    try:
        stats = manager.get_connection_stats()
        return {
            'websocket_stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get WebSocket statistics"
        )