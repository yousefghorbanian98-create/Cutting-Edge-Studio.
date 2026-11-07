import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, type AssetResponse } from '../../lib/api';
import { useMediaStore } from './mediaStore';

const asset: AssetResponse = {
  id: 'asset-real', project_id: 'project-real', path: '/data/imports/a.mp4', role: 'source',
  kind: 'video', duration: 8.2, fps: 30, width: 1080, height: 1920,
  video_codec: 'h264', audio_codec: 'aac', has_audio: true,
};
const file = () => new File(['media'], 'a.mp4', { type: 'video/mp4' });
beforeEach(() => useMediaStore.getState().clear());

describe('real media import wiring', () => {
  it('stores probed backend asset IDs and rejects duplicate uploads', async () => {
    const create = vi.spyOn(api, 'createProject').mockResolvedValue({ id: 'project-real', name: 'Test' });
    const upload = vi.spyOn(api, 'uploadAsset').mockResolvedValue(asset);
    const result = await useMediaStore.getState().importFiles([file()]);
    expect(result.rejected).toEqual([]);
    expect(result.added[0]).toMatchObject({ id: asset.id, assetId: asset.id, path: asset.path, duration: 8.2 });
    expect(useMediaStore.getState().selectedId).toBe(asset.id);
    expect(create).toHaveBeenCalledOnce();
    expect(upload).toHaveBeenCalledWith('project-real', expect.any(File), 'source');
    const duplicate = await useMediaStore.getState().importFiles([file()]);
    expect(duplicate.rejected[0]?.reason).toBe('duplicate');
    expect(upload).toHaveBeenCalledOnce();
  });
  it('imports reference explicitly instead of repurposing a source', async () => {
    vi.spyOn(api, 'createProject').mockResolvedValue({ id: 'project-real', name: 'Test' });
    const upload = vi.spyOn(api, 'uploadAsset').mockResolvedValue({ ...asset, role: 'reference' });
    await useMediaStore.getState().importFiles([file()], 'reference');
    expect(upload).toHaveBeenCalledWith('project-real', expect.any(File), 'reference');
    expect(useMediaStore.getState().clips[0]?.role).toBe('reference');
  });
  it('reports probe failure without phantom media and resets busy state', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    vi.spyOn(api, 'createProject').mockResolvedValue({ id: 'project-real', name: 'Test' });
    vi.spyOn(api, 'uploadAsset').mockRejectedValue(new Error('ffprobe unavailable'));
    const result = await useMediaStore.getState().importFiles([file()]);
    expect(result.rejected[0]?.reason).toContain('ffprobe unavailable');
    expect(useMediaStore.getState().clips).toEqual([]);
    expect(useMediaStore.getState().importing).toBe(false);
  });
  it('rejects invalid files before any network request', async () => {
    const create = vi.spyOn(api, 'createProject');
    const result = await useMediaStore.getState().importFiles([new File(['x'], 'bad.exe')]);
    expect(result.rejected[0]?.reason).toBe('extension');
    expect(create).not.toHaveBeenCalled();
  });
  it('rejects concurrent imports rather than creating two projects', async () => {
    let resolve!: (value: { id: string; name: string }) => void;
    vi.spyOn(api, 'createProject').mockReturnValue(new Promise(done => { resolve = done; }));
    vi.spyOn(api, 'uploadAsset').mockResolvedValue(asset);
    const first = useMediaStore.getState().importFiles([file()]);
    await expect(useMediaStore.getState().importFiles([file()])).rejects.toThrow('already in progress');
    resolve({ id: 'project-real', name: 'Test' });
    await first;
    expect(useMediaStore.getState().importing).toBe(false);
  });
  it('preserves a clip on failed deletion, clears selection on success', async () => {
    vi.spyOn(api, 'createProject').mockResolvedValue({ id: 'project-real', name: 'Test' });
    vi.spyOn(api, 'uploadAsset').mockResolvedValue(asset);
    await useMediaStore.getState().importFiles([file()]);
    const del = vi.spyOn(api, 'deleteAsset').mockRejectedValue(new Error('offline'));
    await expect(useMediaStore.getState().deleteImported(asset.id)).rejects.toThrow('offline');
    expect(useMediaStore.getState().clips).toHaveLength(1);
    del.mockResolvedValue(undefined);
    await useMediaStore.getState().deleteImported(asset.id);
    expect(useMediaStore.getState().clips).toEqual([]);
    expect(useMediaStore.getState().selectedId).toBeNull();
  });
});
