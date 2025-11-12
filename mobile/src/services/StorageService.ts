import AsyncStorage from '@react-native-async-storage/async-storage';
import { User } from '../types';

interface StorageKeys {
  ACCESS_TOKEN: string;
  USER: string;
  APP_SETTINGS: string;
  BIOMETRIC_ENABLED: string;
  NOTIFICATION_SETTINGS: string;
  USER_PREFERENCES: string;
  RISK_SETTINGS: string;
}

const STORAGE_KEYS: StorageKeys = {
  ACCESS_TOKEN: 'access_token',
  USER: 'user',
  APP_SETTINGS: 'app_settings',
  BIOMETRIC_ENABLED: 'biometric_enabled',
  NOTIFICATION_SETTINGS: 'notification_settings',
  USER_PREFERENCES: 'user_preferences',
  RISK_SETTINGS: 'risk_settings',
};

interface UserPreferences {
  defaultRiskProfile: string;
  autoRefreshInterval: number;
  chartType: string;
  enableSounds: boolean;
  enableVibration: boolean;
  enablePushNotifications: boolean;
}

interface AppSettings {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  enableBiometric: boolean;
  enablePushNotifications: boolean;
  autoRefreshInterval: number;
}

interface NotificationSettings {
  tradeAlerts: boolean;
  riskAlerts: boolean;
  opportunityAlerts: boolean;
  analysisAlerts: boolean;
  enableSounds: boolean;
  enableVibration: boolean;
  quietHours: {
    enabled: boolean;
    start: string;
    end: string;
  };
}

interface RiskSettings {
  riskTolerance: number;
  maxDailyTrades: number;
  autoTradingEnabled: boolean;
  maxPositionSizePercent: number;
  stopLossPercent: number;
  customAlertsEnabled: boolean;
  emergencyStopEnabled: boolean;
}

