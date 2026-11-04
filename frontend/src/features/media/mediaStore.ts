import { create } from 'zustand';
import { api } from '../../lib/api';
import { type CandidateFile, kindOf, validateFiles } from '../../lib/files';

export interface MediaClip {
  id: string;
  name: string;
  size: number;
  path: string;
  kind: 'video' | 'audio';
  role: 'source' | 'reference';
  assetId?: string;
  duration?: number;
  width?: number;
  height?: number;
  fps?: number;
}

export interface ImportOutcome {
  added: MediaClip[];
  rejected: { name: string; reason: string }[];
}

interface MediaState {
  clips: MediaClip[];
  projectId: string | null;
  importing: boolean;
  selectedId: string | null;
  selectClip: (id: string) => void;
  importFiles: (files: readonly File[], role?: MediaClip['role']) => Promise<ImportOutcome>;
  deleteImported: (id: string) => Promise<void>;
  /** Import files, de-duplicating by path. Returns what happened (no silent drops). */
  addFiles: (files: readonly CandidateFile[], role?: MediaClip['role']) => ImportOutcome;
  removeClip: (id: string) => void;
  reorder: (fromId: string, toId: string) => void;
  clear: () => void;
}

let sequence = 0;

function nextId(): string {
  sequence += 1;
  return `clip-${sequence}`;
}

export const useMediaStore = create<MediaState>((set, get) => ({
  clips: [],
  projectId: null,
  importing: false,
  selectedId: null,
  selectClip: (id) => set({ selectedId: id }),
  importFiles: async (files, role = 'source') => {
    // Serial imports keep memory/disk pressure bounded and prevent duplicate project creation.
    if (get().importing) throw new Error('An import is already in progress');
    set({ importing: true });
    const outcome: ImportOutcome = { added: [], rejected: [] };
    try {
      for (const file of files) {
        const { rejected } = validateFiles([{ name: file.name, size: file.size, path: file.name }]);
        if (rejected.length) {
          outcome.rejected.push({ name: file.name, reason: rejected[0]?.reason ?? 'extension' });
          continue;
        }
        if (get().clips.some(c => c.name === file.name && c.size === file.size && c.role === role)) {
          outcome.rejected.push({ name: file.name, reason: 'duplicate' });
          continue;
        }
        try {
          let projectId = get().projectId;
          if (!projectId) {
            projectId = (await api.createProject()).id;
            set({ projectId });
          }
          const asset = await api.uploadAsset(projectId, file, role);
          const clip: MediaClip = {
            id: asset.id, assetId: asset.id, path: asset.path,
            name: file.name, size: file.size, kind: asset.kind, role,
            duration: asset.duration, width: asset.width, height: asset.height, fps: asset.fps,
          };
          set(state => ({ clips: [...state.clips, clip], selectedId: clip.id }));
          outcome.added.push(clip);
        } catch (error) {
          console.error('media.import.failed', file.name, error);
          outcome.rejected.push({ name: file.name, reason: String(error) });
        }
      }
      return outcome;
    } finally {
      set({ importing: false });
    }
  },
  deleteImported: async (id) => {
    const clip = get().clips.find(item => item.id === id);
    if (clip?.assetId) await api.deleteAsset(clip.assetId);
    set(state => ({
      clips: state.clips.filter(item => item.id !== id),
      selectedId: state.selectedId === id ? null : state.selectedId,
    }));
  },
  addFiles: (files, role = 'source') => {
    const existing = new Set(get().clips.map((clip) => clip.path));
    const { accepted, rejected } = validateFiles(files);
    const added: MediaClip[] = [];
    const rejections: ImportOutcome['rejected'] = rejected.map((item) => ({
      name: item.name,
      reason: item.reason,
    }));

    for (const file of accepted) {
      if (existing.has(file.path)) {
        rejections.push({ name: file.name, reason: 'duplicate' });
        continue;
      }
      existing.add(file.path);
      const kind = kindOf(file.name);
      if (kind === null) continue; // validated above; keeps the type narrow
      added.push({ id: nextId(), name: file.name, size: file.size, path: file.path, kind, role });
    }

    if (added.length > 0) {
      set((state) => ({ clips: [...state.clips, ...added] }));
    }
    return { added, rejected: rejections };
  },
  removeClip: (id) => set((state) => ({ clips: state.clips.filter((clip) => clip.id !== id) })),
  reorder: (fromId, toId) =>
    set((state) => {
      const from = state.clips.findIndex((clip) => clip.id === fromId);
      const to = state.clips.findIndex((clip) => clip.id === toId);
      if (from === -1 || to === -1 || from === to) return state;
      const clips = [...state.clips];
      const [moved] = clips.splice(from, 1);
      if (!moved) return state;
      clips.splice(to, 0, moved);
      return { clips };
    }),
  clear: () => set({ clips: [], projectId: null, importing: false, selectedId: null }),
}));

/** Reference clips only (Style Match reads exactly one). */
export function selectReferences(clips: readonly MediaClip[]): MediaClip[] {
  return clips.filter((clip) => clip.role === 'reference');
}
