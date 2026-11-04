import type { InspectionResponse, InspectionCapabilities, InspectionOperation } from '../features/stylematch/inspectionSchema';
import type { WorkspaceResponse, WorkspaceSnapshot } from '../features/workspace/schema';

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
      headers: init?.body instanceof FormData ? undefined : { 'content-type': 'application/json' },
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

export interface ProjectResponse {
  id: string;
  name: string;
}
export interface AssetResponse {
  id: string;
  project_id: string;
  name?: string;
  size_bytes?: number;
  available?: boolean;
  path: string;
  role: string;
  kind: 'video' | 'audio';
  duration: number;
  fps: number;
  width: number;
  height: number;
  video_codec: string | null;
  audio_codec: string | null;
  has_audio: boolean;
}

export function assetContentUrl(id: string): string {
  return `${BASE}/assets/${encodeURIComponent(id)}/content`;
}

const measurementPath = (operation:InspectionOperation) => ({decode:'inspection',rhythm:'rhythm',scenes:'scenes'}[operation]);
export const api = {
  inspectionCapabilities: (id:string, signal?:AbortSignal, operation:InspectionOperation="decode") => request<InspectionCapabilities>(`/projects/${encodeURIComponent(id)}/${measurementPath(operation)}/capabilities`,{signal}),
  latestInspection: (id:string, signal?:AbortSignal, operation:InspectionOperation="decode") => request<InspectionResponse>(`/projects/${encodeURIComponent(id)}/${measurementPath(operation)}/latest`,{signal}),
  getInspection: (id:string, job:string, signal?:AbortSignal, operation:InspectionOperation="decode") => request<InspectionResponse>(`/projects/${encodeURIComponent(id)}/${measurementPath(operation)}/jobs/${encodeURIComponent(job)}`,{signal}),
  startInspection: (id:string, reference_asset_id:string, source_asset_ids:string[], operation:InspectionOperation="decode") => request<InspectionResponse>(`/projects/${encodeURIComponent(id)}/${measurementPath(operation)}/jobs`,{method:'POST',body:JSON.stringify({reference_asset_id,source_asset_ids})}),
  cancelInspection: (id:string,job:string, operation:InspectionOperation="decode") => request<InspectionResponse>(`/projects/${encodeURIComponent(id)}/${measurementPath(operation)}/jobs/${encodeURIComponent(job)}/cancel`,{method:'POST'}),
  health: () => request<HealthResponse>('/health'),
  listProjects: () => request<ProjectResponse[]>('/projects'),
  listAssets: (id: string) => request<AssetResponse[]>(`/projects/${encodeURIComponent(id)}/assets`),
  getWorkspace: (id: string) => request<WorkspaceResponse>(`/projects/${encodeURIComponent(id)}/workspace`),
  saveWorkspace: (id: string, base_revision: string, name: string, snapshot: WorkspaceSnapshot) =>
    request<WorkspaceResponse>(`/projects/${encodeURIComponent(id)}/workspace`, {
      method: 'PUT',
      body: JSON.stringify({ base_revision, name, snapshot }),
    }),
  createProject: () =>
    request<ProjectResponse>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name: 'Local editing session', mode: 'style-match' }),
    }),
  uploadAsset: (projectId: string, file: File, role: 'source' | 'reference') => {
    const body = new FormData();
    body.append('file', file);
    body.append('role', role);
    return request<AssetResponse>(`/projects/${encodeURIComponent(projectId)}/uploads`, {
      method: 'POST',
      body,
    });
  },
  deleteAsset: (id: string) => request<void>(`/assets/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
