import { beforeEach, describe, expect, it } from 'vitest';
import { useAppStore } from './useAppStore';

beforeEach(() => {
  useAppStore.setState({ language: 'fa', theme: 'pro', backend: 'checking', backendVersion: null });
});

describe('app store', () => {
  it('defaults to Persian RTL and the PRO theme (LOCK-13 / bilingual)', () => {
    expect(useAppStore.getState().language).toBe('fa');
    expect(useAppStore.getState().theme).toBe('pro');
  });

  it('applies language to <html> lang and dir', () => {
    useAppStore.getState().setLanguage('en');
    expect(document.documentElement.lang).toBe('en');
    expect(document.documentElement.dir).toBe('ltr');
    useAppStore.getState().setLanguage('fa');
    expect(document.documentElement.dir).toBe('rtl');
  });

  it('applies the theme through a data attribute', () => {
    useAppStore.getState().setTheme('glass');
    expect(document.documentElement.dataset.theme).toBe('glass');
  });

  it('records backend health', () => {
    useAppStore.getState().setBackend('online', '1.0.0');
    expect(useAppStore.getState().backend).toBe('online');
    expect(useAppStore.getState().backendVersion).toBe('1.0.0');
    useAppStore.getState().setBackend('offline');
    expect(useAppStore.getState().backend).toBe('offline');
    expect(useAppStore.getState().backendVersion).toBeNull();
  });
});
