// Core Types
export interface User {
  id: string;
  email: string;
  risk_profile: 'conservative' | 'moderate' | 'aggressive';
  is_active: boolean;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  kalshi_api_key?: string;
  kalshi_private_key?: string;
  risk_profile: string;
}

// Market Types
export interface Market {
  market_id: string;
  title: string;
  category: string;
  subtitle?: string;
  settle_date?: string;
  status: string;
  current_price?: number;
  volume?: number;
  created_at: string;
  updated_at: string;
}

export interface MarketDetail extends Market {
  description?: string;
  rules?: string;
  order_book?: Record<string, any>;
  price_history?: MarketPricePoint[];
}

export interface MarketPricePoint {
  price: number;
  volume?: number;
  timestamp: string;
}

// Analysis Types
export interface IndividualAnalysis {
  score: number;
  confidence: number;
  signal: string;
  details: Record<string, any>;
}

export interface EnsembleAnalysis {
  market_id: string;
  market_title: string;
  ensemble_prediction: number;
  confidence: number;
  signal_classification: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
  individual_results: Record<string, IndividualAnalysis>;
  dynamic_weights: Record<string, number>;
  analysis_timestamp: string;
  details: Record<string, any>;
}

export interface TradingOpportunity {
  market_id: string;
  market_title: string;
  category: string;
  ensemble_prediction: number;
  confidence: number;
  signal_classification: string;
  expected_value: number;
  current_price?: number;
  volume?: number;
  individual_predictions: Record<string, IndividualAnalysis>;
  risk_score: number;
  recommendation: string;
  last_updated: string;
}

// Trading Types
export interface OrderRequest {
  market_id: string;
  side: 'yes' | 'no';
  count: number;
  price?: number;
  expected_return?: number;
  win_probability?: number;
}

export interface OrderResponse {
  order_id: string;
  market_id: string;
  side: string;
  count: number;
  price: number;
  status: string;
  executed_at: string;
  fees: number;
  risk_assessment?: RiskAssessment;
  message: string;
}

export interface Position {
  position_id: string;
  market_id: string;
  market_title: string;
  side: string;
  count: number;
  entry_price: number;
  current_price: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  duration_hours: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  updated_at: string;
}

export interface Trade {
  trade_id: string;
  market_id: string;
  market_title: string;
  side: string;
  count: number;
  price: number;
  status: string;
  filled_at?: string;
  created_at: string;
  fees: number;
  realized_pnl?: number;
}

// Risk Management Types
export interface RiskCheck {
  passed: boolean;
  level: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  details: Record<string, any>;
}

export interface RiskAssessment {
  approved: boolean;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  risk_score: number;
  position_size: number;
  max_loss: number;
  risk_checks: RiskCheck[];
  recommendations: string[];
}

export interface RiskMetrics {
  portfolio_value: number;
  daily_pnl: number;
  daily_trades_count: number;
  current_drawdown: number;
  max_portfolio_value: number;
  category_exposures: Record<string, number>;
  total_positions: number;
  risk_checks_enabled: boolean;
  emergency_stop_active: boolean;
  last_updated: string;
}

// Portfolio Types
export interface PortfolioMetrics {
  total_value: number;
  cash_balance: number;
  positions_value: number;
  total_pnl: number;
  total_pnl_percent: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  number_of_positions: number;
  number_of_winning_positions: number;
  number_of_losing_positions: number;
  win_rate: number;
  max_drawdown: number;
  sharpe_ratio: number;
  average_position_size: number;
}

export interface PortfolioPerformance {
  period_start: string;
  period_end: string;
  starting_value: number;
  ending_value: number;
  total_return: number;
  total_return_percent: number;
  max_value: number;
  min_value: number;
  volatility: number;
  data_points: number;
  daily_values: Array<{
    date: string;
    value: number;
    pnl: number;
  }>;
}

// WebSocket Types
export type WebSocketEventType =
  | 'market_update'
  | 'analysis_update'
  | 'opportunity_alert'
  | 'position_update'
  | 'trade_executed'
  | 'risk_alert'
  | 'connection_status';

