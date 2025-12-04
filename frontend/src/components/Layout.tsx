import React from 'react';
import { Layout as AntLayout, Menu } from 'antd';
import { Link, Outlet, useLocation } from 'react-router-dom';

const { Header, Content } = AntLayout;

const Layout: React.FC = () => {
  const location = useLocation();
  const selectedKey = location.pathname.split('/')[1] || 'dashboard';

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ color: '#fff', fontWeight: 700, marginRight: 24 }}>Kalshi Agent</div>
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
      </Header>
      <Content style={{ padding: '24px' }}>
        <Outlet />
      </Content>
    </AntLayout>
  );
};

export default Layout;
