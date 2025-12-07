import React, { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Enable React's built-in act() for tests to avoid relying on deprecated helpers
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// Provide a stable matchMedia implementation for Ant Design components
let consoleErrorSpy: jest.SpyInstance;
let consoleWarnSpy: jest.SpyInstance;

beforeAll(() => {
  window.matchMedia =
    window.matchMedia ||
    (() => ({
      matches: false,
      media: '',
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    } as MediaQueryList));

  const originalError = console.error;
  consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation((message?: unknown, ...args: unknown[]) => {
    if (typeof message === 'string' && message.includes('ReactDOMTestUtils.act')) {
      return;
    }

    originalError(message, ...args);
  });

  const originalWarn = console.warn;
  consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation((message?: unknown, ...args: unknown[]) => {
    if (typeof message === 'string' && message.includes('React Router Future Flag Warning')) {
      return;
    }

    originalWarn(message, ...args);
  });
});

afterAll(() => {
  consoleErrorSpy?.mockRestore();
  consoleWarnSpy?.mockRestore();
});

const mockInitializeAuth = jest.fn();

jest.mock('./hooks/useAuth', () => ({
  __esModule: true,
  default: () => ({
    isAuthenticated: false,
    initializeAuth: mockInitializeAuth,
  }),
  useAuthStore: () => ({
    isAuthenticated: false,
    initializeAuth: mockInitializeAuth,
  }),
}));

jest.mock('./components/Login', () => () => <div>Login Page</div>);
jest.mock('./components/Layout', () => ({ children }: { children: React.ReactNode }) => <div>Layout Wrapper{children}</div>);
jest.mock('./components/Dashboard', () => () => <div>Dashboard View</div>);
jest.mock('./components/Markets', () => () => <div>Markets View</div>);
jest.mock('./components/Watchlist', () => () => <div>Watchlist View</div>);
jest.mock('./components/AlertsSettings', () => () => <div>Alerts Settings View</div>);
jest.mock('./components/Analysis', () => () => <div>Analysis View</div>);
jest.mock('./components/Trading', () => () => <div>Trading View</div>);
jest.mock('./components/Portfolio', () => () => <div>Portfolio View</div>);
jest.mock('./components/RiskSettings', () => () => <div>Risk Settings View</div>);
jest.mock('./components/Register', () => () => <div>Register View</div>);
jest.mock('./components/NotFound', () => () => <div>Not Found</div>);
jest.mock('./App.css', () => ({}), { virtual: true });

// Import App after mocks are defined so that nested dependencies use the mocked versions
// eslint-disable-next-line @typescript-eslint/no-var-requires
const App = require('./App').default as typeof import('./App').default;

describe('App routing', () => {
  it('routes unauthenticated users to the login page after mount', async () => {
    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(mockInitializeAuth).toHaveBeenCalled();
    });

    expect(await screen.findByText(/login page/i)).toBeInTheDocument();
  });
});
