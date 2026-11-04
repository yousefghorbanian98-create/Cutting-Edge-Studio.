import { describe, expect, it } from 'vitest';
import {
  MIN_CLIP_SECONDS,
  clamp,
  clipEnd,
  findFreeSlot,
  fitZoom,
  overlaps,
  pixelsToSeconds,
  quantize,
  rulerTicks,
  secondsToPixels,
  snapTime,
  splitClipAt,
  timecode,
  trimClipEdge,
  type TimelineClip,
} from './timelineMath';

const clip = (overrides: Partial<TimelineClip> = {}): TimelineClip => ({
  id: 'c1',
  mediaId: '/m/a.mp4',
  name: 'a.mp4',
  trackId: 'v1',
  start: 2,
  duration: 4,
  inPoint: 0,
  kind: 'video',
  ...overrides,
});

describe('coordinate conversion', () => {
  it('round-trips seconds and pixels', () => {
    expect(secondsToPixels(2.5, 40)).toBe(100);
    expect(pixelsToSeconds(100, 40)).toBe(2.5);
  });

  it('never divides by a non-positive scale', () => {
    expect(pixelsToSeconds(100, 0)).toBe(0);
  });

  it('clamps and guards NaN', () => {
    expect(clamp(5, 0, 3)).toBe(3);
    expect(clamp(-1, 0, 3)).toBe(0);
    expect(clamp(Number.NaN, 2, 3)).toBe(2);
  });
});

describe('snapping', () => {
  const context = { pxPerSecond: 40, grid: 0.5, targets: [0, 2, 6], enabled: true };

  it('snaps to a nearby target within 8px', () => {
    // 8px at 40px/s = 0.2s
    expect(snapTime(2.1, context)).toEqual({ value: 2, snapped: true });
    expect(snapTime(5.9, context)).toEqual({ value: 6, snapped: true });
  });

  it('falls back to the grid when no target is close', () => {
    const result = snapTime(3.26, context);
    expect(result.value).toBeCloseTo(3.5, 5);
  });

  it('does nothing when snapping is disabled', () => {
    expect(snapTime(2.1, { ...context, enabled: false })).toEqual({ value: 2.1, snapped: false });
  });

  it('quantizes only for positive grids', () => {
    expect(quantize(1.26, 0.5)).toBeCloseTo(1.5, 5);
    expect(quantize(1.26, 0)).toBe(1.26);
  });
});

describe('overlap and placement', () => {
  it('detects overlaps only on the same track', () => {
    expect(overlaps(clip(), clip({ id: 'c2', start: 3 }))).toBe(true);
    expect(overlaps(clip(), clip({ id: 'c2', start: 3, trackId: 'v2' }))).toBe(false);
    expect(overlaps(clip(), clip({ id: 'c2', start: 6 }))).toBe(false); // touching is fine
  });

  it('pushes the new clip past occupied space', () => {
    const single = [clip({ id: 'a', start: 0, duration: 5 })];
    expect(findFreeSlot(single, 'v1', 1, 3)).toBe(5);

    const stacked = [clip({ id: 'a', start: 0, duration: 5 }), clip({ id: 'b', start: 6, duration: 2 })];
    expect(findFreeSlot(stacked, 'v1', 1, 3)).toBe(8);
    expect(findFreeSlot(stacked, 'v1', 100, 3)).toBe(100);
  });

  it('ignores the clip being moved', () => {
    const existing = [clip({ id: 'a', start: 0, duration: 5 })];
    expect(findFreeSlot(existing, 'v1', 1, 2, 'a')).toBe(1);
  });
});

describe('split and trim', () => {
  it('splits into two clips with a correct inPoint', () => {
    const result = splitClipAt(clip(), 4);
    expect(result).not.toBeNull();
    const [left, right] = result ?? [];
    expect(left?.duration).toBe(2);
    expect(right?.start).toBe(4);
    expect(right?.duration).toBe(2);
    expect(right?.inPoint).toBe(2);
    expect(right?.id).not.toBe(left?.id);
  });

  it('refuses degenerate splits', () => {
    expect(splitClipAt(clip(), 2)).toBeNull();
    expect(splitClipAt(clip(), 5.95)).toBeNull();
  });

  it('trims the end without moving the start', () => {
    const { clip: trimmed, changed } = trimClipEdge(clip(), 'end', -1);
    expect(changed).toBe(true);
    expect(trimmed.duration).toBe(3);
    expect(trimmed.start).toBe(2);
  });

  it('never trims below the minimum duration', () => {
    const { clip: trimmed } = trimClipEdge(clip(), 'end', -99);
    expect(trimmed.duration).toBe(MIN_CLIP_SECONDS);
  });

  it('trims the start and keeps the source inPoint consistent', () => {
    const { clip: trimmed } = trimClipEdge(clip({ start: 3, inPoint: 1 }), 'start', 1);
    expect(trimmed.start).toBe(4);
    expect(trimmed.duration).toBe(3);
    expect(trimmed.inPoint).toBe(2);
  });

  it('reports no change for a zero delta', () => {
    expect(trimClipEdge(clip(), 'end', 0).changed).toBe(false);
    expect(trimClipEdge(clip(), 'start', 0).changed).toBe(false);
  });
});

describe('display helpers', () => {
  it('formats timecode with frames', () => {
    expect(timecode(0)).toBe('00:00:00:00');
    expect(timecode(61.5, 30)).toBe('00:01:01:15');
    expect(timecode(-5)).toBe('00:00:00:00');
  });

  it('produces ruler ticks that respect the minimum spacing', () => {
    const ticks = rulerTicks(10, 40, 70);
    expect(ticks.length).toBeGreaterThan(1);
    const gap = (ticks[1]?.time ?? 0) - (ticks[0]?.time ?? 0);
    expect(gap * 40).toBeGreaterThanOrEqual(70);
    expect(ticks[0]?.major).toBe(true);
  });

  it('fits zoom into the viewport and clamps', () => {
    expect(fitZoom(60, 600)).toBeGreaterThan(8);
    expect(fitZoom(0, 600)).toBe(8);
    expect(fitZoom(1, 100000)).toBeLessThanOrEqual(400);
  });

  it('computes clip end', () => {
    expect(clipEnd(clip())).toBe(6);
  });
});
