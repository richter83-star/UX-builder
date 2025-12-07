import React, { useEffect, useState } from 'react';
import { Card, Input, List, Button, Tag, Space, Typography } from 'antd';
import apiService from '../services/api';
import { Market } from '../types';

const { Title, Text } = Typography;

const Markets: React.FC = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');

  useEffect(() => {
    const fetchMarkets = async () => {
      setLoading(true);
      try {
        const data = await apiService.getMarkets({ search: query, limit: 20 });
        setMarkets(data);
      } finally {
        setLoading(false);
      }
    };
    fetchMarkets();
  }, [query]);

  const handleTrack = async (ticker: string, canTrack: boolean) => {
    if (!canTrack) return;
    await apiService.trackMarket(ticker);
    setMarkets((prev) =>
      prev.map((m) => (m.market_id === ticker ? { ...m } : m))
    );
  };

  const handleRequest = async (ticker: string) => {
    await apiService.requestMarket({ market_ticker: ticker });
  };

  return (
    <Card loading={loading} title={<Title level={4}>Markets</Title>}>
      <Input.Search
        placeholder="Search markets"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ marginBottom: 16 }}
      />
      <List
        dataSource={markets}
        renderItem={(item) => (
          <List.Item
            actions={[
              item.can_track ? (
                <Button type="primary" onClick={() => handleTrack(item.market_id, item.can_track)}>
                  Track
                </Button>
              ) : (
                <Button onClick={() => handleRequest(item.market_id)}>Request access</Button>
              )
            ]}
          >
            <List.Item.Meta
              title={
                <Space>
                  <span>{item.title}</span>
                  {item.access_status && (
                    <Tag color={item.can_track ? 'green' : 'orange'}>{item.access_status}</Tag>
                  )}
                </Space>
              }
              description={item.subtitle}
            />
            <div>
              <Text type="secondary">Settle: {item.settle_date ? new Date(item.settle_date).toLocaleString() : 'TBD'}</Text>
            </div>
          </List.Item>
        )}
      />
    </Card>
  );
};

export default Markets;
