import { beforeEach, describe, expect, it } from 'vitest';
import { snapTargets, useTimelineStore } from './timelineStore';

const add = (name = 'a.mp4', at = 0, kind: 'video' | 'audio' = 'video') =>
  useTimelineStore.getState().addClip({ mediaId: `/m/${name}`, name, kind, at });

beforeEach(() => {
  useTimelineStore.getState().reset();
});

describe('timeline store — placement', () => {
  it('adds a 5s clip on the first unlocked track of the same kind', () => {
    const clip = add();
    expect(clip?.trackId).toBe('v1');
    expect(clip?.duration).toBe(5);
    expect(useTimelineStore.getState().selectedIds).toEqual([clip?.id]);
  });

  it('routes audio to the audio track', () => {
    expect(add('music.mp3', 0, 'audio')?.trackId).toBe('a1');
  });

  it('never overlaps: a second clip at the same position is pushed right', () => {
    add('a.mp4', 0);
    const second = add('b.mp4', 0);
    expect(second?.start).toBe(5);
  });

  it('extends the sequence duration as clips are added', () => {
    add('a.mp4', 0);
    expect(useTimelineStore.getState().duration).toBeGreaterThanOrEqual(30);
  });
});

describe('timeline store — editing', () => {
  it('moves a clip and refuses locked tracks', () => {
    const clip = add('a.mp4', 0);
    expect(useTimelineStore.getState().moveClip(String(clip?.id), 12)).toBe(true);
    expect(useTimelineStore.getState().clips[0]?.start).toBe(12);
    expect(useTimelineStore.getState().moveClip(String(clip?.id), 12)).toBe(false);
  });

  it('keeps clips from colliding when moved onto each other', () => {
    const first = add('a.mp4', 0);
    const second = add('b.mp4', 20);
    useTimelineStore.getState().moveClip(String(second?.id), 1);
    const starts = useTimelineStore.getState().clips.map((clip) => clip.start).sort((a, b) => a - b);
    expect(starts).toEqual([0, 5]);
    expect(first?.start).toBe(0);
  });

  it('trims and splits at the playhead', () => {
    const clip = add('a.mp4', 0);
    expect(useTimelineStore.getState().trimClip(String(clip?.id), 'end', -2)).toBe(true);
    expect(useTimelineStore.getState().clips[0]?.duration).toBe(3);

    useTimelineStore.getState().setPlayhead(1);
    expect(useTimelineStore.getState().splitAtPlayhead()).toBe(1);
    expect(useTimelineStore.getState().clips).toHaveLength(2);
  });

  it('splits nothing when the playhead is not over a clip', () => {
    add('a.mp4', 10);
    useTimelineStore.getState().setPlayhead(0);
    expect(useTimelineStore.getState().splitAtPlayhead()).toBe(0);
  });

  it('removes only the selected clips', () => {
    const first = add('a.mp4', 0);
    add('b.mp4', 10);
    useTimelineStore.getState().selectClip(String(first?.id));
    expect(useTimelineStore.getState().removeSelected()).toBe(1);
    expect(useTimelineStore.getState().clips).toHaveLength(1);
    expect(useTimelineStore.getState().removeSelected()).toBe(0);
  });

  it('supports multi-selection with additive clicks', () => {
    const first = add('a.mp4', 0);
    const second = add('b.mp4', 10);
    useTimelineStore.getState().selectClip(String(first?.id));
    useTimelineStore.getState().selectClip(String(second?.id), true);
    expect(useTimelineStore.getState().selectedIds).toHaveLength(2);
    useTimelineStore.getState().selectClip(String(second?.id), true);
    expect(useTimelineStore.getState().selectedIds).toEqual([first?.id]);
  });
});

describe('timeline store — history', () => {
  it('undoes and redoes structural edits', () => {
    add('a.mp4', 0);
    add('b.mp4', 10);
    expect(useTimelineStore.getState().clips).toHaveLength(2);
    expect(useTimelineStore.getState().undo()).toBe(true);
    expect(useTimelineStore.getState().clips).toHaveLength(1);
    expect(useTimelineStore.getState().redo()).toBe(true);
    expect(useTimelineStore.getState().clips).toHaveLength(2);
  });

  it('returns false with an empty history', () => {
    expect(useTimelineStore.getState().undo()).toBe(false);
    expect(useTimelineStore.getState().redo()).toBe(false);
  });

  it('clears the redo stack after a new edit', () => {
    add('a.mp4', 0);
    useTimelineStore.getState().undo();
    add('c.mp4', 30);
    expect(useTimelineStore.getState().redo()).toBe(false);
  });
});

describe('timeline store — bookmarks and view state', () => {
  it('adds a bookmark at the playhead and refuses duplicates', () => {
    useTimelineStore.getState().setPlayhead(4);
    const bookmark = useTimelineStore.getState().addBookmark('peak');
    expect(bookmark?.time).toBe(4);
    expect(useTimelineStore.getState().addBookmark()).toBeNull();
    expect(useTimelineStore.getState().bookmarks).toHaveLength(1);
  });

  it('clamps the playhead into the sequence', () => {
    useTimelineStore.getState().setPlayhead(-5);
    expect(useTimelineStore.getState().playhead).toBe(0);
    useTimelineStore.getState().setPlayhead(9999);
    expect(useTimelineStore.getState().playhead).toBe(useTimelineStore.getState().duration);
  });

  it('zooms within the allowed range', () => {
    for (let index = 0; index < 40; index += 1) useTimelineStore.getState().zoomIn();
    expect(useTimelineStore.getState().pxPerSecond).toBeLessThanOrEqual(400);
    for (let index = 0; index < 60; index += 1) useTimelineStore.getState().zoomOut();
    expect(useTimelineStore.getState().pxPerSecond).toBeGreaterThanOrEqual(8);
  });

  it('toggles snapping and playback', () => {
    useTimelineStore.getState().toggleSnap();
    expect(useTimelineStore.getState().snapEnabled).toBe(false);
    useTimelineStore.getState().togglePlaying();
    expect(useTimelineStore.getState().playing).toBe(true);
  });

  it('collects snap targets from clip edges and bookmarks', () => {
    const first = add('a.mp4', 0);
    useTimelineStore.getState().setPlayhead(9);
    useTimelineStore.getState().addBookmark();
    const targets = snapTargets(
      useTimelineStore.getState().clips,
      useTimelineStore.getState().bookmarks,
      String(first?.id),
    );
    expect(targets).toEqual([0, 9]);
  });
});
