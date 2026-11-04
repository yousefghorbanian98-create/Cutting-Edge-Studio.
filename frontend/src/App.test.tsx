import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { useMediaStore } from './features/media/mediaStore';
import { useWizardStore } from './features/stylematch/wizardStore';
import { useAppStore } from './store/useAppStore';

const HEALTH = {
  status: 'ok',
  version: '1.0.0',
  app_name: 'CuttingEdgeV2',
  offline: true,
  database: '/tmp/x/cutting-edge.db',
  models_dir: '/tmp/x/models',
};

function stubHealth(payload: unknown = HEALTH) {
  return vi.fn().mockImplementation((url: string) => {
    const body = url.endsWith('/uploads') ? {
      id: 'asset-1', project_id: 'project-1', path: '/local/imports/posing.mp4',
      role: 'source', kind: 'video', duration: 12.5, width: 1080, height: 1920, fps: 30,
    } : url === '/api/v1/projects' ? { id: 'project-1', name: 'Test' } : payload;
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  useAppStore.setState({ language: 'fa', theme: 'pro', backend: 'checking', backendVersion: null });
  useMediaStore.getState().clear();
  useWizardStore.getState().reset();
});

describe('application shell', () => {
  it('renders the 4 workspace panels plus menu and status bars in Persian', async () => {
    vi.stubGlobal('fetch', stubHealth());
    render(<App />);
    expect(screen.getByRole('navigation', { name: 'main menu' })).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'رسانه' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'پیش‌نمایش' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'تایم‌لاین' })).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'خصوصیات' })).toBeInTheDocument();
  });

  it('shows the connected state and version when the backend answers', async () => {
    vi.stubGlobal('fetch', stubHealth());
    render(<App />);
    await waitFor(() =>
      expect(screen.getByRole('status', { name: 'backend status' })).toHaveTextContent(
        'هستهٔ پردازش متصل است',
      ),
    );
    expect(screen.getByText(/1\.0\.0/)).toBeInTheDocument();
  });

  it('degrades to an offline badge instead of crashing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')));
    render(<App />);
    await waitFor(() =>
      expect(screen.getByRole('status', { name: 'backend status' })).toHaveTextContent(
        'هستهٔ پردازش در دسترس نیست',
      ),
    );
  });

  it('switches language and direction from the menu bar', async () => {
    vi.stubGlobal('fetch', stubHealth());
    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: 'زبان' }));
    expect(document.documentElement.dir).toBe('ltr');
    expect(screen.getByRole('region', { name: 'Preview' })).toBeInTheDocument();
  });

  it('switches theme through the command palette (Ctrl+K)', async () => {
    vi.stubGlobal('fetch', stubHealth());
    render(<App />);
    await userEvent.keyboard('{Control>}k{/Control}');
    await userEvent.click(screen.getByText('تغییر تم'));
    expect(document.documentElement.dataset.theme).toBe('glass');
  });

  it('imports a clip through the file input and shows it in the media panel', async () => {
    vi.stubGlobal('fetch', stubHealth());
    render(<App />);
    const input = screen.getByLabelText('ورود کلیپ') as HTMLInputElement;
    const file = new File(['x'], 'posing.mp4', { type: 'video/mp4' });
    await userEvent.upload(input, file);
    expect(await screen.findByText('posing.mp4')).toBeInTheDocument();
  });

  it('keeps the Style Match wizard blocked until a reference exists', async () => {
    vi.stubGlobal('fetch', stubHealth());
    render(<App />);
    expect(screen.getByTestId('wizard-next')).toBeDisabled();
    expect(screen.getByText('یک ویدیوی مرجع انتخاب کنید')).toBeInTheDocument();
  });
});
