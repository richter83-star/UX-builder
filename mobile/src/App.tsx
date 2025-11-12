import React, { useEffect, useState } from 'react';
import {
  StatusBar,
  SafeAreaView,
  StyleSheet,
  View,
  LogBox,
  Platform,
  Alert,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { ThemeProvider } from './theme/ThemeProvider';
import { AuthProvider } from './contexts/AuthContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { AuthNavigator } from './navigation/AuthNavigator';
import { AppNavigator } from './navigation/AppNavigator';
import { useAuth } from './hooks/useAuth';
import { NotificationService } from './services/NotificationService';
import { WebSocketService } from './services/WebSocketService';
import SplashScreen from './components/SplashScreen';
import ErrorBoundary from './components/ErrorBoundary';
import { colors } from './theme/colors';

// Ignore common React Native warnings
LogBox.ignoreLogs(['VirtualizedLists should never be nested']);

const App: React.FC = () => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    // Initialize services
    const initializeServices = async () => {
      try {
        // Initialize notification service
        await NotificationService.initialize();

        // Setup notification channels
        await NotificationService.setupChannels();

        // Hide splash screen after initialization
        setTimeout(() => {
          setShowSplash(false);
        }, 2000);

        console.log('Mobile app services initialized');
      } catch (error) {
        console.error('Error initializing services:', error);
        setShowSplash(false);
      }
    };

    initializeServices();

    // Set up deep linking handler
    const handleDeepLink = (url: string) => {
      console.log('Deep link received:', url);
      // Handle deep linking logic here
    };

    if (Platform.OS === 'ios') {
      // Handle iOS deep linking
    } else {
      // Handle Android deep linking
    }
  }, []);

  const handleAppStateChange = (nextAppState: string) => {
    if (nextAppState === 'active') {
      // App came to foreground
      WebSocketService.reconnect();
    } else if (nextAppState === 'background') {
      // App went to background
      WebSocketService.pause();
    }
  };

  useEffect(() => {
    // Subscribe to app state changes
    const subscription = require('react-native').AppState?.addEventListener?.(
      'change',
      handleAppStateChange
    );

    return () => {
      subscription?.remove?.();
    };
  }, []);

  const renderApp = () => {
    if (showSplash || isLoading) {
      return <SplashScreen />;
    }

    if (!isAuthenticated) {
      return (
        <NavigationContainer theme={{ colors: { background: colors.background } }}>
          <ThemeProvider>
            <AuthNavigator />
          </ThemeProvider>
        </NavigationContainer>
      );
    }

    return (
      <NavigationContainer theme={{ colors: { background: colors.background } }}>
        <ThemeProvider>
          <WebSocketProvider>
            <NotificationProvider>
              <AppNavigator />
            </NotificationProvider>
          </WebSocketProvider>
        </ThemeProvider>
      </NavigationContainer>
    );
  };

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ErrorBoundary>
        <SafeAreaView style={styles.container}>
          <StatusBar
            barStyle="light-content"
            backgroundColor={colors.background}
            translucent={false}
          />
          {renderApp()}
        </SafeAreaView>
      </ErrorBoundary>
    </GestureHandlerRootView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
});

export default App;