import { describe, expect, it } from 'vitest';
import { MAX_FILE_BYTES, extensionOf, formatBytes, kindOf, validateFiles } from './files';

const file = (name: string, size = 1024) => ({ name, size, path: `/media/${name}` });

describe('file validation', () => {
  it('extracts lowercase extensions', () => {
    expect(extensionOf('Clip.MP4')).toBe('mp4');
    expect(extensionOf('no-extension')).toBe('');
  });

  it('classifies video and audio, rejects the rest', () => {
    expect(kindOf('a.mov')).toBe('video');
    expect(kindOf('b.WAV')).toBe('audio');
    expect(kindOf('c.txt')).toBeNull();
  });

  it('accepts valid files and reports every rejection reason', () => {
    const result = validateFiles([
      file('good.mp4'),
      file('notes.pdf'),
      file('empty.mp4', 0),
      file('huge.mkv', MAX_FILE_BYTES + 1),
    ]);
    expect(result.accepted.map((item) => item.name)).toEqual(['good.mp4']);
    expect(result.rejected).toEqual([
      { name: 'notes.pdf', reason: 'extension' },
      { name: 'empty.mp4', reason: 'empty' },
      { name: 'huge.mkv', reason: 'too-large' },
    ]);
  });

  it('formats bytes deterministically', () => {
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(1024 * 1024 * 1536)).toBe('1.5 GB');
  });
});
