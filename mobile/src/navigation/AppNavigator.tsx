import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';

// Auth Screens
import LoginScreen from '../screens/auth/LoginScreen';
import RegisterScreen from '../screens/auth/RegisterScreen';
import ForgotPasswordScreen from '../screens/auth/ForgotPasswordScreen';

// Main Screens
import DashboardScreen from '../screens/main/DashboardScreen';
import MarketsScreen from '../screens/main/MarketsScreen';
import AnalysisScreen from '../screens/main/AnalysisScreen';
import TradingScreen from '../screens/main/TradingScreen';
import PortfolioScreen from '../screens/main/PortfolioScreen';
import SettingsScreen from '../screens/main/SettingsScreen';

// Detail Screens
import MarketDetailScreen from '../screens/detail/MarketDetailScreen';
import MarketAnalysisScreen from '../screens/detail/MarketAnalysisScreen';
import PositionDetailScreen from '../screens/detail/PositionDetailScreen';
import OrderConfirmationScreen from '../screens/detail/OrderConfirmationScreen';

// Settings Sub-screens
import ProfileSettingsScreen from '../screens/settings/ProfileSettingsScreen';
import RiskSettingsScreen from '../screens/settings/RiskSettingsScreen';
import NotificationSettingsScreen from '../screens/settings/NotificationSettingsScreen';
import AboutScreen from '../screens/settings/AboutScreen';

import { RootStackParamList, AuthStackParamList, MainTabParamList, SettingsStackParamList } from '../types';

const Stack = createNativeStackNavigator<RootStackParamList>();
const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();
const SettingsStack = createNativeStackNavigator<SettingsStackParamList>();

const AuthNavigator = () => {
  const { colors } = useTheme();

  return (
    <AuthStack.Navigator
      initialRouteName="Login"
      screenOptions={{
        headerStyle: {
          backgroundColor: colors.background,
        },
        headerTintColor: colors.text,
        headerShadowVisible: false,
      }}
    >
      <AuthStack.Screen
        name="Login"
        component={LoginScreen}
        options={{ headerShown: false }}
      />
      <AuthStack.Screen
        name="Register"
        component={RegisterScreen}
        options={{ title: 'Create Account' }}
      />
      <AuthStack.Screen
        name="ForgotPassword"
        component={ForgotPasswordScreen}
        options={{ title: 'Reset Password' }}
      />
    </AuthStack.Navigator>
  );
};

const SettingsNavigator = () => {
  const { colors } = useTheme();

  return (
    <SettingsStack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: colors.background,
        },
        headerTintColor: colors.text,
        headerShadowVisible: false,
      }}
    >
      <SettingsStack.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ headerShown: false }}
      />
      <SettingsStack.Screen
        name="ProfileSettings"
        component={ProfileSettingsScreen}
        options={{ title: 'Profile' }}
      />
      <SettingsStack.Screen
        name="RiskSettings"
        component={RiskSettingsScreen}
        options={{ title: 'Risk Management' }}
      />
      <SettingsStack.Screen
        name="NotificationSettings"
        component={NotificationSettingsScreen}
        options={{ title: 'Notifications' }}
      />
      <SettingsStack.Screen
        name="About"
        component={AboutScreen}
        options={{ title: 'About' }}
      />
    </SettingsStack.Navigator>
  );
};

const MainTabNavigator = () => {
  const { colors } = useTheme();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: string;

          switch (route.name) {
            case 'Dashboard':
              iconName = 'dashboard';
              break;
            case 'Markets':
              iconName = 'store';
              break;
            case 'Analysis':
              iconName = 'analytics';
              break;
            case 'Trading':
              iconName = 'trending-up';
              break;
            case 'Portfolio':
              iconName = 'account-balance-wallet';
              break;
            case 'SettingsTab':
              iconName = 'settings';
              break;
            default:
              iconName = 'help';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarStyle: {
          backgroundColor: colors.background,
          borderTopColor: colors.border,
        },
        headerStyle: {
          backgroundColor: colors.background,
        },
        headerTintColor: colors.text,
        headerShadowVisible: false,
      })}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{ title: 'Dashboard' }}
      />
      <Tab.Screen
        name="Markets"
        component={MarketsScreen}
        options={{ title: 'Markets' }}
      />
      <Tab.Screen
        name="Analysis"
        component={AnalysisScreen}
        options={{ title: 'Analysis' }}
      />
      <Tab.Screen
        name="Trading"
        component={TradingScreen}
        options={{ title: 'Trading' }}
      />
      <Tab.Screen
        name="Portfolio"
        component={PortfolioScreen}
        options={{ title: 'Portfolio' }}
      />
      <Tab.Screen
        name="SettingsTab"
        component={SettingsNavigator}
        options={{ title: 'Settings', headerShown: false }}
      />
    </Tab.Navigator>
  );
};

const AppNavigator = () => {
  const { authState } = useAuth();

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {authState.isAuthenticated ? (
          <>
            <Stack.Screen name="Main" component={MainTabNavigator} />
            <Stack.Screen
              name="MarketDetail"
              component={MarketDetailScreen}
              options={{ headerShown: true, title: 'Market Details' }}
            />
            <Stack.Screen
              name="MarketAnalysis"
              component={MarketAnalysisScreen}
              options={{ headerShown: true, title: 'Market Analysis' }}
            />
            <Stack.Screen
              name="PositionDetail"
              component={PositionDetailScreen}
              options={{ headerShown: true, title: 'Position Details' }}
            />
            <Stack.Screen
              name="OrderConfirmation"
              component={OrderConfirmationScreen}
              options={{ headerShown: true, title: 'Confirm Order' }}
            />
          </>
        ) : (
          <Stack.Screen name="Auth" component={AuthNavigator} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;