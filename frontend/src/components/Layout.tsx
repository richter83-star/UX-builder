import React from 'react';
import { Alert, Layout as AntLayout, Menu, Space, Switch, Tooltip, Typography } from 'antd';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { InfoCircleOutlined } from '@ant-design/icons';
import { useCopy } from '../hooks/useCopy';

const { Header, Content } = AntLayout;
const { Text } = Typography;

const Layout: React.FC = () => {
  const location = useLocation();
  const selectedKey = location.pathname.split('/')[1] || 'dashboard';
  const { copy, mode, toggleMode } = useCopy();

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ color: '#fff', fontWeight: 700, marginRight: 8 }}>Kalshi Agent</div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={[
            { key: 'dashboard', label: <Link to="/dashboard">Dashboard</Link> },
            { key: 'markets', label: <Link to="/markets">Markets</Link> },
            { key: 'watchlist', label: <Link to="/watchlist">Watchlist</Link> },
            { key: 'alerts', label: <Link to="/alerts">Alerts</Link> },
          ]}
        />
        <Space style={{ marginLeft: 'auto' }} align="center">
          <Switch
            checkedChildren={copy.banner.toggleLabel}
            unCheckedChildren={copy.banner.toggleLabel}
            checked={mode === 'money'}
            onChange={toggleMode}
          />
          <Text style={{ color: '#fff' }}>{copy.banner.title}</Text>
          <Tooltip title={copy.dashboard.tooltip} color="#1890ff">
            <InfoCircleOutlined style={{ color: '#fff' }} />
          </Tooltip>
        </Space>
      </Header>
      <Alert
        type="info"
        showIcon
        message={copy.banner.title}
        description={
          <div>
            <div>{copy.banner.line1}</div>
            <div>{copy.banner.line2}</div>
          </div>
        }
      />
      <Content style={{ padding: '24px' }}>
        <Outlet />
      </Content>
    </AntLayout>
  );
};

export default Layout;