export interface WebSocketMessage {
  type: WebSocketEventType;
  data: any;
  timestamp?: string;
}

export interface MarketUpdateData {
  market_id: string;
  price: number;
  volume?: number;
  bid?: number;
  ask?: number;
  timestamp: string;
}

export interface PositionUpdateData {
  portfolio_metrics: {
    total_value: number;
    daily_pnl: number;
    win_rate: number;
    number_of_positions: number;
  };
  positions?: Array<{
    position_id: string;
    market_id: string;
    market_title: string;
    unrealized_pnl: number;
    unrealized_pnl_percent: number;
    risk_level: string;
  }>;
  timestamp: string;
}

export interface RiskAlertData {
  alerts: Array<{
    type: string;
    message: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
  }>;
  risk_metrics: RiskMetrics;
  timestamp: string;
}

export interface TradeExecutedData {
  trade_id: string;
  market_id: string;
  side: string;
  count: number;
  price: number;
  status: string;
  fees: number;
  timestamp: string;
}

// Notification Types
export interface NotificationData {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info' | 'trade' | 'risk' | 'opportunity';
  title: string;
  message: string;
  data?: any;
  timestamp: string;
  read: boolean;
}

export interface NotificationConfig {
  enablePush: boolean;
  enableInApp: boolean;
  enableSound: boolean;
  enableVibration: boolean;
  tradeAlerts: boolean;
  riskAlerts: boolean;
  opportunityAlerts: boolean;
}

// Navigation Types
export type RootStackParamList = 'Auth' | 'Main';
export type AuthStackParamList = 'Login' | 'Register' | 'ForgotPassword';
export type MainStackParamList = 'Dashboard' | 'Markets' | 'Analysis' | 'Trading' | 'Portfolio' | 'Settings';
export type MarketStackParamList = 'MarketDetail' | 'MarketAnalysis';

export interface RootStackParamList {
  Auth: AuthStackParamList;
  Main: MainStackParamList;
}

export interface AuthStackParamList {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
}

export interface MainStackParamList {
  Dashboard: undefined;
  Markets: { category?: string; search?: string };
  Analysis: { marketId?: string };
  Trading: { marketId?: string };
  Portfolio: { positionId?: string };
  Settings: { screen?: 'profile' | 'risk' | 'notifications' | 'about' };
}

export interface MarketStackParamList {
  MarketDetail: { marketId: string };
  MarketAnalysis: { marketId: string };
}

// Form Types
export interface RiskSettingsForm {
  risk_tolerance: number; // 1-10 scale
  max_daily_trades: number;
  auto_trading_enabled: boolean;
  max_position_size_percent: number;
  stop_loss_percent: number;
  custom_alerts_enabled: boolean;
}

export interface FilterForm {
  category?: string;
  min_confidence?: number;
  min_prediction?: number;
  risk_level?: string;
  date_range?: [string, string];
}

export interface SearchForm {
  query: string;
  category?: string;
  limit?: number;
}

// Chart Types
export interface ChartDataPoint {
  x: string | number;
  y: number;
  timestamp?: string;
}

export interface PriceChartData extends ChartDataPoint {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PerformanceChartData {
  date: string;
  value: number;
  pnl: number;
  drawdown: number;
}

// UI State Types
export interface LoadingState {
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
}

export interface PaginationState {
  page: number;
  limit: number;
  total: number;
  hasMore: boolean;
}

// Settings Types
export interface AppSettings {
  theme: 'light' | 'dark' | 'auto';
  notifications: NotificationConfig;
  biometric: boolean;
  autoRefresh: boolean;
  refreshInterval: number; // seconds
  chartType: 'line' | 'bar' | 'candlestick';
  defaultRiskProfile: string;
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

// API Response Types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
  success?: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

// Utility Types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

// Export commonly used types
export type {
  ReactNode,
  ComponentType,
  FC,
  ReactElement,
  ReactText,
} from 'react';