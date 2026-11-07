import { describe, expect, it } from 'vitest';
import { EFFECT_IDS, fromEditorData, toEditorData, toTimelineClip } from './timelineAdapter';
import type { TimelineClip, Track } from './timelineMath';

const tracks: Track[] = [
  { id: 'v1', name: 'V1', kind: 'video', locked: false, muted: false },
  { id: 'a1', name: 'A1', kind: 'audio', locked: false, muted: false },
];

const clip = (overrides: Partial<TimelineClip> = {}): TimelineClip => ({
  id: 'c1',
  mediaId: '/m/a.mp4',
  name: 'a.mp4',
  trackId: 'v1',
  start: 1,
  duration: 2,
  inPoint: 0,
  kind: 'video',
  ...overrides,
});

describe('timeline adapter', () => {
  it('creates one row per track, sorted by start', () => {
    const rows = toEditorData(tracks, [clip({ id: 'b', start: 5 }), clip({ id: 'a', start: 1 })]);
    expect(rows).toHaveLength(2);
    expect(rows[0]?.id).toBe('v1');
    expect(rows[0]?.actions.map((action) => action.id)).toEqual(['a', 'b']);
    expect(rows[1]?.actions).toEqual([]);
  });

  it('maps kinds to effect ids and honours locked tracks', () => {
    const rows = toEditorData(
      [{ ...tracks[0]!, locked: true }, tracks[1]!],
      [clip(), clip({ id: 'aud', trackId: 'a1', kind: 'audio' })],
    );
    expect(rows[0]?.actions[0]?.effectId).toBe(EFFECT_IDS.video);
    expect(rows[0]?.actions[0]?.movable).toBe(false);
    expect(rows[1]?.actions[0]?.effectId).toBe(EFFECT_IDS.audio);
  });

  it('flattens rows back to change records', () => {
    const rows = toEditorData(tracks, [clip()]);
    expect(fromEditorData(rows)).toEqual([{ id: 'c1', trackId: 'v1', start: 1, end: 3 }]);
  });

  it('builds a store clip from a media item', () => {
    const built = toTimelineClip({ path: '/m/x.mp4', name: 'x.mp4', kind: 'video' }, { id: 'n1', trackId: 'v1', at: -3 });
    expect(built.start).toBe(0);
    expect(built.duration).toBe(5);
    expect(built.inPoint).toBe(0);
  });
});
