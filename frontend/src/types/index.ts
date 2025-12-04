// User and Authentication Types
export interface User {
  id: string;
  email: string;
  risk_profile: 'conservative' | 'moderate' | 'aggressive';
  is_active: boolean;
  created_at: string;
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

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
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

export interface MarketSeries {
  name: string;
  category: string;
  description?: string;
  markets_count: number;
  active_markets: number;
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

export interface AnalysisSummary {
  total_markets_analyzed: number;
  successful_analyses: number;
  failed_analyses: number;
  average_confidence: number;
  bullish_signals: number;
  bearish_signals: number;
  neutral_signals: number;
  top_opportunities: TradingOpportunity[];
  analysis_time_seconds: number;
}

export interface PerformanceMetrics {
  analyzer: string;
  total_predictions: number;
  recent_accuracy: number;
  overall_accuracy: number;
  average_confidence: number;
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

export interface PortfolioAllocation {
  total_portfolio_value: number;
  category_allocation: Record<string, {
    value: number;
    percentage: number;
    positions: number;
  }>;
  total_categories: number;
  largest_category: string | null;
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

// UI/Component Types
export interface TableColumn {
  key: string;
  title: string;
  dataIndex: string;
  width?: number;
  align?: 'left' | 'center' | 'right';
  sorter?: boolean;
  render?: (value: any, record: any, index: number) => React.ReactNode;
}

export interface ChartDataPoint {
  x: string | number;
  y: number;
  timestamp?: string;
}

export interface ChartConfig {
  title: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  color?: string;
  showGrid?: boolean;
  showTooltip?: boolean;
}

export interface NotificationConfig {
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
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

// Watchlist / rules
export interface WatchlistEntry {
  market_ticker: string;
  tracked_at: string;
  expires_at: string;
  alerts_enabled: boolean;
  decision_trace: string;
  effective_rules: Record<string, any>;
}

export interface OverridePayload {
  alerts_enabled?: boolean;
  edge_threshold?: number;
  min_liquidity?: number;
  max_spread?: number;
  channels_json?: Record<string, boolean>;
}

export interface RuleDefaults {
  alerts_enabled_default: boolean;
  edge_threshold_default: number;
  max_alerts_per_day: number;
  digest_mode: string;
  digest_time?: string;
  channels_json?: Record<string, boolean>;
  min_liquidity?: number;
  max_spread?: number;
}

// Store/State Types
export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface MarketState {
  markets: Market[];
  selectedMarket: MarketDetail | null;
  loading: boolean;
  error: string | null;
  filters: FilterForm;
  pagination: {
    page: number;
    limit: number;
    total: number;
  };
}

export interface AnalysisState {
  opportunities: TradingOpportunity[];
  selectedAnalysis: EnsembleAnalysis | null;
  performanceMetrics: PerformanceMetrics[];
  summary: AnalysisSummary | null;
  loading: boolean;
  analyzing: boolean;
  error: string | null;
}

export interface TradingState {
  positions: Position[];
  trades: Trade[];
  portfolioMetrics: PortfolioMetrics | null;
  riskMetrics: RiskMetrics | null;
  loading: boolean;
  error: string | null;
}

export interface WebSocketState {
  connected: boolean;
  subscribedMarkets: Set<string>;
  lastMessage: WebSocketMessage | null;
  connectionStats: {
    activeConnections: number;
    totalSubscriptions: number;
    marketsWithSubscribers: number;
  } | null;
}

// Utility Types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

// Error Types
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface ValidationError {
  field: string;
  message: string;
  value?: any;
}

// Configuration Types
export interface AppConfig {
  apiUrl: string;
  wsUrl: string;
  environment: 'development' | 'production' | 'staging';
  version: string;
  features: {
    autoTrading: boolean;
    advancedCharts: boolean;
    notifications: boolean;
    riskManagement: boolean;
  };
}

// Chart Specific Types
export interface PriceChartPoint extends ChartDataPoint {
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

export interface AllocationChartData {
  category: string;
  value: number;
  percentage: number;
  color?: string;
}

// Export all types for easy importing
export type {
  // Re-export commonly used external types
  CSSProperties,
  ReactNode,
  ReactElement,
  ComponentType,
} from 'react';