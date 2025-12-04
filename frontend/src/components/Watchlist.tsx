import React, { useEffect, useState } from 'react';
import { Card, List, Button, Drawer, Space, Switch, InputNumber, Tag, Typography, Progress } from 'antd';
import apiService from '../services/api';
import { WatchlistEntry, OverridePayload } from '../types';

const { Title, Text } = Typography;

const Watchlist: React.FC = () => {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [openTicker, setOpenTicker] = useState<string | null>(null);
  const [override, setOverride] = useState<OverridePayload>({});

  const load = async () => {
    setLoading(true);
    const data = await apiService.getWatchlist();
    setEntries(data);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const openOverride = async (ticker: string) => {
    try {
      const data = await apiService.getOverride(ticker);
      setOverride(data);
    } catch {
      setOverride({});
    }
    setOpenTicker(ticker);
  };

  const saveOverride = async () => {
    if (!openTicker) return;
    await apiService.saveOverride(openTicker, override);
    setOpenTicker(null);
    await load();
  };

  const trackedCount = entries.length;
  const cap = 25;

  return (
    <Card title={<Title level={4}>Watchlist ({trackedCount}/{cap})</Title>} loading={loading}>
      <List
        dataSource={entries}
        renderItem={(item) => (
          <List.Item
            actions=[
              <Button key="override" onClick={() => openOverride(item.market_ticker)}>
                ⚙ Override
              </Button>,
              <Tag key="trace" color={item.decision_trace.includes('blocked') ? 'red' : 'blue'}>
                {item.decision_trace}
              </Tag>,
            ]
          >
            <List.Item.Meta
              title={item.market_ticker}
              description={
                <Space direction="vertical">
                  <Text type="secondary">
                    Expires {new Date(item.expires_at).toLocaleString()}
                  </Text>
                  <Space>
                    <Text>Alerts</Text>
                    <Switch checked={item.alerts_enabled} disabled />
                  </Space>
                </Space>
              }
            />
          </List.Item>
        )}
      />
      <Drawer
        title={`Overrides for ${openTicker}`}
        open={!!openTicker}
        onClose={() => setOpenTicker(null)}
        width={400}
        footer={<Button type="primary" onClick={saveOverride}>Save</Button>}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Text>Alerts enabled</Text>
            <Switch
              checked={override.alerts_enabled ?? undefined}
              onChange={(val) => setOverride({ ...override, alerts_enabled: val })}
            />
          </Space>
          <Space>
            <Text>Edge threshold</Text>
            <InputNumber
              value={override.edge_threshold ?? undefined}
              onChange={(val) => setOverride({ ...override, edge_threshold: Number(val) })}
              step={0.01}
              min={0}
              max={1}
            />
          </Space>
          <Space>
            <Text>Min liquidity</Text>
            <InputNumber
              value={override.min_liquidity ?? undefined}
              onChange={(val) => setOverride({ ...override, min_liquidity: Number(val) })}
            />
          </Space>
          <Space>
            <Text>Max spread</Text>
            <InputNumber
              value={override.max_spread ?? undefined}
              onChange={(val) => setOverride({ ...override, max_spread: Number(val) })}
            />
          </Space>
        </Space>
      </Drawer>
    </Card>
  );
};

export default Watchlist;
