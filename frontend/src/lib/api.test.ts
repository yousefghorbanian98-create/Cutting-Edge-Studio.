import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from './api';

const HEALTH = {
  status: 'ok',
  version: '1.0.0',
  app_name: 'CuttingEdgeV2',
  offline: true,
  database: '/tmp/x/cutting-edge.db',
  models_dir: '/tmp/x/models',
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('api client', () => {
  it('calls the relative /api/v1 path (never a hardcoded host)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(HEALTH), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    await api.health();
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/v1/health');
  });

  it('parses the health payload', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(HEALTH), { status: 200 })));
    const health = await api.health();
    expect(health.version).toBe('1.0.0');
    expect(health.offline).toBe(true);
  });

  it('wraps http errors in ApiError with the status code', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() => Promise.resolve(new Response('boom', { status: 500 }))),
    );
    await expect(api.health()).rejects.toBeInstanceOf(ApiError);
    await expect(api.health()).rejects.toMatchObject({ status: 500, message: 'boom' });
  });

  it('reports status 0 when the backend is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')));
    await expect(api.health()).rejects.toMatchObject({ status: 0 });
  });
});
