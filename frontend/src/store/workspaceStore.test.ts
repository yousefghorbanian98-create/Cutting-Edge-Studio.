import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, type AssetResponse } from '../lib/api';
import { useAppStore } from './useAppStore';
import { useMediaStore } from './mediaStore';
import { usePostStore } from './postStore';
import { useWizardStore } from './wizardStore';
import { useTimelineStore } from './timelineStore';
import { snapshotSchema } from '../features/workspace/schema';
import { captureSnapshot, LAST_PROJECT_STORAGE, useWorkspaceStore, watchWorkspaceChanges } from '../store/workspaceStore';

const revision = 'a'.repeat(64);
const nextRevision = 'b'.repeat(64);
const asset: AssetResponse = {
  id: 'asset-1',
  project_id: 'project-1',
  path: '/managed/uuid.mp4',
  name: 'گل زیبا.mp4',
  size_bytes: 64,
  available: true,
  role: 'source',
  kind: 'video',
  duration: 8,
  fps: 30,
  width: 1920,
  height: 1080,
  video_codec: 'h264',
  audio_codec: null,
  has_audio: false,
};
const reference: AssetResponse = {
  ...asset,
  id: 'reference-1',
  path: '/references/ref.mp4',
  name: 'مرجع.mp4',
  role: 'reference',
};
let unwatch = () => {};
function populated() {
  useMediaStore.setState({
    projectId: 'project-1',
    projectName: 'مسابقه',
    clips: [
      {
        id: asset.id,
        assetId: asset.id,
        path: asset.path,
        name: asset.name!,
        size: 64,
        role: 'source',
        kind: 'video',
        duration: 8,
      },
      {
        id: reference.id,
        assetId: reference.id,
        path: reference.path,
        name: reference.name!,
        size: 64,
        role: 'reference',
        kind: 'video',
        duration: 8,
      },
    ],
    selectedId: asset.id,
  });
  useTimelineStore.getState().addClip({ mediaId: asset.path, name: asset.name!, duration: 4, kind: 'video', at: 2 });
  useTimelineStore.getState().setPlayhead(3);
  useTimelineStore.getState().addBookmark('گل');
  useTimelineStore.getState().setPlayhead(3);
  useTimelineStore.getState().setZoom(80);
  useWizardStore.getState().selectReference(reference.path);
  usePostStore.getState().setPreset('youtube');
  return structuredClone(captureSnapshot());
}
beforeEach(() => {
  localStorage.clear();
  useMediaStore.getState().clear();
  useTimelineStore.getState().reset();
  useWizardStore.getState().reset();
  usePostStore.getState().reset();
  useAppStore.getState().setLanguage('en');
  useAppStore.getState().setTheme('pro');
  useWorkspaceStore.setState({
    initialized: true,
    navigating: false,
    status: 'idle',
    dirty: false,
    generation: 0,
    revision: null,
    revisionProject: null,
    error: null,
    warning: null,
    conflict: false,
    projects: [],
  });
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
});
afterEach(() => {
  unwatch();
});

