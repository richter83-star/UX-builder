import React, { useEffect, useState } from 'react';
import { Card, Switch, InputNumber, Select, Button, Space, Typography, Alert } from 'antd';
import apiService from '../services/api';
import { RuleDefaults } from '../types';

const { Title, Text } = Typography;

const AlertsSettings: React.FC = () => {
  const [rules, setRules] = useState<RuleDefaults | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const data = await apiService.getRules();
      setRules(data);
      setLoading(false);
    };
    load();
  }, []);

  const save = async () => {
    await apiService.updateRules(rules || {});
  };

  return (
    <Card title={<Title level={4}>Alert defaults</Title>} loading={loading}>
      <Alert
        type="info"
        message="Early access: email + daily digest enforced server-side"
        style={{ marginBottom: 16 }}
      />
      {rules && (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Text>Alerts enabled by default</Text>
            <Switch
              checked={rules.alerts_enabled_default}
              onChange={(val) => setRules({ ...rules, alerts_enabled_default: val })}
            />
          </Space>
          <Space>
            <Text>Edge threshold</Text>
            <InputNumber
              value={rules.edge_threshold_default}
              step={0.01}
              min={0}
              max={1}
              onChange={(val) => setRules({ ...rules, edge_threshold_default: Number(val) })}
            />
          </Space>
          <Space>
            <Text>Max alerts per day (tier capped at 10)</Text>
            <InputNumber
              value={rules.max_alerts_per_day}
              onChange={(val) => setRules({ ...rules, max_alerts_per_day: Number(val) })}
            />
          </Space>
          <Space>
            <Text>Digest mode</Text>
            <Select
              value={rules.digest_mode}
              onChange={(val) => setRules({ ...rules, digest_mode: val })}
              options={[{ value: 'daily', label: 'Daily (free tier)' }, { value: 'instant', label: 'Instant' }]}
            />
          </Space>
          <Button type="primary" onClick={save}>
            Save
          </Button>
        </Space>
      )}
    </Card>
  );
};

export default AlertsSettings;
