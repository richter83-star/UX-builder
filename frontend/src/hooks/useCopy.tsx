import React, { createContext, useContext, useMemo, useState } from 'react';
import { BASE_COPY, MONEY_COPY } from '../constants/copy';

type CopyMode = 'money' | 'base';

type CopyShape = typeof MONEY_COPY;

interface CopyContextValue {
  mode: CopyMode;
  toggleMode: () => void;
  copy: CopyShape;
}

const CopyContext = createContext<CopyContextValue | undefined>(undefined);

export const CopyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<CopyMode>('money');

  const copy = useMemo(() => (mode === 'money' ? MONEY_COPY : BASE_COPY), [mode]);

  const toggleMode = () => setMode((prev) => (prev === 'money' ? 'base' : 'money'));

  return <CopyContext.Provider value={{ mode, toggleMode, copy }}>{children}</CopyContext.Provider>;
};

export const useCopy = () => {
  const context = useContext(CopyContext);
  if (!context) {
    throw new Error('useCopy must be used within a CopyProvider');
  }
  return context;
};
