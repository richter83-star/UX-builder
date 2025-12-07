import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';

import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Markets from './components/Markets';
import Watchlist from './components/Watchlist';
import AlertsSettings from './components/AlertsSettings';
import Analysis from './components/Analysis';
import Trading from './components/Trading';
import Portfolio from './components/Portfolio';
import RiskSettings from './components/RiskSettings';
import Login from './components/Login';
import Register from './components/Register';
import NotFound from './components/NotFound';
import { CopyProvider } from './hooks/useCopy';

import useAuthStore from './hooks/useAuth';

import './App.css';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

// Protected route component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Public route component (redirect if authenticated)
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

const App: React.FC = () => {
  const [mounted, setMounted] = useState(false);
  const { isAuthenticated, initializeAuth } = useAuthStore();

  useEffect(() => {
    setMounted(true);
    initializeAuth();
  }, [initializeAuth]);

  useEffect(() => {
    // WebSocket setup can be added when live automation is enabled
  }, [isAuthenticated]);

  // Don't render until mounted (prevents hydration issues)
  if (!mounted) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <CopyProvider>
        <ConfigProvider
          theme={{
            algorithm: theme.defaultAlgorithm,
            token: {
              colorPrimary: '#1890ff',
              colorSuccess: '#52c41a',
              colorWarning: '#faad14',
              colorError: '#ff4d4f',
              colorInfo: '#1890ff',
              borderRadius: 6,
              wireframe: false,
            },
            components: {
              Layout: {
                headerBg: '#001529',
                siderBg: '#001529',
              },
              Menu: {
                darkItemBg: '#001529',
                darkSubMenuItemBg: '#000c17',
                darkItemSelectedBg: '#1890ff',
              },
            },
          }}
        >
          <Router>
            <div className="App">
              <Routes>
                {/* Public routes */}
                <Route
                  path="/login"
                  element={
                    <PublicRoute>
                      <Login />
                    </PublicRoute>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <PublicRoute>
                      <Register />
                    </PublicRoute>
                  }
                />

                {/* Protected routes */}
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <Layout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="dashboard" element={<Dashboard />} />
                  <Route path="markets" element={<Markets />} />
                  <Route path="watchlist" element={<Watchlist />} />
                  <Route path="alerts" element={<AlertsSettings />} />
                  <Route path="analysis" element={<Analysis />} />
                  <Route path="trading" element={<Trading />} />
                  <Route path="portfolio" element={<Portfolio />} />
                  <Route path="risk-settings" element={<RiskSettings />} />
                </Route>

                {/* Fallback route */}
                <Route path="*" element={<NotFound />} />
              </Routes>

              {/* Global toast notifications */}
              <Toaster
                position="top-right"
                toastOptions={{
                  duration: 4000,
                  style: {
                    background: '#363636',
                    color: '#fff',
                  },
                  success: {
                    duration: 3000,
                    iconTheme: {
                      primary: '#52c41a',
                      secondary: '#fff',
                    },
                  },
                  error: {
                    duration: 5000,
                    iconTheme: {
                      primary: '#ff4d4f',
                      secondary: '#fff',
                    },
                  },
                }}
              />
            </div>
          </Router>
        </ConfigProvider>
      </CopyProvider>
    </QueryClientProvider>
  );
};

export default App;