describe('versioned project sessions', () => {
  it('captures only durable data, never functions/history/playing or fabricated analysis completion', () => {
    const snapshot = populated();
    expect(snapshotSchema.parse(snapshot)).toEqual(snapshot);
    expect(JSON.stringify(snapshot)).not.toContain('completed');
    expect(snapshot.timeline).not.toHaveProperty('past');
    expect(snapshot.timeline).not.toHaveProperty('playing');
    expect(snapshot.referenceAssetId).toBe(reference.id);
  });
  it('restores original names, trim geometry, bookmarks, tracks, media selections and settings atomically', async () => {
    const snapshot = populated();
    snapshot.mediaOrder = [reference.id, asset.id];
    snapshot.timeline.tracks[0]!.muted = true;
    snapshot.timeline.tracks[0]!.locked = true;
    snapshot.timeline.clips[0]!.inPoint = 1;
    snapshot.appearance = { language: 'fa', theme: 'glass' };
    vi.spyOn(api, 'getWorkspace').mockResolvedValue({ name: 'بازگشایی', revision, snapshot });
    vi.spyOn(api, 'listAssets').mockResolvedValue([asset, reference]);
    useMediaStore.getState().clear();
    useTimelineStore.getState().reset();
    useWizardStore.setState({ completed: true });
    await useWorkspaceStore.getState().open('project-1');
    expect(useMediaStore.getState().clips.map((c) => c.name)).toEqual(['مرجع.mp4', 'گل زیبا.mp4']);
    expect(useMediaStore.getState().selectedId).toBe(asset.id);
    expect(useTimelineStore.getState()).toMatchObject({
      ...snapshot.timeline,
      playing: false,
      past: [],
      future: [],
      selectedIds: [],
    });
    expect(useWizardStore.getState()).toMatchObject({ selectedReference: reference.path, completed: false });
    expect(usePostStore.getState().presetId).toBe('youtube');
    expect(useAppStore.getState()).toMatchObject({ language: 'fa', theme: 'glass' });
    expect(useWorkspaceStore.getState()).toMatchObject({ dirty: false, revision, status: 'idle' });
    expect(localStorage.getItem(LAST_PROJECT_STORAGE)).toBe('project-1');
  });
  it('reopens legacy empty projects and surfaces missing files without deleting saved edits', async () => {
    vi.spyOn(api, 'getWorkspace').mockResolvedValue({ name: 'Legacy', revision, snapshot: null });
    vi.spyOn(api, 'listAssets').mockResolvedValue([{ ...asset, name: undefined, available: false }]);
    await useWorkspaceStore.getState().open('project-1');
    expect(useMediaStore.getState().clips[0]).toMatchObject({ name: 'uuid.mp4', available: false });
    expect(useTimelineStore.getState().clips).toEqual([]);
  });
  it('appends independently imported assets rather than hiding files absent from the last snapshot', async () => {
    const snapshot = populated();
    snapshot.mediaOrder = [asset.id];
    vi.spyOn(api, 'getWorkspace').mockResolvedValue({ name: 'Project', revision, snapshot });
    vi.spyOn(api, 'listAssets').mockResolvedValue([reference, asset]);
    await useWorkspaceStore.getState().open('project-1');
    expect(useMediaStore.getState().clips.map((c) => c.id)).toEqual([asset.id, reference.id]);
  });
  it.each(['unknown-version', 'foreign-asset', 'missing-path', 'duplicate-order'])(
    'does not partially overwrite the active editor on %s',
    async (reason) => {
      const snapshot = populated();
      if (reason === 'unknown-version') Object.assign(snapshot, { version: 999 });
      if (reason === 'duplicate-order') snapshot.mediaOrder.push(asset.id);
      if (reason === 'missing-path') snapshot.timeline.clips[0]!.mediaId = '/deleted/file.mp4';
      const before = captureSnapshot();
      vi.spyOn(api, 'getWorkspace').mockResolvedValue({ name: 'Other', revision, snapshot });
      vi.spyOn(api, 'listAssets').mockResolvedValue(
        reason === 'foreign-asset' ? [{ ...asset, project_id: 'other' }, reference] : [asset, reference],
      );
      await expect(useWorkspaceStore.getState().open('project-1')).rejects.toThrow();
      expect(captureSnapshot()).toEqual(before);
      expect(useMediaStore.getState().projectName).toBe('مسابقه');
      expect(useWorkspaceStore.getState().error).toBeTruthy();
      expect(useWorkspaceStore.getState().navigating).toBe(false);
    },
  );
  it('recovers intentional deletion of unused selected/reference media without rewriting the saved snapshot', async () => {
    const snapshot = populated();
    snapshot.selectedAssetId = reference.id;
    const original = JSON.stringify(snapshot);
    vi.spyOn(api, 'getWorkspace').mockResolvedValue({ name: 'Project', revision, snapshot });
    vi.spyOn(api, 'listAssets').mockResolvedValue([asset]);
    const save = vi.spyOn(api, 'saveWorkspace');
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    await useWorkspaceStore.getState().open('project-1');
    expect(useMediaStore.getState().selectedId).toBeNull();
    expect(useWizardStore.getState().selectedReference).toBeNull();
    expect(useTimelineStore.getState().clips).toEqual(snapshot.timeline.clips);
    expect(useWorkspaceStore.getState()).toMatchObject({ dirty: false, status: 'idle' });
    expect(useWorkspaceStore.getState().warning).toContain('Saved media was deleted');
    expect(JSON.stringify(snapshot)).toBe(original);
    expect(save).not.toHaveBeenCalled();
    expect(console.warn).toHaveBeenCalled();
  });
  it('saves using the loaded revision and preserves edits made during the request', async () => {
    populated();
    unwatch = watchWorkspaceChanges();
    useWorkspaceStore.setState({ dirty: true, revision, revisionProject: 'project-1' });
    let resolve!: (value: Awaited<ReturnType<typeof api.saveWorkspace>>) => void;
    const savedSnapshot = captureSnapshot();
    const save = vi.spyOn(api, 'saveWorkspace').mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const pending = useWorkspaceStore.getState().save();
    const also = useWorkspaceStore.getState().save();
    expect(also).toBe(pending);
    useTimelineStore.getState().setPlayhead(4);
    useTimelineStore.getState().addBookmark('بعدی');
    resolve({ name: 'مسابقه', revision: nextRevision, snapshot: savedSnapshot });
    await pending;
    expect(save).toHaveBeenCalledOnce();
    expect(save).toHaveBeenCalledWith('project-1', revision, 'مسابقه', savedSnapshot);
    expect(useWorkspaceStore.getState()).toMatchObject({ dirty: true, revision: nextRevision, status: 'idle' });
  });
  it('attaches a newly imported project only if its backend snapshot is empty', async () => {
    populated();
    const get = vi.spyOn(api, 'getWorkspace').mockResolvedValue({ name: 'Project', revision, snapshot: null });
    const save = vi
      .spyOn(api, 'saveWorkspace')
      .mockResolvedValue({ name: 'Project', revision: nextRevision, snapshot: captureSnapshot() });
    await useWorkspaceStore.getState().save();
    expect(get).toHaveBeenCalledWith('project-1');
    expect(save).toHaveBeenCalledOnce();
    useWorkspaceStore.setState({ revision: null, revisionProject: null, dirty: true });
    get.mockResolvedValue({ name: 'Existing', revision: nextRevision, snapshot: captureSnapshot() });
    await expect(useWorkspaceStore.getState().save()).rejects.toThrow('before overwriting');
    expect(save).toHaveBeenCalledOnce();
    expect(useWorkspaceStore.getState().dirty).toBe(true);
  });
  it('reports conflicts without clearing dirty edits, changing the revision or switching projects', async () => {
    populated();
    useWorkspaceStore.setState({ dirty: true, revision, revisionProject: 'project-1' });
    vi.spyOn(api, 'saveWorkspace').mockRejectedValue(new ApiError('Changed elsewhere', 409));
    const get = vi.spyOn(api, 'getWorkspace');
    await expect(useWorkspaceStore.getState().open('other')).rejects.toThrow();
    expect(get).not.toHaveBeenCalled();
    expect(useWorkspaceStore.getState()).toMatchObject({
      dirty: true,
      revision,
      conflict: true,
      status: 'error',
      navigating: false,
    });
    expect(useMediaStore.getState().projectId).toBe('project-1');
    expect(useTimelineStore.getState().clips).toHaveLength(1);
  });
  it('refuses a switch if the user changed the document while the previous save was in flight', async () => {
    populated();
    unwatch = watchWorkspaceChanges();
    useWorkspaceStore.setState({ dirty: true, revision, revisionProject: 'project-1' });
    let finish!: (value: Awaited<ReturnType<typeof api.saveWorkspace>>) => void;
    vi.spyOn(api, 'saveWorkspace').mockReturnValue(
      new Promise((done) => {
        finish = done;
      }),
    );
    const get = vi.spyOn(api, 'getWorkspace');
    const switching = useWorkspaceStore.getState().open('other');
    usePostStore.getState().toggle('comparison');
    finish({ name: 'Project', revision: nextRevision, snapshot: captureSnapshot() });
    await expect(switching).rejects.toThrow('changed during save');
    expect(get).not.toHaveBeenCalled();
    expect(useMediaStore.getState().projectId).toBe('project-1');
  });
  it('blocks competing navigation and imports during a switch', async () => {
    populated();
    let finish!: (value: Awaited<ReturnType<typeof api.getWorkspace>>) => void;
    vi.spyOn(api, 'getWorkspace').mockReturnValue(
      new Promise((done) => {
        finish = done;
      }),
    );
    vi.spyOn(api, 'listAssets').mockResolvedValue([asset, reference]);
    const first = useWorkspaceStore.getState().open('project-1');
    await expect(useWorkspaceStore.getState().open('another')).rejects.toThrow('busy');
    await expect(useWorkspaceStore.getState().newProject()).rejects.toThrow('busy');
    finish({ name: 'Project', revision, snapshot: null });
    await first;
    useMediaStore.setState({ importing: true });
    await expect(useWorkspaceStore.getState().open('another')).rejects.toThrow('busy');
  });
  it('tracks edits but ignores playback, undo selection and backend health polling', () => {
    populated();
    unwatch = watchWorkspaceChanges();
    useTimelineStore.getState().togglePlaying();
    useAppStore.getState().setBackend('online', '1');
    useTimelineStore.getState().clearSelection();
    expect(useWorkspaceStore.getState().dirty).toBe(false);
    useTimelineStore.getState().setPlayhead(4);
    expect(useWorkspaceStore.getState().dirty).toBe(true);
  });
  it('generates unique clip and bookmark IDs even after hydrating legacy numeric IDs', () => {
    populated();
    const first = useTimelineStore.getState().clips[0]!;
    useTimelineStore.setState({
      clips: [
        { ...first, id: 'clip-1' },
        { ...first, id: 'clip-1-b', start: 20 },
      ],
      selectedIds: ['clip-1'],
      playhead: 3,
    });
    useTimelineStore.getState().splitAtPlayhead();
    useTimelineStore.setState({ selectedIds: ['clip-1'], playhead: 2.5 });
    useTimelineStore.getState().splitAtPlayhead();
    useTimelineStore.getState().addBookmark('New');
    const ids = useTimelineStore.getState().clips.map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
  it('retains unsaved edits on network failure and supports explicit retry', async () => {
    populated();
    useWorkspaceStore.setState({ dirty: true, revision, revisionProject: 'project-1' });
    const save = vi.spyOn(api, 'saveWorkspace').mockRejectedValue(new Error('offline'));
    await expect(useWorkspaceStore.getState().save()).rejects.toThrow('offline');
    expect(useWorkspaceStore.getState()).toMatchObject({ dirty: true, status: 'error' });
    save.mockResolvedValue({ name: 'Project', revision: nextRevision, snapshot: captureSnapshot() });
    await useWorkspaceStore.getState().save();
    expect(useWorkspaceStore.getState()).toMatchObject({ dirty: false, status: 'idle' });
  });
  it('refreshes project choices and creates a separate blank project', async () => {
    populated();
    vi.spyOn(api, 'listProjects').mockResolvedValue([{ id: 'project-1', name: 'Existing' }]);
    await useWorkspaceStore.getState().refresh();
    expect(useWorkspaceStore.getState().projects).toEqual([{ id: 'project-1', name: 'Existing' }]);
    vi.spyOn(api, 'createProject').mockResolvedValue({ id: 'new', name: 'Blank' });
    vi.spyOn(api, 'getWorkspace').mockResolvedValue({ name: 'Blank', revision, snapshot: null });
    await useWorkspaceStore.getState().newProject();
    expect(useMediaStore.getState()).toMatchObject({ projectId: 'new', clips: [], selectedId: null });
    expect(useTimelineStore.getState().clips).toEqual([]);
  });
  it('loads only the last project ID from browser storage and does not store media or snapshots there', async () => {
    localStorage.setItem(LAST_PROJECT_STORAGE, 'project-1');
    useWorkspaceStore.setState({ initialized: false });
    const get = vi.spyOn(api, 'getWorkspace').mockResolvedValue({ name: 'Persisted', revision, snapshot: null });
    vi.spyOn(api, 'listAssets').mockResolvedValue([asset]);
    await Promise.all([useWorkspaceStore.getState().initialize(), useWorkspaceStore.getState().initialize()]);
    expect(get).toHaveBeenCalledOnce();
    expect(localStorage.length).toBe(1);
    expect(useMediaStore.getState().clips[0]!.name).toBe(asset.name);
  });
  it('shows an explicit storage warning without treating a committed SQLite save as a failed save', async () => {
    populated();
    useWorkspaceStore.setState({ dirty: true, revision, revisionProject: 'project-1' });
    vi.spyOn(api, 'saveWorkspace').mockResolvedValue({
      name: 'Project',
      revision: nextRevision,
      snapshot: captureSnapshot(),
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Storage disabled');
    });
    await useWorkspaceStore.getState().save();
    expect(useWorkspaceStore.getState()).toMatchObject({ dirty: false, status: 'idle' });
    expect(useWorkspaceStore.getState().warning).toContain('project picker');
    expect(console.error).toHaveBeenCalled();
  });
});
