import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import apiService from '../../services/ApiService';
import { LineChart, BarChart, PieChart, ProgressChart } from '../../components/charts';
import {
  TradingOpportunity,
  Market,
  PortfolioMetrics,
  EnsembleAnalysis,
} from '../../types';

const AnalysisScreen: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [opportunities, setOpportunities] = useState<TradingOpportunity[]>([]);
  const [ensembleAnalysis, setEnsembleAnalysis] = useState<EnsembleAnalysis | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<'1d' | '1w' | '1m' | '3m'>('1w');
  const [selectedChart, setSelectedChart] = useState<'performance' | 'distribution' | 'predictions'>('performance');
  const { theme, colors } = useTheme();
  const { authState } = useAuth();

  const loadAnalysisData = useCallback(async () => {
    if (!authState.isAuthenticated) return;

    try {
      const [opportunitiesData, analysisData] = await Promise.all([
        apiService.getTradingOpportunities({ limit: 100 }),
        apiService.getEnsembleAnalysis(),
      ]);

      setOpportunities(opportunitiesData);
      setEnsembleAnalysis(analysisData);
    } catch (error) {
      console.error('Error loading analysis data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [authState.isAuthenticated]);

  useEffect(() => {
    loadAnalysisData();
  }, [loadAnalysisData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadAnalysisData();
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

  const getSignalDistribution = () => {
    const distribution = {
      strong_buy: 0,
      buy: 0,
      hold: 0,
      sell: 0,
      strong_sell: 0,
    };

    opportunities.forEach((opp) => {
      const signal = opp.signal_classification.toLowerCase();
      if (distribution.hasOwnProperty(signal)) {
        distribution[signal as keyof typeof distribution]++;
      }
    });

    return Object.entries(distribution)
      .filter(([_, count]) => count > 0)
      .map(([name, count]) => ({
        name: name.replace('_', ' ').toUpperCase(),
        population: count,
        color: getSignalColor(name),
      }));
  };

  const getSignalColor = (signal: string): string => {
    switch (signal.toLowerCase()) {
      case 'strong_buy':
        return '#10B981';
      case 'buy':
        return '#34D399';
      case 'hold':
        return '#F59E0B';
      case 'sell':
        return '#F87171';
      case 'strong_sell':
        return '#EF4444';
      default:
        return '#6B7280';
    }
  };

  const getPerformanceData = () => {
    if (!ensembleAnalysis) return { labels: [], datasets: [{ data: [] }] };

    const periods = {
      '1d': { labels: ['12AM', '4AM', '8AM', '12PM', '4PM', '8PM'], data: [100, 102, 98, 105, 103, 107] },
      '1w': { labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], data: [100, 103, 101, 108, 106, 110, 112] },
      '1m': { labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'], data: [100, 105, 108, 115] },
      '3m': { labels: ['Month 1', 'Month 2', 'Month 3'], data: [100, 112, 125] },
    };

    const periodData = periods[selectedPeriod];

    return {
      labels: periodData.labels,
      datasets: [{
        data: periodData.data,
        color: (opacity = 1) => `rgba(79, 70, 229, ${opacity})`,
        strokeWidth: 2,
      }],
    };
  };

  const getConfidenceDistribution = () => {
    if (!ensembleAnalysis) return { labels: [], data: [] };

    return {
      labels: ['Sentiment', 'Statistical', 'ML Model', 'Ensemble'],
      data: [0.85, 0.78, 0.82, 0.88],
    };
  };

  const renderPerformanceChart = () => (
    <View style={[styles.chartCard, { backgroundColor: colors.surface }]}>
      <View style={styles.chartHeader}>
        <Text style={[styles.chartTitle, { color: colors.text }]}>
          Portfolio Performance
        </Text>
        <View style={styles.periodSelector}>
          {(['1d', '1w', '1m', '3m'] as const).map((period) => (
            <TouchableOpacity
              key={period}
              style={[
                styles.periodButton,
                selectedPeriod === period && styles.periodButtonActive,
                {
                  backgroundColor: selectedPeriod === period ? colors.primary : `${colors.primary}20`,
                }
              ]}
              onPress={() => setSelectedPeriod(period)}
            >
              <Text style={[
                styles.periodButtonText,
                { color: selectedPeriod === period ? colors.background : colors.primary }
              ]}>
                {period}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
      <LineChart data={getPerformanceData()} />
      <View style={styles.chartStats}>
        <View style={styles.statItem}>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            Total Return
          </Text>
          <Text style={[styles.statValue, { color: colors.success }]}>
            +15.2%
          </Text>
        </View>
        <View style={styles.statItem}>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            Win Rate
          </Text>
          <Text style={[styles.statValue, { color: colors.text }]}>
            68.5%
          </Text>
        </View>
        <View style={styles.statItem}>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            Sharpe Ratio
          </Text>
          <Text style={[styles.statValue, { color: colors.text }]}>
            1.85
          </Text>
        </View>
      </View>
    </View>
  );

  const renderSignalDistribution = () => (
    <View style={[styles.chartCard, { backgroundColor: colors.surface }]}>
      <Text style={[styles.chartTitle, { color: colors.text }]}>
        Signal Distribution
      </Text>
      <PieChart
        data={getSignalDistribution()}
        height={200}
        showLegend={true}
      />
      <View style={styles.legendContainer}>
        {getSignalDistribution().map((item) => (
          <View key={item.name} style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: item.color }]} />
            <Text style={[styles.legendText, { color: colors.textSecondary }]}>
              {item.name}: {item.population}
            </Text>
          </View>
        ))}
      </View>
    </View>
  );

  const renderModelPerformance = () => (
    <View style={[styles.chartCard, { backgroundColor: colors.surface }]}>
      <Text style={[styles.chartTitle, { color: colors.text }]}>
        Model Confidence Scores
      </Text>
      <ProgressChart
        data={getConfidenceDistribution()}
        height={180}
        strokeWidth={12}
        radius={30}
      />
      <View style={styles.modelInfo}>
        <Text style={[styles.modelDescription, { color: colors.textSecondary }]}>
          Ensemble model combines sentiment analysis, statistical patterns, and machine learning predictions
          to generate trading signals with confidence scores.
        </Text>
      </View>
    </View>
  );

  const renderOpportunityAnalysis = () => (
    <View style={[styles.chartCard, { backgroundColor: colors.surface }]}>
      <Text style={[styles.chartTitle, { color: colors.text }]}>
        Opportunity Analysis
      </Text>
      <View style={styles.analysisGrid}>
        <View style={styles.analysisItem}>
          <Icon name="trending-up" size={24} color={colors.success} />
          <Text style={[styles.analysisValue, { color: colors.text }]}>
            {opportunities.length}
          </Text>
          <Text style={[styles.analysisLabel, { color: colors.textSecondary }]}>
            Total Opportunities
          </Text>
        </View>
        <View style={styles.analysisItem}>
          <Icon name="check-circle" size={24} color={colors.success} />
          <Text style={[styles.analysisValue, { color: colors.text }]}>
            {opportunities.filter(o => o.confidence > 0.8).length}
          </Text>
          <Text style={[styles.analysisLabel, { color: colors.textSecondary }]}>
            High Confidence
          </Text>
        </View>
        <View style={styles.analysisItem}>
          <Icon name="security" size={24} color={colors.warning} />
          <Text style={[styles.analysisValue, { color: colors.text }]}>
            {opportunities.filter(o => o.risk_score <= 5).length}
          </Text>
          <Text style={[styles.analysisLabel, { color: colors.textSecondary }]}>
            Low Risk
          </Text>
        </View>
        <View style={styles.analysisItem}>
          <Icon name="insights" size={24} color={colors.primary} />
          <Text style={[styles.analysisValue, { color: colors.text }]}>
            {(opportunities.reduce((acc, o) => acc + o.confidence, 0) / opportunities.length).toFixed(2)}
          </Text>
          <Text style={[styles.analysisLabel, { color: colors.textSecondary }]}>
            Avg Confidence
          </Text>
        </View>
      </View>
    </View>
  );

  const renderChartSelector = () => (
    <View style={styles.chartSelectorContainer}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={styles.chartSelector}>
          {[
            { key: 'performance', label: 'Performance', icon: 'trending-up' },
            { key: 'distribution', label: 'Signals', icon: 'pie-chart' },
            { key: 'predictions', label: 'Models', icon: 'psychology' },
          ].map((chart) => (
            <TouchableOpacity
              key={chart.key}
              style={[
                styles.chartSelectorButton,
                selectedChart === chart.key && styles.chartSelectorButtonActive,
                {
                  backgroundColor: selectedChart === chart.key ? colors.primary : colors.surface,
                  borderColor: colors.border,
                }
              ]}
              onPress={() => setSelectedChart(chart.key as any)}
            >
              <Icon
                name={chart.icon as any}
                size={20}
                color={selectedChart === chart.key ? colors.background : colors.textSecondary}
              />
              <Text style={[
                styles.chartSelectorButtonText,
                { color: selectedChart === chart.key ? colors.background : colors.text }
              ]}>
                {chart.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </View>
  );

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            Loading analysis data...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView
        style={styles.content}
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
            Analysis
          </Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Ensemble analysis and model performance
          </Text>
        </View>

        {renderChartSelector()}

        {selectedChart === 'performance' && renderPerformanceChart()}
        {selectedChart === 'distribution' && renderSignalDistribution()}
        {selectedChart === 'predictions' && renderModelPerformance()}

        {renderOpportunityAnalysis()}
      </ScrollView>
    </SafeAreaView>
  );
};

export default AnalysisScreen;