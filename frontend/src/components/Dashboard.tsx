import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Progress,
  Table,
  Tag,
  Button,
  Space,
  Alert,
  Spin,
  Empty,
  Typography,
  Divider,
} from 'antd';
import {
  DollarOutlined,
  TrophyOutlined,
  RiseOutlined,
  FallOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { motion } from 'framer-motion';

import { useQuery } from 'react-query';
import {
  PortfolioMetrics,
  TradingOpportunity,
  Position,
  RiskMetrics,
} from '../types';
import apiService from '../services/api';
import webSocketService from '../services/websocket';
import useAuthStore from '../hooks/useAuth';
import PerformanceChart from './PerformanceChart';
import OpportunityList from './OpportunityList';

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  const { user } = useAuthStore();
  const [selectedTimeRange, setSelectedTimeRange] = useState(7); // days

  // WebSocket callbacks
  useEffect(() => {
    webSocketService.updateCallbacks({
      onPositionUpdate: (data) => {
        // Invalidate and refetch portfolio metrics
        portfolioMetricsQuery.refetch();
        positionsQuery.refetch();
      },
      onOpportunityAlert: (data) => {
        // Invalidate and refetch opportunities
        opportunitiesQuery.refetch();
      },
      onRiskAlert: (data) => {
        // Show risk alert notification
        console.log('Risk alert received:', data);
      },
      onTradeExecuted: (data) => {
        // Refetch portfolio and positions
        portfolioMetricsQuery.refetch();
        positionsQuery.refetch();
      },
    });
  }, []);

  // Queries for dashboard data
  const portfolioMetricsQuery = useQuery(
    'portfolioMetrics',
    apiService.getPortfolioMetrics,
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      staleTime: 10000,
    }
  );

  const opportunitiesQuery = useQuery(
    'topOpportunities',
    () => apiService.getTradingOpportunities({ limit: 10 }),
    {
      refetchInterval: 60000, // Refetch every minute
      staleTime: 30000,
    }
  );

  const positionsQuery = useQuery(
    'positions',
    () => apiService.getPositions({ limit: 5 }),
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      staleTime: 10000,
    }
  );

  const riskMetricsQuery = useQuery(
    'riskMetrics',
    apiService.getRiskMetrics,
    {
      refetchInterval: 60000, // Refetch every minute
      staleTime: 30000,
    }
  );

  const performanceQuery = useQuery(
    ['portfolioPerformance', selectedTimeRange],
    () => apiService.getPortfolioPerformance(selectedTimeRange),
    {
      staleTime: 60000,
    }
  );

  // Manual refresh handlers
  const refreshAll = () => {
    portfolioMetricsQuery.refetch();
    opportunitiesQuery.refetch();
    positionsQuery.refetch();
    riskMetricsQuery.refetch();
    performanceQuery.refetch();
  };

  // Loading state
  const isLoading =
    portfolioMetricsQuery.isLoading ||
    opportunitiesQuery.isLoading ||
    positionsQuery.isLoading ||
    riskMetricsQuery.isLoading;

  // Error state
  const hasError =
    portfolioMetricsQuery.error ||
    opportunitiesQuery.error ||
    positionsQuery.error ||
    riskMetricsQuery.error;

  // Portfolio metrics data
  const portfolioMetrics = portfolioMetricsQuery.data;

  // Position table columns
  const positionColumns = [
    {
      title: 'Market',
      dataIndex: 'market_title',
      key: 'market_title',
      ellipsis: true,
    },
    {
      title: 'Side',
      dataIndex: 'side',
      key: 'side',
      render: (side: string) => (
        <Tag color={side === 'yes' ? 'green' : 'red'}>
          {side.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Unrealized P&L',
      dataIndex: 'unrealized_pnl',
      key: 'unrealized_pnl',
      render: (pnl: number, record: Position) => (
        <div>
          <Text strong style={{
            color: pnl >= 0 ? '#52c41a' : '#ff4d4f'
          }}>
            ${Math.abs(pnl).toFixed(2)}
          </Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {pnl >= 0 ? '+' : ''}{record.unrealized_pnl_percent.toFixed(1)}%
          </Text>
        </div>
      ),
      sorter: (a: Position, b: Position) => a.unrealized_pnl - b.unrealized_pnl,
    },
    {
      title: 'Risk Level',
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (level: string) => {
        const colors = {
          low: 'green',
          medium: 'orange',
          high: 'red',
          critical: 'magenta',
        };
        return <Tag color={colors[level as keyof typeof colors]}>{level.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Duration',
      dataIndex: 'duration_hours',
      key: 'duration_hours',
      render: (hours: number) => `${Math.round(hours)}h`,
    },
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="dashboard-title">
          <Title level={2}>
            Welcome back, {user?.email?.split('@')[0]}! 👋
          </Title>
          <Text type="secondary">
            Here's your trading overview for today
          </Text>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={refreshAll}
            loading={isLoading}
          >
            Refresh
          </Button>
        </Space>
      </div>

      {hasError && (
        <Alert
          message="Error loading dashboard data"
          description="Please try refreshing the page or contact support if the issue persists."
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
          action={
            <Button size="small" onClick={refreshAll}>
              Retry
            </Button>
          }
        />
      )}

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Portfolio Overview Cards */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} lg={6}>
              <motion.div whileHover={{ scale: 1.02 }}>
                <Card>
                  <Statistic
                    title="Total Portfolio Value"
                    value={portfolioMetrics?.total_value || 0}
                    precision={2}
                    prefix={<DollarOutlined />}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </motion.div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <motion.div whileHover={{ scale: 1.02 }}>
                <Card>
                  <Statistic
                    title="Daily P&L"
                    value={portfolioMetrics?.daily_pnl || 0}
                    precision={2}
                    prefix={portfolioMetrics?.daily_pnl >= 0 ? <RiseOutlined /> : <FallOutlined />}
                    valueStyle={{
                      color: portfolioMetrics?.daily_pnl >= 0 ? '#52c41a' : '#ff4d4f'
                    }}
                  />
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {portfolioMetrics?.daily_pnl_percent?.toFixed(1) || 0}%
                  </Text>
                </Card>
              </motion.div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <motion.div whileHover={{ scale: 1.02 }}>
                <Card>
                  <Statistic
                    title="Win Rate"
                    value={portfolioMetrics?.win_rate || 0}
                    precision={1}
                    suffix="%"
                    prefix={<TrophyOutlined />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </motion.div>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <motion.div whileHover={{ scale: 1.02 }}>
                <Card>
                  <Statistic
                    title="Active Positions"
                    value={portfolioMetrics?.number_of_positions || 0}
                    prefix={<EyeOutlined />}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </motion.div>
            </Col>
          </Row>

          {/* Risk Metrics Alert */}
          {riskMetricsQuery.data && (
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col span={24}>
                {riskMetricsQuery.data.emergency_stop_active && (
                  <Alert
                    message="⚠️ EMERGENCY STOP ACTIVE"
                    description="All automated trading has been halted due to risk management rules."
                    type="error"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}

                {riskMetricsQuery.data.current_drawdown > 10 && (
                  <Alert
                    message="High Drawdown Warning"
                    description={`Current drawdown: ${riskMetricsQuery.data.current_drawdown.toFixed(1)}%`}
                    type="warning"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}
              </Col>
            </Row>
          )}

          {/* Main Content Grid */}
          <Row gutter={[16, 16]}>
            {/* Performance Chart */}
            <Col xs={24} lg={16}>
              <Card
                title="Portfolio Performance"
                extra={
                  <Space>
                    <Button.Group>
                      <Button
                        size="small"
                        type={selectedTimeRange === 7 ? 'primary' : 'default'}
                        onClick={() => setSelectedTimeRange(7)}
                      >
                        7D
                      </Button>
                      <Button
                        size="small"
                        type={selectedTimeRange === 30 ? 'primary' : 'default'}
                        onClick={() => setSelectedTimeRange(30)}
                      >
                        30D
                      </Button>
                      <Button
                        size="small"
                        type={selectedTimeRange === 90 ? 'primary' : 'default'}
                        onClick={() => setSelectedTimeRange(90)}
                      >
                        90D
                      </Button>
                    </Button.Group>
                  </Space>
                }
              >
                {performanceQuery.data ? (
                  <PerformanceChart data={performanceQuery.data} />
                ) : (
                  <Empty description="No performance data available" />
                )}
              </Card>
            </Col>

            {/* Risk Overview */}
            <Col xs={24} lg={8}>
              <Card title="Risk Overview">
                {riskMetricsQuery.data ? (
                  <div>
                    <div style={{ marginBottom: 16 }}>
                      <Text strong>Current Drawdown</Text>
                      <Progress
                        percent={riskMetricsQuery.data.current_drawdown}
                        status={riskMetricsQuery.data.current_drawdown > 15 ? 'exception' :
                               riskMetricsQuery.data.current_drawdown > 10 ? 'active' : 'success'}
                        format={(percent) => `${percent?.toFixed(1)}%`}
                      />
                    </div>

                    <div style={{ marginBottom: 16 }}>
                      <Text strong>Daily Loss Limit</Text>
                      <Progress
                        percent={Math.abs(riskMetricsQuery.data.daily_pnl / (riskMetricsQuery.data.portfolio_value * 0.02)) * 100}
                        status="normal"
                        format={() => `${Math.abs(riskMetricsQuery.data.daily_pnl || 0).toFixed(2)}`}
                      />
                    </div>

                    <Divider />

                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <Text>Daily Trades: {riskMetricsQuery.data.daily_trades_count}</Text>
                      </div>
                      <div>
                        <Text>Emergency Stop: </Text>
                        <Tag color={riskMetricsQuery.data.emergency_stop_active ? 'red' : 'green'}>
                          {riskMetricsQuery.data.emergency_stop_active ? 'ACTIVE' : 'INACTIVE'}
                        </Tag>
                      </div>
                    </Space>
                  </div>
                ) : (
                  <Empty description="Risk data unavailable" />
                )}
              </Card>
            </Col>
          </Row>

          {/* Opportunities and Positions */}
          <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
            {/* Top Opportunities */}
            <Col xs={24} lg={12}>
              <OpportunityList
                title="Top Trading Opportunities"
                opportunities={opportunitiesQuery.data || []}
                loading={opportunitiesQuery.isLoading}
                showAllLink="/analysis"
              />
            </Col>

            {/* Recent Positions */}
            <Col xs={24} lg={12}>
              <Card
                title="Recent Positions"
                extra={
                  <Button type="link" href="/portfolio">
                    View All
                  </Button>
                }
              >
                {positionsQuery.data && positionsQuery.data.length > 0 ? (
                  <Table
                    dataSource={positionsQuery.data}
                    columns={positionColumns}
                    pagination={false}
                    size="small"
                    rowKey="position_id"
                  />
                ) : (
                  <Empty description="No open positions" />
                )}
              </Card>
            </Col>
          </Row>
        </motion.div>
      )}
    </div>
  );
};

export default Dashboard;