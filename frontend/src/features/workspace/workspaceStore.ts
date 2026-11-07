import { create } from 'zustand';
import { z } from 'zod';
import { api, ApiError, type AssetResponse, type ProjectResponse } from '../../lib/api';
import { useAppStore } from '../../store/useAppStore';
import { useMediaStore, type MediaClip } from '../media/mediaStore';
import { usePostStore } from '../post/postStore';
import { useWizardStore } from '../stylematch/wizardStore';
import { useTimelineStore } from '../timeline/timelineStore';
import { snapshotSchema, workspaceSchema, type WorkspaceSnapshot } from './schema';

export const LAST_PROJECT_STORAGE = 'cutting-edge.last-project';
interface WorkspaceState {
  initialized: boolean;
  navigating: boolean;
  status: 'idle' | 'loading' | 'saving' | 'error';
  dirty: boolean;
  generation: number;
  error: string | null;
  conflict: boolean;
  warning: string | null;
  revision: string | null;
  revisionProject: string | null;
  projects: ProjectResponse[];
  initialize: () => Promise<void>;
  refresh: () => Promise<void>;
  save: () => Promise<void>;
  open: (id: string, discard?: boolean) => Promise<void>;
  newProject: () => Promise<void>;
  markDirty: () => void;
}
let saving: Promise<void> | null = null;
let initializing: Promise<void> | null = null;

function remember(id: string): void {
  try {
    localStorage.setItem(LAST_PROJECT_STORAGE, id);
  } catch (error) {
    console.error('workspace.remember.failed', error);
    useWorkspaceStore.setState({ warning: 'Browser storage is unavailable; reopen through the project picker.' });
  }
}

export function captureSnapshot(): WorkspaceSnapshot {
  const media = useMediaStore.getState();
  const timeline = useTimelineStore.getState();
  const wizard = useWizardStore.getState();
  const post = usePostStore.getState();
  const app = useAppStore.getState();
  return {
    version: 1,
    timeline: {
      tracks: timeline.tracks,
      clips: timeline.clips,
      bookmarks: timeline.bookmarks,
      duration: timeline.duration,
      playhead: timeline.playhead,
      pxPerSecond: timeline.pxPerSecond,
      snapEnabled: timeline.snapEnabled,
    },
    mediaOrder: media.clips.flatMap((c) => (c.assetId ? [c.assetId] : [])),
    selectedAssetId: media.clips.find((c) => c.id === media.selectedId)?.assetId ?? null,
    referenceAssetId:
      media.clips.find((c) => c.role === 'reference' && c.path === wizard.selectedReference)?.assetId ?? null,
    wizardStep: wizard.stepIndex,
    post: {
      enabled: post.enabled,
      presetId: post.presetId as WorkspaceSnapshot['post']['presetId'],
      layout: post.layout,
      captionFormat: post.captionFormat,
      quality: post.quality,
    },
    appearance: { language: app.language, theme: app.theme },
  };
}

function importedClips(assets: AssetResponse[], order: string[]): MediaClip[] {
  const validated = z
    .array(
      z.object({
        id: z.string().min(1),
        project_id: z.string().min(1),
        path: z.string().min(1),
        name: z.string().optional(),
        size_bytes: z.number().nonnegative().optional(),
        role: z.enum(['source', 'reference', 'music', 'broll', 'voiceover']),
        kind: z.enum(['video', 'audio']),
        duration: z.number().finite().nonnegative(),
        width: z.number(),
        height: z.number(),
        fps: z.number(),
        available: z.boolean().optional(),
      }),
    )
    .parse(assets);
  const byId = new Map(validated.map((a) => [a.id, a]));
  if (new Set(order).size !== order.length) throw new Error('Saved workspace has duplicate media IDs');
  const ordered = [
    ...order.filter((id) => byId.has(id)),
    ...validated.map((a) => a.id).filter((id) => !order.includes(id)),
  ];
  return ordered.map((id) => {
    const asset = byId.get(id)!;
    return {
      id,
      assetId: id,
      path: asset.path,
      name: asset.name || asset.path.split(/[/\\]/).pop() || id,
      size: asset.size_bytes ?? 0,
      kind: asset.kind,
      role: asset.role,
      duration: asset.duration,
      width: asset.width,
      height: asset.height,
      fps: asset.fps,
      available: asset.available ?? true,
    };
  });
}

function applyWorkspace(
  id: string,
  name: string,
  assets: AssetResponse[],
  snapshot: WorkspaceSnapshot | null,
): string | null {
  const clips = importedClips(assets, snapshot?.mediaOrder ?? []);
  if (assets.some((asset) => asset.project_id !== id)) throw new Error('Asset belongs to another project');
  if (snapshot) {
    if (snapshot.timeline.clips.some((c) => !clips.some((m) => m.path === c.mediaId)))
      throw new Error('Saved timeline media is no longer registered; original snapshot preserved.');
  }
  // All validation happens before touching the active workspace.
  useTimelineStore.getState().reset();
  usePostStore.getState().reset();
  useWizardStore.getState().reset();
  useMediaStore.setState({
    projectId: id,
    projectName: name,
    clips,
    selectedId: clips.find((c) => c.id === snapshot?.selectedAssetId)?.id ?? null,
  });
  if (snapshot) {
    useTimelineStore.setState({ ...snapshot.timeline, playing: false, selectedIds: [], past: [], future: [] });
    usePostStore.setState(snapshot.post);
    useWizardStore.setState({
      stepIndex: snapshot.wizardStep,
      selectedReference: clips.find((c) => c.id === snapshot.referenceAssetId)?.path ?? null,
      completed: false,
    });
    useAppStore.getState().setLanguage(snapshot.appearance.language);
    useAppStore.getState().setTheme(snapshot.appearance.theme);
  }
  const savedIds = snapshot ? [...snapshot.mediaOrder, snapshot.selectedAssetId, snapshot.referenceAssetId] : [];
  const deleted = savedIds.filter((key) => key && !clips.some((c) => c.id === key));
  if (deleted.length) {
    console.warn('workspace.deleted-media', deleted);
    return 'Saved media was deleted from this project; timeline edits and original saved bytes are preserved.';
  }
  return null;
}

