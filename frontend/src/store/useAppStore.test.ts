import { readFileSync } from 'node:fs';
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

describe('theme stylesheet contract', () => {
  const css = readFileSync('src/index.css', 'utf-8');

  function variablesOf(selector: string): Set<string> {
    const start = css.indexOf(selector);
    expect(start, `theme block not found: ${selector}`).toBeGreaterThan(-1);
    const body = css.slice(start + selector.length, css.indexOf('}', start));
    return new Set([...body.matchAll(/(--[\w-]+)\s*:/g)].map((m) => m[1]!));
  }

  const pro = variablesOf(":root,\n:root[data-theme='pro'] {");
  const glass = variablesOf(":root[data-theme='glass'] {");
  const minimal = variablesOf(":root[data-theme='minimal'] {");

  it('declares all three themes', () => {
    expect(pro.size).toBeGreaterThan(10);
  });

  // A variable defined by only some themes silently resolves to nothing after a
  // switch, which is how `.glass-panel` ended up transparent outside the glass theme.
  it.each([
    ['glass', () => glass],
    ['minimal', () => minimal],
  ])('%s defines exactly the same variables as pro', (_name, get) => {
    const theme = get();
    expect([...pro].filter((v) => !theme.has(v))).toEqual([]);
    expect([...theme].filter((v) => !pro.has(v))).toEqual([]);
  });

  it('never references a custom property that no theme defines', () => {
    const used = new Set([...css.matchAll(/var\((--[\w-]+)/g)].map((m) => m[1]!));
    const defined = new Set([...pro, ...glass, ...minimal]);
    expect([...used].filter((v) => !defined.has(v))).toEqual([]);
  });
});
