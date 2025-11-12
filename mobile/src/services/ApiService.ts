import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  User,
  LoginCredentials,
  RegisterData,
  AuthResponse,
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
  PerformanceMetrics,
  ApiResponse,
  PaginatedResponse,
} from '../types';

class ApiService {
  private api: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = __DEV__
      ? 'http://localhost:8000'  // Development
      : 'https://api.kalshi-agent.com';  // Production

    this.api = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor for adding auth token
    this.api.interceptors.request.use(
      async (config) => {
        const token = await this.getAuthToken();
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
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          await this.clearAuthToken();
          // Navigate to login (handled by AuthContext)
        }
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private async getAuthToken(): Promise<string | null> {
    try {
      const AsyncStorage = require('@react-native-async-storage/async-storage').default;
      return await AsyncStorage.getItem('access_token');
    } catch (error) {
      console.warn('Error getting auth token:', error);
      return null;
    }
  }

  private async setAuthToken(token: string): Promise<void> {
    try {
      const AsyncStorage = require('@react-native-async-storage/async-storage').default;
      await AsyncStorage.setItem('access_token', token);
    } catch (error) {
      console.warn('Error setting auth token:', error);
    }
  }

  private async clearAuthToken(): Promise<void> {
    try {
      const AsyncStorage = require('@react-native-async-storage/async-storage').default;
      await AsyncStorage.removeItem('access_token');
      await AsyncStorage.removeItem('user');
    } catch (error) {
      console.warn('Error clearing auth token:', error);
    }
  }

  private async storeUser(user: User): Promise<void> {
    try {
      const AsyncStorage = require('@react-native-async-storage/async-storage').default;
      await AsyncStorage.setItem('user', JSON.stringify(user));
    } catch (error) {
      console.warn('Error storing user:', error);
    }
  }

  private async getStoredUser(): Promise<User | null> {
    try {
      const AsyncStorage = require('@react-native-async-storage/async-storage').default;
      const userStr = await AsyncStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    } catch (error) {
      console.warn('Error getting stored user:', error);
      return null;
    }
  }

  private handleError(error: AxiosError): Error {
    const message = error.response?.data?.detail || error.message || 'An unexpected error occurred';
    return new Error(message);
  }

  // Authentication endpoints
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response = await this.api.post<AuthResponse>('/api/auth/login', credentials);
      const { access_token, user } = response.data;

      // Store token and user info
      await this.setAuthToken(access_token);
      await this.storeUser(user);

      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async register(userData: RegisterData): Promise<AuthResponse> {
    try {
      const response = await this.api.post<AuthResponse>('/api/auth/register', userData);
      const { access_token, user } = response.data;

      // Store token and user info
      await this.setAuthToken(access_token);
      await this.storeUser(user);

      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async logout(): Promise<void> {
    try {
      await this.api.post('/api/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      await this.clearAuthToken();
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      const response = await this.api.get<User>('/api/auth/me');
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async updateProfile(profileData: Partial<RegisterData>): Promise<void> {
    try {
      await this.api.put('/api/auth/profile', profileData);
    } catch (error) {
      throw this.handleError(error as AxiosError);
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
      const response = await this.api.get<Market[]>('/api/markets/', { params });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getMarketDetail(
    marketId: string,
    params?: {
      include_history?: boolean;
      history_days?: number;
    }
  ): Promise<MarketDetail> {
    try {
      const response = await this.api.get<MarketDetail>(`/api/markets/${marketId}`, { params });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getMarketHistory(
    marketId: string,
    params?: {
      start_date?: string;
      end_date?: string;
      interval?: string;
    }
  ): Promise<any> {
    try {
      const response = await this.api.get(`/api/markets/${marketId}/history`, { params });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getMarketPrice(marketId: string): Promise<any> {
    try {
      const response = await this.api.get(`/api/markets/${marketId}/price`);
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
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
      throw this.handleError(error as AxiosError);
    }
  }

  async getMarketSeries(category?: string): Promise<any[]> {
    try {
      const response = await this.api.get('/api/markets/series/list', {
        params: { category }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  // Analysis endpoints
  async refreshAnalysis(
    marketIds: string[],
    forceRefresh = false
  ): Promise<any> {
    try {
      const response = await this.api.post('/api/analysis/refresh', {
        market_ids: marketIds,
        force_refresh: forceRefresh
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getTradingOpportunities(params?: {
    category?: string;
    min_confidence?: number;
    min_prediction?: number;
    limit?: number;
  }): Promise<TradingOpportunity[]> {
    try {
      const response = await this.api.get<TradingOpportunity[]>('/api/analysis/opportunities', { params });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getMarketAnalysis(marketId: string, analyzer?: string): Promise<EnsembleAnalysis> {
    try {
      const response = await this.api.get<EnsembleAnalysis>(`/api/analysis/${marketId}`, {
        params: { analyzer }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getRecentAnalysisSummary(hours = 24, category?: string): Promise<AnalysisSummary> {
    try {
      const response = await this.api.get<AnalysisSummary>('/api/analysis/summary/recent', {
        params: { hours, category }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  // Trading endpoints
  async placeOrder(order: OrderRequest, autoRiskCheck = true): Promise<OrderResponse> {
    try {
      const response = await this.api.post<OrderResponse>('/api/trading/orders', order, {
        params: { auto_risk_check: autoRiskCheck }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getPositions(params?: {
    market_id?: string;
    risk_level?: string;
    limit?: number;
  }): Promise<Position[]> {
    try {
      const response = await this.api.get<Position[]>('/api/trading/positions', { params });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getPositionDetail(positionId: string): Promise<Position> {
    try {
      const response = await this.api.get<Position>(`/api/trading/positions/${positionId}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async closePosition(positionId: string, reason = 'manual'): Promise<any> {
    try {
      const response = await this.api.post(`/api/trading/positions/${positionId}/close`, null, {
        params: { reason }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
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
      const response = await this.api.get<Trade[]>('/api/trading/history', { params });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getPortfolioMetrics(): Promise<PortfolioMetrics> {
    try {
      const response = await this.api.get<PortfolioMetrics>('/api/trading/portfolio/metrics');
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getPortfolioPerformance(days = 30): Promise<any> {
    try {
      const response = await this.api.get('/api/trading/portfolio/performance', {
        params: { days }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getPortfolioAllocation(): Promise<any> {
    try {
      const response = await this.api.get('/api/trading/portfolio/allocation');
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
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
      const response = await this.api.post<RiskAssessment>('/api/trading/risk/assess', request);
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async getRiskMetrics(): Promise<RiskMetrics> {
    try {
      const response = await this.api.get<RiskMetrics>('/api/trading/risk/metrics');
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  async toggleEmergencyStop(active: boolean, reason = ''): Promise<any> {
    try {
      const response = await this.api.post('/api/trading/risk/emergency-stop', null, {
        params: { active, reason }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  // Health check
  async healthCheck(): Promise<any> {
    try {
      const response = await this.api.get('/health');
      return response.data;
    } catch (error) {
      throw this.handleError(error as AxiosError);
    }
  }

  // Network status
  async getNetworkStatus(): Promise<{
    connected: boolean;
    online: boolean;
    latency: number;
  }> {
    try {
      const startTime = Date.now();
      await this.healthCheck();
      const endTime = Date.now();

      return {
        connected: true,
        online: true,
        latency: endTime - startTime
      };
    } catch (error) {
      return {
        connected: false,
        online: false,
        latency: -1
      };
    }
  }

  // Utility methods
  getBaseURL(): string {
    return this.baseURL;
  }

  setBaseURL(url: string): void {
    this.baseURL = url;
    this.api.defaults.baseURL = url;
  }
}

// Create and export singleton instance
const apiService = new ApiService();
export default apiService;