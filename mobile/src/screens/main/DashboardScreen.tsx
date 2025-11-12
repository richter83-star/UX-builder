import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  StyleSheet,
  Dimensions,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import apiService from '../../services/ApiService';
import webSocketService from '../../services/WebSocketService';
import {
  PortfolioMetrics,
  TradingOpportunity,
  Market,
  WebSocketMessage,
  WebSocketEventType,
} from '../../types';

const { width: screenWidth } = Dimensions.get('window');

interface DashboardScreenProps {
  navigation: any;
}

const DashboardScreen: React.FC<DashboardScreenProps> = ({ navigation }) => {
  const [refreshing, setRefreshing] = useState(false);
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics | null>(null);
  const [opportunities, setOpportunities] = useState<TradingOpportunity[]>([]);
  const [recentMarkets, setRecentMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const { theme, colors } = useTheme();
  const { authState } = useAuth();

  const loadDashboardData = useCallback(async () => {
    if (!authState.isAuthenticated) return;

    try {
      const [portfolio, opportunitiesData, marketsData] = await Promise.all([
        apiService.getPortfolioMetrics(),
        apiService.getTradingOpportunities({ limit: 5 }),
        apiService.getMarkets({ limit: 10 }),
      ]);

      setPortfolioMetrics(portfolio);
      setOpportunities(opportunitiesData);
      setRecentMarkets(marketsData);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [authState.isAuthenticated]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  useEffect(() => {
    if (authState.isAuthenticated && authState.user) {
      const initializeWebSocket = async () => {
        try {
          await webSocketService.connect(
            authState.user.id,
            authState.token!,
            {
              onConnect: () => setWsConnected(true),
              onDisconnect: () => setWsConnected(false),
              onPositionUpdate: (data) => {
                if (data.portfolio_metrics) {
                  setPortfolioMetrics(data.portfolio_metrics);
                }
              },
              onError: (error) => console.error('WebSocket error:', error),
            }
          );
        } catch (error) {
          console.error('WebSocket connection failed:', error);
        }
      };

      initializeWebSocket();

      return () => {
        webSocketService.disconnect();
      };
    }
  }, [authState.isAuthenticated, authState.user, authState.token]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercentage = (value: number): string => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const getSignalColor = (signal: string): string => {
    switch (signal.toLowerCase()) {
      case 'strong_buy':
      case 'buy':
        return colors.success;
      case 'strong_sell':
      case 'sell':
        return colors.error;
      case 'hold':
      default:
        return colors.warning;
    }
  };

  const renderPortfolioCard = () => {
    if (!portfolioMetrics) return null;

    return (
      <View style={[styles.card, { backgroundColor: colors.surface }]}>
        <View style={styles.cardHeader}>
          <Text style={[styles.cardTitle, { color: colors.text }]}>
            Portfolio Overview
          </Text>
          <TouchableOpacity
            onPress={() => navigation.navigate('Portfolio')}
            style={styles.seeAllButton}
          >
            <Icon name="arrow-forward" size={20} color={colors.primary} />
          </TouchableOpacity>
        </View>

        <View style={styles.portfolioValue}>
          <Text style={[styles.portfolioAmount, { color: colors.text }]}>
            {formatCurrency(portfolioMetrics.total_value)}
          </Text>
          <View style={[
            styles.portfolioChange,
            portfolioMetrics.daily_pnl >= 0 ? styles.positiveChange : styles.negativeChange
          ]}>
            <Icon
              name={portfolioMetrics.daily_pnl >= 0 ? 'trending-up' : 'trending-down'}
              size={16}
              color={portfolioMetrics.daily_pnl >= 0 ? colors.success : colors.error}
            />
            <Text style={[
              styles.changeText,
              { color: portfolioMetrics.daily_pnl >= 0 ? colors.success : colors.error }
            ]}>
              {formatCurrency(portfolioMetrics.daily_pnl)} ({formatPercentage(portfolioMetrics.daily_pnl_percent)})
            </Text>
          </View>
        </View>

        <View style={styles.portfolioStats}>
          <View style={styles.statItem}>
            <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
              Positions
            </Text>
            <Text style={[styles.statValue, { color: colors.text }]}>
              {portfolioMetrics.number_of_positions}
            </Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
              Win Rate
            </Text>
            <Text style={[styles.statValue, { color: colors.text }]}>
              {portfolioMetrics.win_rate.toFixed(1)}%
            </Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
              Sharpe
            </Text>
            <Text style={[styles.statValue, { color: colors.text }]}>
              {portfolioMetrics.sharpe_ratio.toFixed(2)}
            </Text>
          </View>
        </View>
      </View>
    );
  };

  const renderOpportunitiesCard = () => (
    <View style={[styles.card, { backgroundColor: colors.surface }]}>
      <View style={styles.cardHeader}>
        <Text style={[styles.cardTitle, { color: colors.text }]}>
          Top Opportunities
        </Text>
        <TouchableOpacity
          onPress={() => navigation.navigate('Analysis')}
          style={styles.seeAllButton}
        >
          <Icon name="arrow-forward" size={20} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {opportunities.length > 0 ? (
        opportunities.map((opportunity, index) => (
          <TouchableOpacity
            key={opportunity.market_id}
            style={[styles.opportunityItem, index < opportunities.length - 1 && styles.opportunityItemBorder]}
            onPress={() => navigation.navigate('MarketDetail', { marketId: opportunity.market_id })}
          >
            <View style={styles.opportunityContent}>
              <Text style={[styles.opportunityTitle, { color: colors.text }]} numberOfLines={2}>
                {opportunity.market_title}
              </Text>
              <View style={styles.opportunityMeta}>
                <Text style={[styles.opportunityCategory, { color: colors.textSecondary }]}>
                  {opportunity.category}
                </Text>
                <View style={styles.opportunitySignal}>
                  <Text style={[styles.signalText, { color: getSignalColor(opportunity.signal_classification) }]}>
                    {opportunity.signal_classification.replace('_', ' ').toUpperCase()}
                  </Text>
                </View>
              </View>
              <View style={styles.opportunityStats}>
                <View style={styles.opportunityStat}>
                  <Text style={[styles.statLabelSmall, { color: colors.textSecondary }]}>
                    Confidence
                  </Text>
                  <Text style={[styles.statValueSmall, { color: colors.text }]}>
                    {(opportunity.confidence * 100).toFixed(1)}%
                  </Text>
                </View>
                <View style={styles.opportunityStat}>
                  <Text style={[styles.statLabelSmall, { color: colors.textSecondary }]}>
                    Prediction
                  </Text>
                  <Text style={[styles.statValueSmall, { color: colors.text }]}>
                    {opportunity.ensemble_prediction.toFixed(3)}
                  </Text>
                </View>
                <View style={styles.opportunityStat}>
                  <Text style={[styles.statLabelSmall, { color: colors.textSecondary }]}>
                    Risk
                  </Text>
                  <Text style={[styles.statValueSmall, { color: colors.text }]}>
                    {opportunity.risk_score.toFixed(1)}
                  </Text>
                </View>
              </View>
            </View>
          </TouchableOpacity>
        ))
      ) : (
        <View style={styles.emptyState}>
          <Icon name="insights" size={48} color={colors.textSecondary} />
          <Text style={[styles.emptyStateText, { color: colors.textSecondary }]}>
            No opportunities available
          </Text>
        </View>
      )}
    </View>
  );

  const renderRecentMarketsCard = () => (
    <View style={[styles.card, { backgroundColor: colors.surface }]}>
      <View style={styles.cardHeader}>
        <Text style={[styles.cardTitle, { color: colors.text }]}>
          Recent Markets
        </Text>
        <TouchableOpacity
          onPress={() => navigation.navigate('Markets')}
          style={styles.seeAllButton}
        >
          <Icon name="arrow-forward" size={20} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {recentMarkets.length > 0 ? (
        recentMarkets.slice(0, 5).map((market, index) => (
          <TouchableOpacity
            key={market.market_id}
            style={[styles.marketItem, index < Math.min(4, recentMarkets.length - 1) && styles.marketItemBorder]}
            onPress={() => navigation.navigate('MarketDetail', { marketId: market.market_id })}
          >
            <View style={styles.marketContent}>
              <Text style={[styles.marketTitle, { color: colors.text }]} numberOfLines={2}>
                {market.title}
              </Text>
              <View style={styles.marketMeta}>
                <Text style={[styles.marketCategory, { color: colors.textSecondary }]}>
                  {market.category}
                </Text>
                <Text style={[styles.marketStatus, { color: colors.primary }]}>
                  {market.status}
                </Text>
              </View>
              {market.current_price && (
                <Text style={[styles.marketPrice, { color: colors.text }]}>
                  ${market.current_price.toFixed(2)}
                </Text>
              )}
            </View>
          </TouchableOpacity>
        ))
      ) : (
        <View style={styles.emptyState}>
          <Icon name="store" size={48} color={colors.textSecondary} />
          <Text style={[styles.emptyStateText, { color: colors.textSecondary }]}>
            No recent markets
          </Text>
        </View>
      )}
    </View>
  );

  const renderConnectionStatus = () => (
    <View style={[styles.connectionStatus, { backgroundColor: colors.surface }]}>
      <View style={styles.connectionIndicator}>
        <Icon
          name={wsConnected ? 'wifi' : 'wifi-off'}
          size={16}
          color={wsConnected ? colors.success : colors.error}
        />
        <Text style={[styles.connectionText, { color: colors.textSecondary }]}>
          {wsConnected ? 'Connected' : 'Offline'}
        </Text>
      </View>
    </View>
  );

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            Loading dashboard...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollViewContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
            tintColor={colors.primary}
          />
        }
      >
        <View style={styles.header}>
          <Text style={[styles.title, { color: colors.text }]}>
            Welcome back, {authState.user?.email?.split('@')[0] || 'User'}!
          </Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Here's your trading overview
          </Text>
        </View>

        {renderConnectionStatus()}
        {renderPortfolioCard()}
        {renderOpportunitiesCard()}
        {renderRecentMarketsCard()}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollViewContent: {
    padding: 16,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  },
  connectionStatus: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    padding: 8,
    borderRadius: 8,
    marginBottom: 16,
  },
  connectionIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  connectionText: {
    marginLeft: 6,
    fontSize: 12,
    fontWeight: '500',
  },
  card: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  seeAllButton: {
    padding: 4,
  },
  portfolioValue: {
    marginBottom: 20,
  },
  portfolioAmount: {
    fontSize: 32,
    fontWeight: '700',
    marginBottom: 8,
  },
  portfolioChange: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  positiveChange: {},
  negativeChange: {},
  changeText: {
    fontSize: 16,
    fontWeight: '500',
    marginLeft: 4,
  },
  portfolioStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 12,
    marginBottom: 4,
  },
  statValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  opportunityItem: {
    paddingVertical: 12,
  },
  opportunityItemBorder: {
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  opportunityContent: {},
  opportunityTitle: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 4,
    lineHeight: 20,
  },
  opportunityMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  opportunityCategory: {
    fontSize: 12,
    textTransform: 'capitalize',
  },
  opportunitySignal: {},
  signalText: {
    fontSize: 10,
    fontWeight: '600',
  },
  opportunityStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  opportunityStat: {
    flex: 1,
    alignItems: 'center',
  },
  statLabelSmall: {
    fontSize: 10,
    marginBottom: 2,
  },
  statValueSmall: {
    fontSize: 12,
    fontWeight: '600',
  },
  marketItem: {
    paddingVertical: 12,
  },
  marketItemBorder: {
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  marketContent: {},
  marketTitle: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 4,
    lineHeight: 20,
  },
  marketMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  marketCategory: {
    fontSize: 12,
    textTransform: 'capitalize',
  },
  marketStatus: {
    fontSize: 12,
    fontWeight: '500',
  },
  marketPrice: {
    fontSize: 16,
    fontWeight: '600',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  emptyStateText: {
    marginTop: 12,
    fontSize: 14,
    textAlign: 'center',
  },
});

export default DashboardScreen;