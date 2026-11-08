import { produce } from 'immer';
import { create } from 'zustand';
import {
  type TimelineClip,
  type Track,
  MIN_CLIP_SECONDS,
  ZOOM_RANGE,
  clamp,
  clipEnd,
  findFreeSlot,
  splitClipAt,
  trimClipEdge,
} from '../features/timeline/timelineMath';

export interface Bookmark {
  id: string;
  time: number;
  label: string;
  color: string;
}

interface HistoryEntry {
  clips: TimelineClip[];
  bookmarks: Bookmark[];
}

export interface TimelineState {
  duration: number;
  playhead: number;
  playing: boolean;
  pxPerSecond: number;
  snapEnabled: boolean;
  tracks: Track[];
  clips: TimelineClip[];
  bookmarks: Bookmark[];
  selectedIds: string[];
  past: HistoryEntry[];
  future: HistoryEntry[];

  setDuration: (seconds: number) => void;
  setPlayhead: (seconds: number) => void;
  togglePlaying: () => void;
  setZoom: (pxPerSecond: number) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  toggleSnap: () => void;

  addClip: (input: { mediaId: string; name: string; kind: 'video' | 'audio'; at?: number; duration?: number }) => TimelineClip | null;
  moveClip: (id: string, start: number) => boolean;
  trimClip: (id: string, edge: 'start' | 'end', deltaSeconds: number) => boolean;
  splitAtPlayhead: () => number;
  removeSelected: () => number;
  selectClip: (id: string, additive?: boolean) => void;
  clearSelection: () => void;

  addBookmark: (label?: string) => Bookmark | null;
  removeBookmark: (id: string) => void;

  undo: () => boolean;
  redo: () => boolean;
  reset: () => void;
}

const DEFAULT_TRACKS: Track[] = [
  { id: 'v1', name: 'V1', kind: 'video', locked: false, muted: false },
  { id: 'v2', name: 'V2', kind: 'video', locked: false, muted: false },
  { id: 'a1', name: 'A1', kind: 'audio', locked: false, muted: false },
];

const HISTORY_LIMIT = 50;
const nextId = (prefix: string): string => {
  return `${prefix}-${crypto.randomUUID()}`;
};

const initialState = {
  duration: 120,
  playhead: 0,
  playing: false,
  pxPerSecond: 40,
  snapEnabled: true,
  tracks: DEFAULT_TRACKS,
  clips: [] as TimelineClip[],
  bookmarks: [] as Bookmark[],
  selectedIds: [] as string[],
  past: [] as HistoryEntry[],
  future: [] as HistoryEntry[],
};

