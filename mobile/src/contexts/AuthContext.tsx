import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { Alert, Platform } from 'react-native';
import {
  User,
  AuthState,
  LoginCredentials,
  RegisterData,
} from '../types';
import apiService from '../services/ApiService';
import { StorageService } from '../services/StorageService';

interface AuthContextType {
  authState: AuthState;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (userData: Partial<User>) => Promise<void>;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
  isAuthenticated: () => boolean;
  getUser: () => User | null;
}

type AuthAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_TOKEN'; payload: string | null }
  | { type: 'SET_AUTHENTICATED'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'LOGOUT' };

const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

const authReducer = (state: AuthState, action: AuthAction): AuthState => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_USER':
      return { ...state, user: action.payload };
    case 'SET_TOKEN':
      return { ...state, token: action.payload };
    case 'SET_AUTHENTICATED':
      return { ...state, isAuthenticated: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'LOGOUT':
      return {
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      };
    default:
      return state;
  }
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, dispatch] = useReducer(authReducer, initialState);

  const setLoading = (loading: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: loading });
  };

  const setAuthState = (user: User | null, token: string | null, isAuthenticated: boolean) => {
    dispatch({ type: 'SET_USER', payload: user });
    dispatch({ type: 'SET_TOKEN', payload: token });
    dispatch({ type: 'SET_AUTHENTICATED', payload: isAuthenticated });
  };

  const setError = (error: string | null) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  };

  const clearError = () => {
    dispatch({ type: 'SET_ERROR', payload: null });
  };

  const login = async (credentials: LoginCredentials): Promise<void> => {
    try {
      setLoading(true);
      clearError();

      const response = await apiService.login(credentials);

      setAuthState(response.user, response.access_token, true);

      // Store user preferences
      await StorageService.storeUser(response.user);
      await StorageService.storeAuthToken(response.access_token);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed';
      setError(errorMessage);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData: RegisterData): Promise<void> => {
    try {
      setLoading(true);
      clearError();

      const response = await apiService.register(userData);

      setAuthState(response.user, response.access_token, true);

      // Store user preferences
      await StorageService.storeUser(response.user);
      await StorageService.storeAuthToken(response.access_token);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Registration failed';
      setError(errorMessage);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    try {
      setLoading(true);

      await apiService.logout();

      // Clear stored data
      await StorageService.clearAuthData();

      setAuthState(null, null, false);

    } catch (error) {
      console.error('Logout error:', error);
      // Still clear local data even if API call fails
      await StorageService.clearAuthData();
      setAuthState(null, null, false);
    } finally {
      setLoading(false);
    }
  };

  const updateUser = async (userData: Partial<User>): Promise<void> => {
    try {
      setLoading(true);
      clearError();

      await apiService.updateProfile(userData);

      // Update user in state and storage
      if (authState.user) {
        const updatedUser = { ...authState.user, ...userData };
        setAuthState(updatedUser, authState.token, authState.isAuthenticated);
        await StorageService.storeUser(updatedUser);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Profile update failed';
      setError(errorMessage);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const isAuthenticated = (): boolean => {
    return authState.isAuthenticated;
  };

  const getUser = (): User | null => {
    return authState.user;
  };

  // Initialize auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setLoading(true);

        // Check for stored auth data
        const storedUser = await StorageService.getStoredUser();
        const storedToken = await StorageService.getStoredToken();

        if (storedUser && storedToken) {
          setAuthState(storedUser, storedToken, true);

          // Verify token is still valid
          try {
            await apiService.getCurrentUser();
          } catch (error) {
            console.warn('Token validation failed:', error);
            await logout(); // Token is invalid
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const value: AuthContextType = {
    authState,
    login,
    register,
    logout,
    updateUser,
    clearError,
    setLoading,
    isAuthenticated,
    getUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;