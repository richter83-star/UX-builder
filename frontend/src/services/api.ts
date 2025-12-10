import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import {
  AuthResponse,
  LoginCredentials,
  RegisterData,
  Market,
  MarketDetail,
  TradingOpportunity,
  EnsembleAnalysis,
  OrderRequest,
  OrderResponse,
  Position,
  Trade,
  PortfolioMetrics,
  RiskAssessment,
  RiskMetrics,
  AnalysisSummary,
  PerformanceMetrics
} from '../types';

type ApiError = AxiosError<{ detail?: string }>;

class ApiService {
  public readonly api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for adding auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Generic error handler
  private handleError(error: ApiError): Promise<never> {
    const message = error.response?.data?.detail || error.message || 'An unexpected error occurred';
    return Promise.reject(new Error(message));
  }

  // Authentication endpoints
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response: AxiosResponse<AuthResponse> = await this.api.post('/api/auth/login', credentials);
      const { access_token, user } = response.data;

      // Store token and user info
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user', JSON.stringify(user));

      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async register(userData: RegisterData): Promise<AuthResponse> {
    try {
      const response: AxiosResponse<AuthResponse> = await this.api.post('/api/auth/register', userData);
      const { access_token, user } = response.data;

      // Store token and user info
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user', JSON.stringify(user));

      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async logout(): Promise<void> {
    try {
      await this.api.post('/api/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
    }
  }

  async getCurrentUser(): Promise<any> {
    try {
      const response = await this.api.get('/api/auth/me');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async updateProfile(profileData: Partial<RegisterData>): Promise<void> {
    try {
      await this.api.put('/api/auth/profile', profileData);
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  // Market endpoints
  async getMarkets(params?: {
    category?: string;
    status?: string;
    limit?: number;
    offset?: number;
    search?: string;
  }): Promise<Market[]> {
    try {
      const response = await this.api.get('/api/markets/', { params });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getMarketDetail(marketId: string, params?: {
    include_history?: boolean;
    history_days?: number;
  }): Promise<MarketDetail> {
    try {
      const response = await this.api.get(`/api/markets/${marketId}`, { params });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getMarketHistory(marketId: string, params?: {
    start_date?: string;
    end_date?: string;
    interval?: string;
  }): Promise<any> {
    try {
      const response = await this.api.get(`/api/markets/${marketId}/history`, { params });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getMarketPrice(marketId: string): Promise<any> {
    try {
      const response = await this.api.get(`/api/markets/${marketId}/price`);
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async searchMarkets(params: {
    query: string;
    category?: string;
    limit?: number;
  }): Promise<any> {
    try {
      const response = await this.api.get('/api/markets/search', { params });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getMarketSeries(category?: string): Promise<any[]> {
    try {
      const response = await this.api.get('/api/markets/series/list', {
        params: { category }
      });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  // Watchlist endpoints
  async getWatchlist(): Promise<any> {
    try {
      const response = await this.api.get('/api/watchlist/');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async trackMarket(marketTicker: string): Promise<any> {
    try {
      const response = await this.api.post(`/api/watchlist/${marketTicker}`);
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async untrackMarket(marketTicker: string): Promise<any> {
    try {
      const response = await this.api.post(`/api/watchlist/${marketTicker}/untrack`);
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getOverride(marketTicker: string): Promise<any> {
    try {
      const response = await this.api.get(`/api/watchlist/${marketTicker}/override`);
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async saveOverride(marketTicker: string, payload: any): Promise<any> {
    try {
      const response = await this.api.put(`/api/watchlist/${marketTicker}/override`, payload);
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  // Rules
  async getRules(): Promise<any> {
    try {
      const response = await this.api.get('/api/rules/');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async updateRules(payload: any): Promise<any> {
    try {
      const response = await this.api.put('/api/rules/', payload);
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async requestMarket(payload: any): Promise<any> {
    try {
      const response = await this.api.post('/api/market-requests/', payload);
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getMarketCategories(): Promise<any> {
    try {
      const response = await this.api.get('/api/markets/categories/list');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  // Analysis endpoints
  async refreshAnalysis(marketIds: string[], forceRefresh = false): Promise<any> {
    try {
      const response = await this.api.post('/api/analysis/refresh', {
        market_ids: marketIds,
        force_refresh: forceRefresh
      });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getTradingOpportunities(params?: {
    category?: string;
    min_confidence?: number;
    min_prediction?: number;
    limit?: number;
  }): Promise<TradingOpportunity[]> {
    try {
      const response = await this.api.get('/api/analysis/opportunities', { params });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getMarketAnalysis(marketId: string, analyzer?: string): Promise<EnsembleAnalysis> {
    try {
      const response = await this.api.get(`/api/analysis/${marketId}`, {
        params: { analyzer }
      });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getRecentAnalysisSummary(hours = 24, category?: string): Promise<AnalysisSummary> {
    try {
      const response = await this.api.get('/api/analysis/summary/recent', {
        params: { hours, category }
      });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getAnalyzerPerformanceMetrics(): Promise<PerformanceMetrics[]> {
    try {
      const response = await this.api.get('/api/analysis/performance/metrics');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async clearAnalysisCache(marketId?: string): Promise<any> {
    try {
      const response = await this.api.delete('/api/analysis/cache', {
        params: { market_id: marketId }
      });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  // Trading endpoints
  async placeOrder(order: OrderRequest, autoRiskCheck = true): Promise<OrderResponse> {
    try {
      const response = await this.api.post('/api/trading/orders', order, {
        params: { auto_risk_check: autoRiskCheck }
      });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getPositions(params?: {
    market_id?: string;
    risk_level?: string;
    limit?: number;
  }): Promise<Position[]> {
    try {
      const response = await this.api.get('/api/trading/positions', { params });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getPositionDetail(positionId: string): Promise<Position> {
    try {
      const response = await this.api.get(`/api/trading/positions/${positionId}`);
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async closePosition(positionId: string, reason = 'manual'): Promise<any> {
    try {
      const response = await this.api.post(`/api/trading/positions/${positionId}/close`, null, {
        params: { reason }
      });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getTradeHistory(params?: {
    start_date?: string;
    end_date?: string;
    status?: string;
    market_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<Trade[]> {
    try {
      const response = await this.api.get('/api/trading/history', { params });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getPortfolioMetrics(): Promise<PortfolioMetrics> {
    try {
      const response = await this.api.get('/api/trading/portfolio/metrics');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getPortfolioPerformance(days = 30): Promise<any> {
    try {
      const response = await this.api.get('/api/trading/portfolio/performance', {
        params: { days }
      });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getPortfolioAllocation(): Promise<any> {
    try {
      const response = await this.api.get('/api/trading/portfolio/allocation');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async assessTradeRisk(request: {
    market_id: string;
    side: 'yes' | 'no';
    count: number;
    price?: number;
    expected_return?: number;
    win_probability?: number;
  }): Promise<RiskAssessment> {
    try {
      const response = await this.api.post('/api/trading/risk/assess', request);
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async getRiskMetrics(): Promise<RiskMetrics> {
    try {
      const response = await this.api.get('/api/trading/risk/metrics');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  async toggleEmergencyStop(active: boolean, reason = ''): Promise<any> {
    try {
      const response = await this.api.post('/api/trading/risk/emergency-stop', null, {
        params: { active, reason }
      });
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  // Health check
  async healthCheck(): Promise<any> {
    try {
      const response = await this.api.get('/health');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }

  // WebSocket stats
  async getWebSocketStats(): Promise<any> {
    try {
      const response = await this.api.get('/ws/stats');
      return response.data;
    } catch (error) {
      return this.handleError(error as ApiError);
    }
  }
}

// Create and export singleton instance
const apiService = new ApiService();
export default apiService;

// Export axios instance for custom requests
export const { api } = apiService;