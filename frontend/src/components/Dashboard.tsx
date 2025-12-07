import React from 'react';
import { Button, Card, Space, Tooltip, Typography } from 'antd';
import { InfoCircleOutlined, SafetyOutlined, ThunderboltOutlined, FileSearchOutlined } from '@ant-design/icons';
import { useCopy } from '../hooks/useCopy';

const { Title, Paragraph, Text } = Typography;

const Dashboard: React.FC = () => {
  const { copy } = useCopy();

  return (
    <Card>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Space align="center">
          <Title level={3} style={{ margin: 0 }}>
            {copy.dashboard.headline}
          </Title>
          <Tooltip title={copy.dashboard.tooltip}>
            <InfoCircleOutlined />
          </Tooltip>
        </Space>
        <Paragraph>{copy.signals.microcopy}</Paragraph>
        <Space wrap>
          <Button type="primary" icon={<ThunderboltOutlined />}>
            {copy.dashboard.primaryCta}
          </Button>
          <Button icon={<SafetyOutlined />}>{copy.dashboard.secondaryCta}</Button>
          <Button icon={<FileSearchOutlined />}>{copy.dashboard.tertiaryCta}</Button>
        </Space>
        <Paragraph type="secondary">
          <Text strong>{copy.signals.title}</Text>: {copy.dashboard.tooltip}
        </Paragraph>
      </Space>
    </Card>
  );
};

export default Dashboard;
