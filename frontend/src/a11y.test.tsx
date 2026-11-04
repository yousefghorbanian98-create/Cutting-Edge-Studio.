import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { useAppStore } from './store/useAppStore';

/**
 * axe-core over the whole rendered app. Colour-contrast is disabled because jsdom
 * cannot compute stylesheet colours; contrast is verified on the real build (P8/CI).
 */
const AXE_OPTIONS: axe.RunOptions = {
  rules: { 'color-contrast': { enabled: false } },
};

function stubHealth() {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ status: 'ok', version: '1.0.0', app_name: 'x', offline: true, database: '', models_dir: '' }),
        { status: 200 },
      ),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  useAppStore.setState({ language: 'fa', theme: 'pro', backend: 'checking', backendVersion: null });
});

describe('accessibility (WCAG 2.1 A/AA structural rules)', () => {
  it('has no violations on the main shell', async () => {
    stubHealth();
    const { container } = render(<App />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations.map((violation) => `${violation.id}: ${violation.nodes.length}`)).toEqual([]);
  });

  it('has no violations in English/LTR', async () => {
    stubHealth();
    useAppStore.getState().setLanguage('en');
    const { container } = render(<App />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations.map((violation) => violation.id)).toEqual([]);
  });

  it('has no violations with the command palette open', async () => {
    stubHealth();
    const { container } = render(<App />);
    await userEvent.keyboard('{Control>}k{/Control}');
    expect(screen.getByPlaceholderText(/دستور/)).toBeInTheDocument();
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations.map((violation) => violation.id)).toEqual([]);
  });
});
