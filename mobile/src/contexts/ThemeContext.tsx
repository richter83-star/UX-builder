import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { StorageService } from '../services/StorageService';

export interface ThemeColors {
  primary: string;
  secondary: string;
  background: string;
  surface: string;
  text: string;
  textSecondary: string;
  border: string;
  success: string;
  warning: string;
  error: string;
  info: string;
}

export interface Theme {
  colors: ThemeColors;
  spacing: {
    xs: number;
    sm: number;
    md: number;
    lg: number;
    xl: number;
    xxl: number;
  };
  borderRadius: {
    sm: number;
    md: number;
    lg: number;
    xl: number;
  };
  typography: {
    h1: {
      fontSize: number;
      fontWeight: string;
    };
    h2: {
      fontSize: number;
      fontWeight: string;
    };
    h3: {
      fontSize: number;
      fontWeight: string;
    };
    h4: {
      fontSize: number;
      fontWeight: string;
    };
    body: {
      fontSize: number;
      fontWeight: string;
    };
    caption: {
      fontSize: number;
      fontWeight: string;
    };
  };
}

const lightTheme: Theme = {
  colors: {
    primary: '#4F46E5',
    secondary: '#7C3AED',
    background: '#FFFFFF',
    surface: '#F9FAFB',
    text: '#111827',
    textSecondary: '#6B7280',
    border: '#E5E7EB',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  borderRadius: {
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
  },
  typography: {
    h1: { fontSize: 32, fontWeight: '700' },
    h2: { fontSize: 24, fontWeight: '600' },
    h3: { fontSize: 20, fontWeight: '600' },
    h4: { fontSize: 16, fontWeight: '600' },
    body: { fontSize: 14, fontWeight: '400' },
    caption: { fontSize: 12, fontWeight: '400' },
  },
};

const darkTheme: Theme = {
  colors: {
    primary: '#6366F1',
    secondary: '#8B5CF6',
    background: '#000000',
    surface: '#1F2937',
    text: '#F9FAFB',
    textSecondary: '#9CA3AF',
    border: '#374151',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  borderRadius: {
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
  },
  typography: {
    h1: { fontSize: 32, fontWeight: '700' },
    h2: { fontSize: 24, fontWeight: '600' },
    h3: { fontSize: 20, fontWeight: '600' },
    h4: { fontSize: 16, fontWeight: '600' },
    body: { fontSize: 14, fontWeight: '400' },
    caption: { fontSize: 12, fontWeight: '400' },
  },
};

interface ThemeContextType {
  theme: Theme;
  colors: ThemeColors;
  themeMode: 'light' | 'dark' | 'auto';
  setThemeMode: (mode: 'light' | 'dark' | 'auto') => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const systemColorScheme = useColorScheme();
  const [themeMode, setThemeModeState] = useState<'light' | 'dark' | 'auto'>('auto');

  const setThemeMode = async (mode: 'light' | 'dark' | 'auto') => {
    setThemeModeState(mode);
    try {
      const appSettings = await StorageService.getAppSettings();
      await StorageService.storeAppSettings({
        ...appSettings,
        theme: mode,
      });
    } catch (error) {
      console.error('Error saving theme mode:', error);
    }
  };

  useEffect(() => {
    const loadThemeMode = async () => {
      try {
        const appSettings = await StorageService.getAppSettings();
        setThemeModeState(appSettings.theme);
      } catch (error) {
        console.error('Error loading theme mode:', error);
      }
    };

    loadThemeMode();
  }, []);

  const isDark = themeMode === 'auto'
    ? systemColorScheme === 'dark'
    : themeMode === 'dark';

  const theme = isDark ? darkTheme : lightTheme;

  const value: ThemeContextType = {
    theme,
    colors: theme.colors,
    themeMode,
    setThemeMode,
    isDark,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeContext;