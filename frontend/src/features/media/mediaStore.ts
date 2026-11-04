import { create } from 'zustand';
import { type CandidateFile, kindOf, validateFiles } from '../../lib/files';

export interface MediaClip {
  id: string;
  name: string;
  size: number;
  path: string;
  kind: 'video' | 'audio';
  role: 'source' | 'reference';
}

export interface ImportOutcome {
  added: MediaClip[];
  rejected: { name: string; reason: string }[];
}

interface MediaState {
  clips: MediaClip[];
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
  clear: () => set({ clips: [] }),
}));

/** Reference clips only (Style Match reads exactly one). */
export function selectReferences(clips: readonly MediaClip[]): MediaClip[] {
  return clips.filter((clip) => clip.role === 'reference');
}