function report(error: unknown): void {
  console.error('workspace.operation.failed', error);
  useWorkspaceStore.setState({
    status: 'error',
    error:
      error instanceof z.ZodError
        ? `Invalid or unsupported workspace: ${error.issues[0]?.message ?? 'validation failed'}`
        : String(error),
    conflict: error instanceof ApiError && error.status === 409,
  });
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  initialized: false,
  navigating: false,
  status: 'idle',
  dirty: false,
  generation: 0,
  error: null,
  conflict: false,
  warning: null,
  revision: null,
  revisionProject: null,
  projects: [],
  markDirty: () => {
    if (!get().initialized || get().status === 'loading' || !useMediaStore.getState().projectId) return;
    set((state) => ({
      dirty: true,
      generation: state.generation + 1,
      status: state.status === 'error' && !state.conflict ? 'idle' : state.status,
    }));
  },
  initialize: () => {
    if (initializing) return initializing;
    if (get().initialized) return Promise.resolve();
    initializing = (async () => {
      try {
        const id = localStorage.getItem(LAST_PROJECT_STORAGE);
        if (id) await get().open(id, true);
      } catch (error) {
        report(error);
      } finally {
        set({ initialized: true });
      }
    })().finally(() => {
      initializing = null;
    });
    return initializing;
  },
  refresh: async () => {
    try {
      const projects = z
        .array(z.object({ id: z.string().min(1), name: z.string().min(1) }))
        .parse(await api.listProjects());
      set({ projects });
    } catch (error) {
      report(error);
      throw error;
    }
  },
  save: () => {
    if (saving) return saving;
    saving = (async () => {
      const media = useMediaStore.getState();
      if (!media.projectId || media.importing) return;
      const id = media.projectId;
      const generation = get().generation;
      set({ status: 'saving', error: null });
      try {
        const snapshot = snapshotSchema.parse(captureSnapshot());
        const name = z.string().trim().min(1).max(200).parse(media.projectName);
        let revision = get().revisionProject === id ? get().revision : null;
        if (!revision) {
          const current = workspaceSchema.parse(await api.getWorkspace(id));
          if (current.snapshot) throw new Error('Open the saved project before overwriting its workspace');
          revision = current.revision;
        }
        const saved = workspaceSchema.parse(await api.saveWorkspace(id, revision, name, snapshot));
        set({
          revision: saved.revision,
          revisionProject: id,
          status: 'idle',
          dirty: get().generation !== generation,
          error: null,
          conflict: false,
        });
        remember(id);
      } catch (error) {
        report(error);
        throw error;
      }
    })().finally(() => {
      saving = null;
    });
    return saving;
  },
  open: async (id, discard = false) => {
    if (get().navigating || useMediaStore.getState().importing) throw new Error('Workspace is busy');
    set({ navigating: true });
    try {
      if (!discard && get().dirty) {
        await get().save();
        if (get().dirty) throw new Error('Workspace changed during save; finish editing before switching');
      }
      if (saving) {
        try {
          await saving;
        } catch (error) {
          if (!discard) throw error;
          console.error('workspace.discard.failed-save', error);
        }
      }
      set({ status: 'loading', error: null });
      const [saved, assets] = await Promise.all([api.getWorkspace(id), api.listAssets(id)]);
      const workspace = workspaceSchema.parse(saved);
      const warning = applyWorkspace(id, workspace.name, assets, workspace.snapshot);
      set({
        revision: workspace.revision,
        revisionProject: id,
        dirty: false,
        status: 'idle',
        conflict: false,
        warning,
      });
      remember(id);
    } catch (error) {
      report(error);
      throw error;
    } finally {
      set({ navigating: false });
    }
  },
  newProject: async () => {
    if (get().navigating || useMediaStore.getState().importing) throw new Error('Workspace is busy');
    set({ navigating: true });
    try {
      if (get().dirty) {
        await get().save();
        if (get().dirty) throw new Error('Unsaved changes remain');
      }
      if (saving) await saving;
      set({ status: 'loading', error: null });
      const project = await api.createProject();
      const workspace = workspaceSchema.parse(await api.getWorkspace(project.id));
      applyWorkspace(project.id, workspace.name, [], null);
      set({
        revision: workspace.revision,
        revisionProject: project.id,
        dirty: false,
        status: 'idle',
        conflict: false,
        warning: null,
      });
      remember(project.id);
    } catch (error) {
      report(error);
      throw error;
    } finally {
      set({ navigating: false });
    }
  },
}));

/** Store subscriptions track document data, not playback flags, history or backend polling. */
export function watchWorkspaceChanges(): () => void {
  const fingerprint = () => JSON.stringify([useMediaStore.getState().projectName, captureSnapshot()]);
  let previous = fingerprint();
  const changed = () => {
    const next = fingerprint();
    if (next !== previous) {
      previous = next;
      useWorkspaceStore.getState().markDirty();
    }
  };
  const disposers = [
    useMediaStore.subscribe(changed),
    useTimelineStore.subscribe(changed),
    usePostStore.subscribe(changed),
    useWizardStore.subscribe(changed),
    useAppStore.subscribe(changed),
  ];
  return () => disposers.forEach((dispose) => dispose());
}
