/** Typed client for the local FastAPI sidecar. Relative URLs only: no host. */

export interface HealthResponse {
  status: 'ok';
  version: string;
  app_name: string;
  offline: boolean;
  database: string;
  models_dir: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const BASE = '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      headers: { 'content-type': 'application/json' },
      ...init,
    });
  } catch (cause) {
    throw new ApiError(`backend unreachable: ${String(cause)}`, 0);
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(detail || `request failed with ${response.status}`, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>('/health'),
};
