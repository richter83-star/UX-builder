import { io, Socket } from 'socket.io-client';
import { WebSocketMessage, WebSocketEventType } from '../types';

export interface WebSocketCallbacks {
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  onMessage?: (message: WebSocketMessage) => void;
  onMarketUpdate?: (data: any) => void;
  onPositionUpdate?: (data: any) => void;
  onOpportunityAlert?: (data: any) => void;
  onTradeExecuted?: (data: any) => void;
  onRiskAlert?: (data: any) => void;
}

class WebSocketService {
  private socket: Socket | null = null;
  private callbacks: WebSocketCallbacks = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;
  private isManualDisconnect = false;

  constructor() {
    this.setupEventHandlers();
  }

  private setupEventHandlers() {
    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.pauseReconnection();
      } else {
        this.resumeReconnection();
      }
    });

    // Handle page unload
    window.addEventListener('beforeunload', () => {
      this.isManualDisconnect = true;
      this.disconnect();
    });
  }

  async connect(userId: string, token: string, callbacks: WebSocketCallbacks = {}): Promise<void> {
    if (this.socket?.connected || this.isConnecting) {
      return;
    }

    this.callbacks = { ...this.callbacks, ...callbacks };
    this.isManualDisconnect = false;
    this.isConnecting = true;

    try {
      const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
      const url = `${wsUrl}/ws?token=${encodeURIComponent(token)}&user_id=${encodeURIComponent(userId)}`;

      this.socket = io(url, {
        transports: ['websocket'],
        upgrade: false,
        rememberTransport: false,
        timeout: 20000,
        forceNew: true,
      });

      this.setupSocketEvents();

      // Wait for connection
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('WebSocket connection timeout'));
        }, 20000);

        this.socket!.once('connect', () => {
          clearTimeout(timeout);
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.callbacks.onConnect?.();
          resolve();
        });

        this.socket!.once('connect_error', (error) => {
          clearTimeout(timeout);
          this.isConnecting = false;
          reject(error);
        });
      });
    } catch (error) {
      this.isConnecting = false;
      throw error;
    }
  }

  private setupSocketEvents() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.callbacks.onConnect?.();
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.callbacks.onDisconnect?.();

      // Attempt reconnection if not manual disconnect
      if (!this.isManualDisconnect && reason !== 'io client disconnect') {
        this.attemptReconnection();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.callbacks.onError?.(error);
      this.isConnecting = false;
    });

    this.socket.on('message', (data: WebSocketMessage) => {
      this.handleMessage(data);
    });

    // Handle connection status messages
    this.socket.on('connection_status', (data) => {
      console.log('Connection status:', data);
    });

    // Handle ping/pong for connection health
    this.socket.on('ping', () => {
      this.sendPong();
    });

    // Handle subscription confirmations
    this.socket.on('subscription_confirmed', (data) => {
      console.log('Subscription confirmed:', data);
    });
  }

  private handleMessage(message: WebSocketMessage) {
    // Update last activity timestamp
    this.callbacks.onMessage?.(message);

    // Route to specific handlers based on message type
    switch (message.type) {
      case WebSocketEventType.MARKET_UPDATE:
        this.callbacks.onMarketUpdate?.(message.data);
        break;

      case WebSocketEventType.POSITION_UPDATE:
        this.callbacks.onPositionUpdate?.(message.data);
        break;

      case WebSocketEventType.OPPORTUNITY_ALERT:
        this.callbacks.onOpportunityAlert?.(message.data);
        break;

      case WebSocketEventType.TRADE_EXECUTED:
        this.callbacks.onTradeExecuted?.(message.data);
        break;

      case WebSocketEventType.RISK_ALERT:
        this.callbacks.onRiskAlert?.(message.data);
        break;

      case WebSocketEventType.ANALYSIS_UPDATE:
        // Handle analysis updates if needed
        break;

      case WebSocketEventType.CONNECTION_STATUS:
        console.log('Connection status update:', message.data);
        break;

      case 'ping':
        this.sendPong();
        break;

      case 'pong':
        // Update heartbeat
        break;

      default:
        console.log('Unknown message type:', message.type);
    }
  }

  private sendPong() {
    this.send({ type: 'pong', timestamp: new Date().toISOString() });
  }

  private attemptReconnection() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts || this.isManualDisconnect) {
      console.log('Max reconnection attempts reached or manual disconnect');
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);

    setTimeout(() => {
      if (!this.socket?.connected && !this.isManualDisconnect) {
        // Get stored credentials
        const token = localStorage.getItem('access_token');
        const userStr = localStorage.getItem('user');

        if (token && userStr) {
          const user = JSON.parse(userStr);
          this.connect(user.id, token, this.callbacks).catch(error => {
            console.error('Reconnection failed:', error);
          });
        }
      }
    }, delay);
  }

  private pauseReconnection() {
    this.isManualDisconnect = true;
    if (this.socket) {
      this.socket.disconnect();
    }
  }

  private resumeReconnection() {
    this.isManualDisconnect = false;
    if (!this.socket?.connected) {
      const token = localStorage.getItem('access_token');
      const userStr = localStorage.getItem('user');

      if (token && userStr) {
        const user = JSON.parse(userStr);
        this.connect(user.id, token, this.callbacks).catch(error => {
          console.error('Reconnection on resume failed:', error);
        });
      }
    }
  }

  // Message sending methods
  send(message: any): boolean {
    if (!this.socket?.connected) {
      console.warn('WebSocket not connected, message not sent:', message);
      return false;
    }

    try {
      this.socket.emit('message', message);
      return true;
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      return false;
    }
  }

  // Subscription methods
  subscribeToMarket(marketId: string): boolean {
    return this.send({
      type: 'subscribe',
      data: { market_id: marketId }
    });
  }

  unsubscribeFromMarket(marketId: string): boolean {
    return this.send({
      type: 'unsubscribe',
      data: { market_id: marketId }
    });
  }

  requestPortfolioUpdate(): boolean {
    return this.send({
      type: 'get_portfolio'
    });
  }

  requestRiskMetrics(): boolean {
    return this.send({
      type: 'get_risk_metrics'
    });
  }

  // Connection management
  disconnect(): void {
    this.isManualDisconnect = true;
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  isReconnecting(): boolean {
    return this.reconnectAttempts > 0 && !this.isConnected();
  }

  getConnectionInfo() {
    return {
      connected: this.isConnected(),
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts,
      socketId: this.socket?.id,
    };
  }

  // Update callbacks
  updateCallbacks(callbacks: Partial<WebSocketCallbacks>): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  // Heartbeat monitoring
  startHeartbeat(): void {
    // Send periodic ping messages
    setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: 'ping', timestamp: new Date().toISOString() });
      }
    }, 30000); // Every 30 seconds
  }

  // Utility methods
  getConnectionStats() {
    return {
      connected: this.isConnected(),
      reconnecting: this.isReconnecting(),
      reconnectAttempts: this.reconnectAttempts,
      lastActivity: new Date().toISOString(),
    };
  }
}

// Create and export singleton instance
const webSocketService = new WebSocketService();
export default webSocketService;

// Export for testing
export { WebSocketService };