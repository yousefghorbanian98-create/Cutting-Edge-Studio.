import { beforeEach, describe, expect, it } from 'vitest';
import { selectReferences, useMediaStore } from './mediaStore';

const clip = (name: string, path = `/media/${name}`) => ({ name, size: 2048, path });

beforeEach(() => {
  useMediaStore.getState().clear();
});

describe('media store', () => {
  it('imports valid files with a stable id and kind', () => {
    const outcome = useMediaStore.getState().addFiles([clip('a.mp4'), clip('b.wav')]);
    expect(outcome.added).toHaveLength(2);
    expect(outcome.rejected).toEqual([]);
    const [first, second] = useMediaStore.getState().clips;
    expect(first?.kind).toBe('video');
    expect(second?.kind).toBe('audio');
    expect(first?.id).toMatch(/^clip-/);
  });

  it('rejects duplicates by path instead of silently dropping them', () => {
    useMediaStore.getState().addFiles([clip('a.mp4', '/media/x.mp4')]);
    const outcome = useMediaStore.getState().addFiles([clip('a-copy.mp4', '/media/x.mp4')]);
    expect(outcome.added).toEqual([]);
    expect(outcome.rejected).toEqual([{ name: 'a-copy.mp4', reason: 'duplicate' }]);
  });

  it('marks references and filters them', () => {
    useMediaStore.getState().addFiles([clip('ref.mp4', '/media/ref.mp4')], 'reference');
    useMediaStore.getState().addFiles([clip('src.mp4', '/media/src.mp4')]);
    expect(selectReferences(useMediaStore.getState().clips).map((item) => item.name)).toEqual(['ref.mp4']);
  });

  it('removes and reorders clips', () => {
    useMediaStore.getState().addFiles([clip('a.mp4'), clip('b.mp4'), clip('c.mp4')]);
    const [a, b, c] = useMediaStore.getState().clips;
    useMediaStore.getState().reorder(String(c?.id), String(a?.id));
    expect(useMediaStore.getState().clips.map((item) => item.name)).toEqual(['c.mp4', 'a.mp4', 'b.mp4']);
    useMediaStore.getState().removeClip(String(b?.id));
    expect(useMediaStore.getState().clips.map((item) => item.name)).toEqual(['c.mp4', 'a.mp4']);
  });

  it('ignores an unknown reorder target', () => {
    useMediaStore.getState().addFiles([clip('a.mp4')]);
    const before = useMediaStore.getState().clips;
    useMediaStore.getState().reorder('nope', 'also-nope');
    expect(useMediaStore.getState().clips).toBe(before);
  });
});
