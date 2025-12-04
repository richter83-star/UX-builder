import React from 'react';
import { Card, Typography } from 'antd';

const { Title, Paragraph } = Typography;

const Dashboard: React.FC = () => {
  return (
    <Card>
      <Title level={3}>Early access modes</Title>
      <Paragraph>
        Watchlist-only mode ships first: track up to 25 approved markets, manage per-market overrides on the
        Watchlist page, and review decision traces explaining why alerts fire or trades are blocked.
      </Paragraph>
    </Card>
  );
};

export default Dashboard;
