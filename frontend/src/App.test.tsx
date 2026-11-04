import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { useAppStore } from './store/useAppStore';

function stubHealth(payload: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status }));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  useAppStore.setState({ language: 'fa', theme: 'pro', backend: 'checking', backendVersion: null });
});

describe('application shell', () => {
  it('renders the 4 workspace panels plus menu and status bars in Persian', async () => {
    stubHealth({ status: 'ok', version: '1.0.0', app_name: 'x', offline: true, database: '', models_dir: '' });
    render(<App />);
    expect(screen.getByRole('navigation', { name: 'main menu' })).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'رسانه' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'پیش‌نمایش' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'تایم‌لاین' })).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'خصوصیات' })).toBeInTheDocument();
  });

  it('shows the connected state and version when the backend answers', async () => {
    stubHealth({ status: 'ok', version: '1.0.0', app_name: 'x', offline: true, database: '', models_dir: '' });
    render(<App />);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('هستهٔ پردازش متصل است'));
    expect(screen.getByText(/1\.0\.0/)).toBeInTheDocument();
  });

  it('degrades to an offline badge instead of crashing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')));
    render(<App />);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('هستهٔ پردازش در دسترس نیست'));
  });

  it('switches language and direction from the menu bar', async () => {
    stubHealth({ status: 'ok', version: '1.0.0', app_name: 'x', offline: true, database: '', models_dir: '' });
    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: 'EN' }));
    expect(document.documentElement.dir).toBe('ltr');
    expect(screen.getByRole('region', { name: 'Preview' })).toBeInTheDocument();
  });

  it('changes the theme from the menu bar', async () => {
    stubHealth({ status: 'ok', version: '1.0.0', app_name: 'x', offline: true, database: '', models_dir: '' });
    render(<App />);
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'theme' }), 'minimal');
    expect(document.documentElement.dataset.theme).toBe('minimal');
  });
});
