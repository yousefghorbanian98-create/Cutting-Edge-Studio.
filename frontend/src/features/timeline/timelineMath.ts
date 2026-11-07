/** Pure timeline math: no React, no store. Everything here is unit-tested. */

export interface TimelineClip {
  id: string;
  mediaId: string;
  name: string;
  trackId: string;
  /** Position on the timeline, seconds. */
  start: number;
  /** Visible length on the timeline, seconds. */
  duration: number;
  /** Offset inside the source media, seconds. */
  inPoint: number;
  kind: 'video' | 'audio';
}

export interface Track {
  id: string;
  name: string;
  kind: 'video' | 'audio';
  locked: boolean;
  muted: boolean;
}

export const MIN_CLIP_SECONDS = 0.1;
export const SNAP_PIXELS = 8;
export const ZOOM_RANGE = { min: 8, max: 400 } as const;

export function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.min(Math.max(value, min), max);
}

export function secondsToPixels(seconds: number, pxPerSecond: number): number {
  return seconds * pxPerSecond;
}

export function pixelsToSeconds(pixels: number, pxPerSecond: number): number {
  if (pxPerSecond <= 0) return 0;
  return pixels / pxPerSecond;
}

/** Quantize to the nearest multiple of `grid` (no-op for grid <= 0). */
export function quantize(seconds: number, grid: number): number {
  if (grid <= 0) return seconds;
  return Math.round(seconds / grid) * grid;
}

export function clipEnd(clip: TimelineClip): number {
  return clip.start + clip.duration;
}

export function overlaps(a: TimelineClip, b: TimelineClip): boolean {
  if (a.trackId !== b.trackId) return false;
  return a.start < clipEnd(b) && b.start < clipEnd(a);
}

export interface SnapContext {
  pxPerSecond: number;
  grid: number;
  targets: readonly number[];
  enabled: boolean;
}

/**
 * Snap a candidate time to the closest target (clip edges, bookmarks, zero, grid).
 * Returns the snapped value and whether a snap happened.
 */
export function snapTime(candidate: number, context: SnapContext): { value: number; snapped: boolean } {
  if (!context.enabled) return { value: candidate, snapped: false };
  const threshold = pixelsToSeconds(SNAP_PIXELS, context.pxPerSecond);
  let best = candidate;
  let bestDistance = threshold;
  for (const target of context.targets) {
    const distance = Math.abs(target - candidate);
    if (distance <= bestDistance) {
      bestDistance = distance;
      best = target;
    }
  }
  if (best !== candidate) return { value: best, snapped: true };
  // No edge/bookmark is close enough: always fall back to the grid.
  const quantized = quantize(candidate, context.grid);
  return quantized === candidate ? { value: candidate, snapped: false } : { value: quantized, snapped: true };
}

/** First free position at or after `desired` on a track (never overlaps existing clips). */
export function findFreeSlot(
  clips: readonly TimelineClip[],
  trackId: string,
  desired: number,
  duration: number,
  ignoreId?: string,
): number {
  const occupied = clips
    .filter((clip) => clip.trackId === trackId && clip.id !== ignoreId)
    .sort((a, b) => a.start - b.start);
  let start = Math.max(0, desired);
  let moved = true;
  while (moved) {
    moved = false;
    for (const clip of occupied) {
      const candidate = { ...clip, id: 'probe', trackId, start, duration };
      if (overlaps(candidate, clip)) {
        start = clipEnd(clip);
        moved = true;
      }
    }
  }
  return start;
}

/** Split a clip at an absolute timeline position. Returns null when the split is a no-op. */
export function splitClipAt(clip: TimelineClip, atSeconds: number): [TimelineClip, TimelineClip] | null {
  const offset = atSeconds - clip.start;
  if (offset < MIN_CLIP_SECONDS || clip.duration - offset < MIN_CLIP_SECONDS) return null;
  const left: TimelineClip = { ...clip, duration: offset };
  const right: TimelineClip = {
    ...clip,
    id: `${clip.id}-b`,
    start: atSeconds,
    duration: clip.duration - offset,
    inPoint: clip.inPoint + offset,
  };
  return [left, right];
}

export interface TrimResult {
  clip: TimelineClip;
  changed: boolean;
}

/** Trim one edge, refusing to cross the minimum duration or the zero boundary. */
export function trimClipEdge(clip: TimelineClip, edge: 'start' | 'end', deltaSeconds: number): TrimResult {
  if (edge === 'end') {
    const next = Math.max(MIN_CLIP_SECONDS, clip.duration + deltaSeconds);
    if (Math.abs(next - clip.duration) < 1e-6) return { clip, changed: false };
    return { clip: { ...clip, duration: next }, changed: true };
  }
  const maxDelta = clip.duration - MIN_CLIP_SECONDS;
  const delta = clamp(deltaSeconds, -clip.start, maxDelta);
  if (Math.abs(delta) < 1e-6) return { clip, changed: false };
  return {
    clip: {
      ...clip,
      start: clip.start + delta,
      duration: clip.duration - delta,
      inPoint: Math.max(0, clip.inPoint + delta),
    },
    changed: true,
  };
}

/** "01:23:45:12" — hours:minutes:seconds:frames. */
export function timecode(seconds: number, fps = 30): string {
  const safe = Math.max(0, seconds);
  const totalFrames = Math.round(safe * fps);
  const frames = totalFrames % fps;
  const totalSeconds = Math.floor(totalFrames / fps);
  const secs = totalSeconds % 60;
  const minutes = Math.floor(totalSeconds / 60) % 60;
  const hours = Math.floor(totalSeconds / 3600);
  const pad = (value: number, size = 2): string => String(value).padStart(size, '0');
  return `${pad(hours)}:${pad(minutes)}:${pad(secs)}:${pad(frames)}`;
}

export interface RulerTick {
  time: number;
  major: boolean;
}

/** Choose a tick step that keeps labels at least `minSpacingPx` apart. */
export function rulerTicks(duration: number, pxPerSecond: number, minSpacingPx = 60): RulerTick[] {
  const steps = [0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600];
  const step = steps.find((candidate) => candidate * pxPerSecond >= minSpacingPx) ?? steps[steps.length - 1] ?? 600;
  const ticks: RulerTick[] = [];
  for (let time = 0; time <= duration + 1e-9; time += step) {
    ticks.push({ time: Number(time.toFixed(4)), major: Math.abs(time % (step * 5)) < 1e-9 });
  }
  return ticks;
}

/** Zoom that fits the whole sequence into the viewport (clamped to ZOOM_RANGE). */
export function fitZoom(duration: number, viewportWidthPx: number): number {
  if (duration <= 0 || viewportWidthPx <= 0) return ZOOM_RANGE.min;
  return clamp((viewportWidthPx * 0.94) / duration, ZOOM_RANGE.min, ZOOM_RANGE.max);
}
