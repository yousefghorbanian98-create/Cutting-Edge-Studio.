/** Adapter between our timeline store and @xzdarcy/react-timeline-editor rows. */

import type { TimelineRow } from '@xzdarcy/timeline-engine';
import type { TimelineClip, Track } from './timelineMath';

export const EFFECT_IDS = { video: 'video', audio: 'audio' } as const;

export interface EditorActionData {
  clipId: string;
  mediaId: string;
  name: string;
}

/** Map store clips onto editor rows, one row per track (stable order). */
export function toEditorData(tracks: readonly Track[], clips: readonly TimelineClip[]): TimelineRow[] {
  return tracks.map((track) => ({
    id: track.id,
    actions: clips
      .filter((clip) => clip.trackId === track.id)
      .sort((a, b) => a.start - b.start)
      .map((clip) => ({
        id: clip.id,
        start: Number(clip.start.toFixed(3)),
        end: Number((clip.start + clip.duration).toFixed(3)),
        effectId: EFFECT_IDS[clip.kind],
        flexible: true,
        movable: !track.locked,
        resizable: !track.locked,
        data: {
          clipId: clip.id,
          mediaId: clip.mediaId,
          name: clip.name,
        } satisfies EditorActionData,
      })),
  }));
}

export interface EditorChange {
  id: string;
  trackId: string;
  start: number;
  end: number;
}

/** Flatten editor rows back into plain change records (no library types leak out). */
export function fromEditorData(editorData: readonly TimelineRow[]): EditorChange[] {
  const changes: EditorChange[] = [];
  for (const row of editorData) {
    for (const action of row.actions) {
      changes.push({
        id: action.id,
        trackId: row.id,
        start: action.start,
        end: action.end,
      });
    }
  }
  return changes;
}

/** Media-panel clip → new timeline clip (5s default, as the P2 MVP rule). */
export function toTimelineClip(
  media: { path: string; name: string; kind: 'video' | 'audio' },
  options: { id: string; trackId: string; at: number; duration?: number },
): TimelineClip {
  return {
    id: options.id,
    mediaId: media.path,
    name: media.name,
    trackId: options.trackId,
    start: Math.max(0, options.at),
    duration: options.duration ?? 5,
    inPoint: 0,
    kind: media.kind,
  };
}