class StorageService {
  // Auth storage methods
  static async storeAuthToken(token: string): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token);
    } catch (error) {
      console.error('Error storing auth token:', error);
      throw error;
    }
  }

  static async getStoredToken(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    } catch (error) {
      console.error('Error getting stored token:', error);
      return null;
    }
  }

  static async removeAuthToken(): Promise<void> {
    try {
      await AsyncStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    } catch (error) {
      console.error('Error removing auth token:', error);
      throw error;
    }
  }

  static async storeUser(user: User): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
    } catch (error) {
      console.error('Error storing user:', error);
      throw error;
    }
  }

  static async getStoredUser(): Promise<User | null> {
    try {
      const userStr = await AsyncStorage.getItem(STORAGE_KEYS.USER);
      return userStr ? JSON.parse(userStr) : null;
    } catch (error) {
      console.error('Error getting stored user:', error);
      return null;
    }
  }

  static async removeUser(): Promise<void> {
    try {
      await AsyncStorage.removeItem(STORAGE_KEYS.USER);
    } catch (error) {
      console.error('Error removing user:', error);
      throw error;
    }
  }

  static async clearAuthData(): Promise<void> {
    try {
      await this.removeAuthToken();
      await this.removeUser();
    } catch (error) {
      console.error('Error clearing auth data:', error);
      throw error;
    }
  }

  // App settings methods
  static async storeAppSettings(settings: AppSettings): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.APP_SETTINGS, JSON.stringify(settings));
    } catch (error) {
      console.error('Error storing app settings:', error);
      throw error;
    }
  }

  static async getAppSettings(): Promise<AppSettings> {
    try {
      const settingsStr = await AsyncStorage.getItem(STORAGE_KEYS.APP_SETTINGS);
      const defaultSettings: AppSettings = {
        theme: 'auto',
        language: 'en',
        enableBiometric: false,
        enablePushNotifications: true,
        autoRefreshInterval: 30,
      };
      return settingsStr ? JSON.parse(settingsStr) : defaultSettings;
    } catch (error) {
      console.error('Error getting app settings:', error);
      return {
        theme: 'auto',
        language: 'en',
        enableBiometric: false,
        enablePushNotifications: true,
        autoRefreshInterval: 30,
      };
    }
  }

  // User preferences methods
  static async storeUserPreferences(preferences: UserPreferences): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.USER_PREFERENCES, JSON.stringify(preferences));
    } catch (error) {
      console.error('Error storing user preferences:', error);
      throw error;
    }
  }

  static async getUserPreferences(): Promise<UserPreferences> {
    try {
      const prefsStr = await AsyncStorage.getItem(STORAGE_KEYS.USER_PREFERENCES);
      const defaultPrefs: UserPreferences = {
        defaultRiskProfile: 'moderate',
        autoRefreshInterval: 30,
        chartType: 'line',
        enableSounds: true,
        enableVibration: true,
        enablePushNotifications: true,
      };
      return prefsStr ? JSON.parse(prefsStr) : defaultPrefs;
    } catch (error) {
      console.error('Error getting user preferences:', error);
      return {
        defaultRiskProfile: 'moderate',
        autoRefreshInterval: 30,
        chartType: 'line',
        enableSounds: true,
        enableVibration: true,
        enablePushNotifications: true,
      };
    }
  }

  // Risk settings methods
  static async storeRiskSettings(settings: RiskSettings): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.RISK_SETTINGS, JSON.stringify(settings));
    } catch (error) {
      console.error('Error storing risk settings:', error);
      throw error;
    }
  }

  static async getRiskSettings(): Promise<RiskSettings> {
    try {
      const settingsStr = await AsyncStorage.getItem(STORAGE_KEYS.RISK_SETTINGS);
      const defaultSettings: RiskSettings = {
        riskTolerance: 5,
        maxDailyTrades: 10,
        autoTradingEnabled: false,
        maxPositionSizePercent: 5,
        stopLossPercent: 10,
        customAlertsEnabled: true,
        emergencyStopEnabled: false,
      };
      return settingsStr ? JSON.parse(settingsStr) : defaultSettings;
    } catch (error) {
      console.error('Error getting risk settings:', error);
      return {
        riskTolerance: 5,
        maxDailyTrades: 10,
        autoTradingEnabled: false,
        maxPositionSizePercent: 5,
        stopLossPercent: 10,
        customAlertsEnabled: true,
        emergencyStopEnabled: false,
      };
    }
  }

  // Notification settings methods
  static async storeNotificationSettings(settings: NotificationSettings): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.NOTIFICATION_SETTINGS, JSON.stringify(settings));
    } catch (error) {
      console.error('Error storing notification settings:', error);
      throw error;
    }
  }

  static async getNotificationSettings(): Promise<NotificationSettings> {
    try {
      const settingsStr = await AsyncStorage.getItem(STORAGE_KEYS.NOTIFICATION_SETTINGS);
      const defaultSettings: NotificationSettings = {
        tradeAlerts: true,
        riskAlerts: true,
        opportunityAlerts: true,
        analysisAlerts: true,
        enableSounds: true,
        enableVibration: true,
        quietHours: {
          enabled: false,
          start: '22:00',
          end: '08:00',
        },
      };
      return settingsStr ? JSON.parse(settingsStr) : defaultSettings;
    } catch (error) {
      console.error('Error getting notification settings:', error);
      return {
        tradeAlerts: true,
        riskAlerts: true,
        opportunityAlerts: true,
        analysisAlerts: true,
        enableSounds: true,
        enableVibration: true,
        quietHours: {
          enabled: false,
          start: '22:00',
          end: '08:00',
        },
      };
    }
  }

  // Biometric settings
  static async storeBiometricEnabled(enabled: boolean): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.BIOMETRIC_ENABLED, JSON.stringify(enabled));
    } catch (error) {
      console.error('Error storing biometric setting:', error);
      throw error;
    }
  }

  static async getBiometricEnabled(): Promise<boolean> {
    try {
      const enabledStr = await AsyncStorage.getItem(STORAGE_KEYS.BIOMETRIC_ENABLED);
      return enabledStr !== null ? JSON.parse(enabledStr) : false;
    } catch (error) {
      console.error('Error getting biometric setting:', error);
      return false;
    }
  }

  // Utility methods
  static async clearAllData(): Promise<void> {
    try {
      const keys = Object.values(STORAGE_KEYS);
      await AsyncStorage.multiRemove(keys);
    } catch (error) {
      console.error('Error clearing all data:', error);
      throw error;
    }
  }

  static async getAllStorageKeys(): Promise<string[]> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      return keys;
    } catch (error) {
      console.error('Error getting storage keys:', error);
      return [];
    }
  }

  static async getStorageSize(): Promise<number> {
    try {
      const keys = await this.getAllStorageKeys();
      let totalSize = 0;

      for (const key of keys) {
        const item = await AsyncStorage.getItem(key);
        if (item) {
          totalSize += item.length;
        }
      }

      return totalSize;
    } catch (error) {
      console.error('Error calculating storage size:', error);
      return 0;
    }
  }

  // Cache management
  static async clearCache(): Promise<void> {
    try {
      // Clear non-essential cached data
      const nonEssentialKeys = [
        'market_cache',
        'analysis_cache',
        'chart_cache',
        'temp_data',
      ];

      const allKeys = await this.getAllStorageKeys();
      const keysToRemove = allKeys.filter(key =>
        nonEssentialKeys.some(essentialKey => key.includes(essentialKey))
      );

      if (keysToRemove.length > 0) {
        await AsyncStorage.multiRemove(keysToRemove);
        console.log(`Cleared ${keysToRemove.length} cache entries`);
      }
    } catch (error) {
      console.error('Error clearing cache:', error);
      throw error;
    }
  }

  // Export storage keys for external use
  static getKeys(): StorageKeys {
    return STORAGE_KEYS;
  }
}

export default StorageService;