export const useTimelineStore = create<TimelineState>((set, get) => {
  /** Record an undo point from the current clip/bookmark state. */
  const pushHistory = (): void => {
    const { clips, bookmarks, past } = get();
    const entry: HistoryEntry = { clips, bookmarks };
    set({ past: [...past, entry].slice(-HISTORY_LIMIT), future: [] });
  };

  const applyClips = (updater: (draft: TimelineClip[]) => void): void => {
    set(
      produce((draft: TimelineState) => {
        updater(draft.clips);
        const end = draft.clips.reduce((max, clip) => Math.max(max, clipEnd(clip)), 0);
        draft.duration = Math.max(30, Math.ceil(end + 10));
      }),
    );
  };

  return {
    ...initialState,

    setDuration: (seconds) => set({ duration: Math.max(1, seconds) }),
    setPlayhead: (seconds) => {
      const { duration } = get();
      set({ playhead: clamp(seconds, 0, duration) });
    },
    togglePlaying: () => set((state) => ({ playing: !state.playing })),
    setZoom: (pxPerSecond) => set({ pxPerSecond: clamp(pxPerSecond, ZOOM_RANGE.min, ZOOM_RANGE.max) }),
    zoomIn: () => set((state) => ({ pxPerSecond: clamp(state.pxPerSecond * 1.25, ZOOM_RANGE.min, ZOOM_RANGE.max) })),
    zoomOut: () => set((state) => ({ pxPerSecond: clamp(state.pxPerSecond / 1.25, ZOOM_RANGE.min, ZOOM_RANGE.max) })),
    toggleSnap: () => set((state) => ({ snapEnabled: !state.snapEnabled })),

    addClip: ({ mediaId, name, kind, at, duration: mediaDuration }) => {
      const state = get();
      const track = state.tracks.find((item) => item.kind === kind && !item.locked);
      if (!track) return null;
      const desired = at ?? state.playhead;
      const duration = mediaDuration && Number.isFinite(mediaDuration) && mediaDuration > 0 ? mediaDuration : 5;
      const start = findFreeSlot(state.clips, track.id, desired, duration);
      const clip: TimelineClip = {
        id: nextId('clip'),
        mediaId,
        name,
        trackId: track.id,
        start,
        duration,
        inPoint: 0,
        kind,
      };
      pushHistory();
      applyClips((draft) => {
        draft.push(clip);
      });
      set({ selectedIds: [clip.id] });
      return clip;
    },

    moveClip: (id, start) => {
      const state = get();
      const clip = state.clips.find((item) => item.id === id);
      if (!clip) return false;
      const track = state.tracks.find((item) => item.id === clip.trackId);
      if (track?.locked) return false;
      const resolved = findFreeSlot(state.clips, clip.trackId, Math.max(0, start), clip.duration, id);
      if (Math.abs(resolved - clip.start) < 1e-6) return false;
      pushHistory();
      applyClips((draft) => {
        const target = draft.find((item) => item.id === id);
        if (target) target.start = resolved;
      });
      return true;
    },

    trimClip: (id, edge, deltaSeconds) => {
      const clip = get().clips.find((item) => item.id === id);
      if (!clip) return false;
      const result = trimClipEdge(clip, edge, deltaSeconds);
      if (!result.changed) return false;
      pushHistory();
      applyClips((draft) => {
        const index = draft.findIndex((item) => item.id === id);
        if (index >= 0 && result.clip) draft[index] = result.clip;
      });
      return true;
    },

    splitAtPlayhead: () => {
      const { clips, playhead } = get();
      const targets = clips.filter((clip) => clip.start < playhead && clipEnd(clip) > playhead);
      if (targets.length === 0) return 0;
      pushHistory();
      let count = 0;
      applyClips((draft) => {
        for (const clip of targets) {
          const index = draft.findIndex((item) => item.id === clip.id);
          const split = splitClipAt({ ...clip }, playhead);
          if (index >= 0 && split) {
            draft.splice(index, 1, split[0], { ...split[1], id: nextId('clip') });
            count += 1;
          }
        }
      });
      return count;
    },

    removeSelected: () => {
      const { selectedIds, clips } = get();
      if (selectedIds.length === 0) return 0;
      const removable = clips.filter((clip) => selectedIds.includes(clip.id));
      if (removable.length === 0) return 0;
      pushHistory();
      applyClips((draft) => {
        for (let index = draft.length - 1; index >= 0; index -= 1) {
          const clip = draft[index];
          if (clip && selectedIds.includes(clip.id)) draft.splice(index, 1);
        }
      });
      set({ selectedIds: [] });
      return removable.length;
    },

    selectClip: (id, additive = false) =>
      set((state) => ({
        selectedIds: additive
          ? state.selectedIds.includes(id)
            ? state.selectedIds.filter((item) => item !== id)
            : [...state.selectedIds, id]
          : [id],
      })),
    clearSelection: () => set({ selectedIds: [] }),

    addBookmark: (label) => {
      const { playhead, bookmarks } = get();
      if (bookmarks.some((item) => Math.abs(item.time - playhead) < MIN_CLIP_SECONDS)) return null;
      const bookmark: Bookmark = {
        id: nextId('mark'),
        time: playhead,
        label: label ?? `M${bookmarks.length + 1}`,
        color: 'var(--accent-primary)',
      };
      pushHistory();
      set({ bookmarks: [...bookmarks, bookmark].sort((a, b) => a.time - b.time) });
      return bookmark;
    },
    removeBookmark: (id) => set((state) => ({ bookmarks: state.bookmarks.filter((item) => item.id !== id) })),

    undo: () => {
      const { past, clips, bookmarks, future } = get();
      const previous = past[past.length - 1];
      if (!previous) return false;
      set({
        past: past.slice(0, -1),
        clips: previous.clips,
        bookmarks: previous.bookmarks,
        future: [{ clips, bookmarks }, ...future].slice(0, HISTORY_LIMIT),
        selectedIds: [],
      });
      return true;
    },
    redo: () => {
      const { future, clips, bookmarks, past } = get();
      const next = future[0];
      if (!next) return false;
      set({
        future: future.slice(1),
        clips: next.clips,
        bookmarks: next.bookmarks,
        past: [...past, { clips, bookmarks }].slice(-HISTORY_LIMIT),
        selectedIds: [],
      });
      return true;
    },
    reset: () => set({ ...initialState }),
  };
});

/** Snap targets for the current state: clip edges + bookmark times + zero. */
export function snapTargets(clips: readonly TimelineClip[], bookmarks: readonly Bookmark[], excludeId?: string): number[] {
  const targets = [0];
  for (const clip of clips) {
    if (clip.id === excludeId) continue;
    targets.push(clip.start, clipEnd(clip));
  }
  for (const bookmark of bookmarks) targets.push(bookmark.time);
  return targets;
}
