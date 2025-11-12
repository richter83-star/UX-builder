import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import apiService from '../../services/ApiService';
import {
  Market,
  OrderRequest,
  Position,
  RiskMetrics,
  TradingOpportunity,
} from '../../types';

interface TradingScreenProps {
  navigation: any;
}

const TradingScreen: React.FC<TradingScreenProps> = ({ navigation }) => {
  const [loading, setLoading] = useState(true);
  const [opportunities, setOpportunities] = useState<TradingOpportunity[]>([]);
  const [selectedOpportunity, setSelectedOpportunity] = useState<TradingOpportunity | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [orderType, setOrderType] = useState<'yes' | 'no'>('yes');
  const [orderAmount, setOrderAmount] = useState('');
  const [orderPrice, setOrderPrice] = useState('');
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { theme, colors } = useTheme();
  const { authState } = useAuth();

  const loadTradingData = useCallback(async () => {
    if (!authState.isAuthenticated) return;

    try {
      const [opportunitiesData, positionsData, riskData] = await Promise.all([
        apiService.getTradingOpportunities({ limit: 20 }),
        apiService.getPositions(),
        apiService.getRiskMetrics(),
      ]);

      setOpportunities(opportunitiesData);
      setPositions(positionsData);
      setRiskMetrics(riskData);
    } catch (error) {
      console.error('Error loading trading data:', error);
    } finally {
      setLoading(false);
    }
  }, [authState.isAuthenticated]);

  useEffect(() => {
    loadTradingData();
  }, [loadTradingData]);

  const handleSelectOpportunity = (opportunity: TradingOpportunity) => {
    setSelectedOpportunity(opportunity);
    setOrderType(opportunity.signal_classification.includes('buy') ? 'yes' : 'no');
    setOrderPrice(opportunity.market_current_price?.toString() || '');
    setShowOrderModal(true);
  };

  const validateOrder = (): boolean => {
    if (!orderAmount || parseFloat(orderAmount) <= 0) {
      Alert.alert('Invalid Amount', 'Please enter a valid order amount');
      return false;
    }

    if (!orderPrice || parseFloat(orderPrice) <= 0) {
      Alert.alert('Invalid Price', 'Please enter a valid order price');
      return false;
    }

    if (!riskMetrics) return true;

    const positionSize = parseFloat(orderAmount) * parseFloat(orderPrice);
    if (positionSize > riskMetrics.max_position_size) {
      Alert.alert('Position Too Large', `Maximum position size is $${riskMetrics.max_position_size.toFixed(2)}`);
      return false;
    }

    if (positionSize > riskMetrics.available_capital) {
      Alert.alert('Insufficient Capital', 'You do not have enough available capital');
      return false;
    }

    return true;
  };

  const handleSubmitOrder = async () => {
    if (!selectedOpportunity || !validateOrder()) return;

    setIsSubmitting(true);
    try {
      const orderRequest: OrderRequest = {
        market_id: selectedOpportunity.market_id,
        side: orderType,
        count: parseInt(orderAmount),
        price: parseFloat(orderPrice),
        expiration: selectedOpportunity.market_expiration,
      };

      const result = await apiService.placeOrder(orderRequest);

      Alert.alert(
        'Order Placed Successfully',
        `Your ${orderType.toUpperCase()} order has been placed successfully.`,
        [
          { text: 'OK', onPress: () => {
            setShowOrderModal(false);
            loadTradingData();
          }}
        ]
      );
    } catch (error) {
      Alert.alert(
        'Order Failed',
        error instanceof Error ? error.message : 'Failed to place order'
      );
    } finally {
      setIsSubmitting(false);
    }
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

  const getRiskColor = (risk: number): string => {
    if (risk <= 3) return colors.success;
    if (risk <= 6) return colors.warning;
    return colors.error;
  };

  const renderOpportunityCard = (opportunity: TradingOpportunity) => (
    <TouchableOpacity
      key={opportunity.market_id}
      style={[styles.opportunityCard, { backgroundColor: colors.surface }]}
      onPress={() => handleSelectOpportunity(opportunity)}
    >
      <View style={styles.opportunityHeader}>
        <View style={styles.opportunityTitleContainer}>
          <Text style={[styles.opportunityTitle, { color: colors.text }]} numberOfLines={2}>
            {opportunity.market_title}
          </Text>
          <Text style={[styles.opportunityCategory, { color: colors.textSecondary }]}>
            {opportunity.category}
          </Text>
        </View>
        <View style={[
          styles.signalBadge,
          { backgroundColor: `${getSignalColor(opportunity.signal_classification)}20` }
        ]}>
          <Text style={[
            styles.signalText,
            { color: getSignalColor(opportunity.signal_classification) }
          ]}>
            {opportunity.signal_classification.replace('_', ' ').toUpperCase()}
          </Text>
        </View>
      </View>

      <View style={styles.opportunityMetrics}>
        <View style={styles.metricColumn}>
          <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>
            Confidence
          </Text>
          <Text style={[styles.metricValue, { color: colors.text }]}>
            {(opportunity.confidence * 100).toFixed(1)}%
          </Text>
        </View>
        <View style={styles.metricColumn}>
          <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>
            Prediction
          </Text>
          <Text style={[styles.metricValue, { color: colors.text }]}>
            {opportunity.ensemble_prediction.toFixed(3)}
          </Text>
        </View>
        <View style={styles.metricColumn}>
          <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>
            Risk Score
          </Text>
          <Text style={[
            styles.metricValue,
            { color: getRiskColor(opportunity.risk_score) }
          ]}>
            {opportunity.risk_score.toFixed(1)}
          </Text>
        </View>
      </View>

      {opportunity.market_current_price && (
        <View style={styles.opportunityPrice}>
          <Text style={[styles.priceLabel, { color: colors.textSecondary }]}>
            Current Price
          </Text>
          <Text style={[styles.priceValue, { color: colors.text }]}>
            ${opportunity.market_current_price.toFixed(2)}
          </Text>
        </View>
      )}

      <TouchableOpacity style={styles.tradeButton}>
        <Text style={[styles.tradeButtonText, { color: colors.background }]}>
          Trade Now
        </Text>
      </TouchableOpacity>
    </TouchableOpacity>
  );

  const renderOrderModal = () => {
    if (!selectedOpportunity) return null;

    const positionSize = parseFloat(orderAmount || '0') * parseFloat(orderPrice || '0');
    const maxPosition = riskMetrics?.max_position_size || 1000;
    const availableCapital = riskMetrics?.available_capital || 0;

    return (
      <Modal
        visible={showOrderModal}
        animationType="slide"
        presentationStyle="pageSheet"
      >
        <SafeAreaView style={[styles.modalContainer, { backgroundColor: colors.background }]}>
          <View style={styles.modalHeader}>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setShowOrderModal(false)}
            >
              <Icon name="close" size={24} color={colors.text} />
            </TouchableOpacity>
            <Text style={[styles.modalTitle, { color: colors.text }]}>
              Place Order
            </Text>
            <View style={styles.placeholder} />
          </View>

          <ScrollView style={styles.modalContent}>
            <View style={[styles.marketInfoCard, { backgroundColor: colors.surface }]}>
              <Text style={[styles.marketTitle, { color: colors.text }]} numberOfLines={3}>
                {selectedOpportunity.market_title}
              </Text>
              <View style={styles.marketInfoRow}>
                <Text style={[styles.marketInfoLabel, { color: colors.textSecondary }]}>
                  Current Price:
                </Text>
                <Text style={[styles.marketInfoValue, { color: colors.text }]}>
                  ${selectedOpportunity.market_current_price?.toFixed(2) || 'N/A'}
                </Text>
              </View>
              <View style={styles.marketInfoRow}>
                <Text style={[styles.marketInfoLabel, { color: colors.textSecondary }]}>
                  Confidence:
                </Text>
                <Text style={[styles.marketInfoValue, { color: colors.text }]}>
                  {(selectedOpportunity.confidence * 100).toFixed(1)}%
                </Text>
              </View>
            </View>

            <View style={[styles.orderTypeSelector, { backgroundColor: colors.surface }]}>
              <Text style={[styles.sectionTitle, { color: colors.text }]}>
                Order Type
              </Text>
              <View style={styles.orderTypeButtons}>
                <TouchableOpacity
                  style={[
                    styles.orderTypeButton,
                    orderType === 'yes' && styles.orderTypeButtonActive,
                    {
                      backgroundColor: orderType === 'yes' ? colors.success : colors.background,
                      borderColor: colors.border
                    }
                  ]}
                  onPress={() => setOrderType('yes')}
                >
                  <Text style={[
                    styles.orderTypeButtonText,
                    { color: orderType === 'yes' ? colors.background : colors.text }
                  ]}>
                    YES
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[
                    styles.orderTypeButton,
                    orderType === 'no' && styles.orderTypeButtonActive,
                    {
                      backgroundColor: orderType === 'no' ? colors.error : colors.background,
                      borderColor: colors.border
                    }
                  ]}
                  onPress={() => setOrderType('no')}
                >
                  <Text style={[
                    styles.orderTypeButtonText,
                    { color: orderType === 'no' ? colors.background : colors.text }
                  ]}>
                    NO
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={[styles.orderForm, { backgroundColor: colors.surface }]}>
              <Text style={[styles.sectionTitle, { color: colors.text }]}>
                Order Details
              </Text>

              <View style={styles.formGroup}>
                <Text style={[styles.formLabel, { color: colors.text }]}>
                  Contract Count
                </Text>
                <TextInput
                  style={[
                    styles.textInput,
                    {
                      backgroundColor: colors.background,
                      borderColor: colors.border,
                      color: colors.text
                    }
                  ]}
                  placeholder="0"
                  placeholderTextColor={colors.textSecondary}
                  value={orderAmount}
                  onChangeText={setOrderAmount}
                  keyboardType="numeric"
                />
              </View>

              <View style={styles.formGroup}>
                <Text style={[styles.formLabel, { color: colors.text }]}>
                  Price per Contract ($)
                </Text>
                <TextInput
                  style={[
                    styles.textInput,
                    {
                      backgroundColor: colors.background,
                      borderColor: colors.border,
                      color: colors.text
                    }
                  ]}
                  placeholder="0.00"
                  placeholderTextColor={colors.textSecondary}
                  value={orderPrice}
                  onChangeText={setOrderPrice}
                  keyboardType="numeric"
                />
              </View>

              <View style={styles.positionSizeInfo}>
                <Text style={[styles.positionSizeLabel, { color: colors.textSecondary }]}>
                  Position Size
                </Text>
                <Text style={[styles.positionSizeValue, { color: colors.text }]}>
                  {formatCurrency(positionSize)}
                </Text>
              </View>

              {riskMetrics && (
                <View style={styles.riskInfo}>
                  <View style={styles.riskRow}>
                    <Text style={[styles.riskLabel, { color: colors.textSecondary }]}>
                      Available Capital:
                    </Text>
                    <Text style={[styles.riskValue, { color: colors.text }]}>
                      {formatCurrency(availableCapital)}
                    </Text>
                  </View>
                  <View style={styles.riskRow}>
                    <Text style={[styles.riskLabel, { color: colors.textSecondary }]}>
                      Max Position:
                    </Text>
                    <Text style={[styles.riskValue, { color: colors.text }]}>
                      {formatCurrency(maxPosition)}
                    </Text>
                  </View>
                </View>
              )}
            </View>

            <TouchableOpacity
              style={[
                styles.submitButton,
                {
                  backgroundColor: positionSize > 0 && positionSize <= maxPosition
                    ? colors.primary
                    : colors.border
                }
              ]}
              onPress={handleSubmitOrder}
              disabled={isSubmitting || positionSize <= 0 || positionSize > maxPosition}
            >
              {isSubmitting ? (
                <ActivityIndicator size="small" color={colors.background} />
              ) : (
                <Text style={[styles.submitButtonText, { color: colors.background }]}>
                  Place {orderType.toUpperCase()} Order
                </Text>
              )}
            </TouchableOpacity>
          </ScrollView>
        </SafeAreaView>
      </Modal>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            Loading trading opportunities...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.text }]}>
          Trading
        </Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
          AI-powered trading opportunities
        </Text>
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.text }]}>
            Top Opportunities
          </Text>
          <TouchableOpacity
            onPress={() => navigation.navigate('Analysis')}
          >
            <Text style={[styles.seeAllText, { color: colors.primary }]}>
              See All
            </Text>
          </TouchableOpacity>
        </View>

        {opportunities.length > 0 ? (
          opportunities.map(renderOpportunityCard)
        ) : (
          <View style={[styles.emptyState, { backgroundColor: colors.surface }]}>
            <Icon name="insights" size={48} color={colors.textSecondary} />
            <Text style={[styles.emptyStateText, { color: colors.textSecondary }]}>
              No trading opportunities available at the moment
            </Text>
          </View>
        )}

        {positions.length > 0 && (
          <View style={styles.sectionHeader}>
            <Text style={[styles.sectionTitle, { color: colors.text }]}>
              Active Positions
            </Text>
            <TouchableOpacity
              onPress={() => navigation.navigate('Portfolio')}
            >
              <Text style={[styles.seeAllText, { color: colors.primary }]}>
                Manage
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {positions.slice(0, 3).map((position) => (
          <View
            key={position.position_id}
            style={[styles.positionCard, { backgroundColor: colors.surface }]}
          >
            <View style={styles.positionHeader}>
              <Text style={[styles.positionTitle, { color: colors.text }]} numberOfLines={2}>
                {position.market_title}
              </Text>
              <View style={[
                styles.positionPill,
                { backgroundColor: position.pnl >= 0 ? `${colors.success}20` : `${colors.error}20` }
              ]}>
                <Text style={[
                  styles.positionPillText,
                  { color: position.pnl >= 0 ? colors.success : colors.error }
                ]}>
                  {position.side.toUpperCase()}
                </Text>
              </View>
            </View>
            <View style={styles.positionMetrics}>
              <View style={styles.positionMetric}>
                <Text style={[styles.positionMetricLabel, { color: colors.textSecondary }]}>
                  P&L
                </Text>
                <Text style={[
                  styles.positionMetricValue,
                  { color: position.pnl >= 0 ? colors.success : colors.error }
                ]}>
                  {formatCurrency(position.pnl)}
                </Text>
              </View>
              <View style={styles.positionMetric}>
                <Text style={[styles.positionMetricLabel, { color: colors.textSecondary }]}>
                  Contracts
                </Text>
                <Text style={[styles.positionMetricValue, { color: colors.text }]}>
                  {position.count}
                </Text>
              </View>
              <View style={styles.positionMetric}>
                <Text style={[styles.positionMetricLabel, { color: colors.textSecondary }]}>
                  Avg Price
                </Text>
                <Text style={[styles.positionMetricValue, { color: colors.text }]}>
                  ${position.average_price.toFixed(2)}
                </Text>
              </View>
            </View>
          </View>
        ))}
      </ScrollView>

      {renderOrderModal()}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
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
  header: {
    padding: 16,
    paddingBottom: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
  },
  content: {
    flex: 1,
    paddingHorizontal: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  seeAllText: {
    fontSize: 14,
    fontWeight: '500',
  },
  opportunityCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  opportunityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  opportunityTitleContainer: {
    flex: 1,
    marginRight: 12,
  },
  opportunityTitle: {
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 22,
    marginBottom: 4,
  },
  opportunityCategory: {
    fontSize: 12,
    textTransform: 'capitalize',
  },
  signalBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  signalText: {
    fontSize: 10,
    fontWeight: '600',
  },
  opportunityMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  metricColumn: {
    alignItems: 'center',
  },
  metricLabel: {
    fontSize: 12,
    marginBottom: 2,
  },
  metricValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  opportunityPrice: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  priceLabel: {
    fontSize: 14,
  },
  priceValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  tradeButton: {
    backgroundColor: '#4F46E5',
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
  },
  tradeButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  emptyState: {
    borderRadius: 12,
    padding: 32,
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyStateText: {
    marginTop: 12,
    fontSize: 14,
    textAlign: 'center',
  },
  positionCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  positionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  positionTitle: {
    flex: 1,
    fontSize: 14,
    fontWeight: '500',
    lineHeight: 20,
    marginRight: 12,
  },
  positionPill: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  positionPillText: {
    fontSize: 10,
    fontWeight: '600',
  },
  positionMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  positionMetric: {
    alignItems: 'center',
  },
  positionMetricLabel: {
    fontSize: 12,
    marginBottom: 2,
  },
  positionMetricValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  modalContainer: {
    flex: 1,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  closeButton: {
    padding: 4,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  placeholder: {
    width: 32,
  },
  modalContent: {
    flex: 1,
    padding: 16,
  },
  marketInfoCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  marketTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  marketInfoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  marketInfoLabel: {
    fontSize: 14,
  },
  marketInfoValue: {
    fontSize: 14,
    fontWeight: '500',
  },
  orderTypeSelector: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  orderTypeButtons: {
    flexDirection: 'row',
    marginTop: 12,
  },
  orderTypeButton: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderWidth: 1,
  },
  orderTypeButtonActive: {},
  orderTypeButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  orderForm: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  formGroup: {
    marginBottom: 16,
  },
  formLabel: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 8,
  },
  textInput: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  positionSizeInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    marginTop: 16,
  },
  positionSizeLabel: {
    fontSize: 14,
    fontWeight: '500',
  },
  positionSizeValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  riskInfo: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  riskRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  riskLabel: {
    fontSize: 12,
  },
  riskValue: {
    fontSize: 12,
    fontWeight: '500',
  },
  submitButton: {
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  submitButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
});

export default TradingScreen;