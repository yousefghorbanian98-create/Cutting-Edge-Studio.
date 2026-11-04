/** File validation helpers for the import pipeline (mirrors backend allow-lists). */

export const VIDEO_EXTENSIONS = ['mp4', 'mov', 'm4v', 'mkv', 'webm', 'avi'] as const;
export const AUDIO_EXTENSIONS = ['wav', 'mp3', 'flac', 'm4a', 'aac', 'ogg'] as const;

export type MediaKind = 'video' | 'audio';

export interface CandidateFile {
  name: string;
  size: number;
  path: string;
}

export interface RejectedFile {
  name: string;
  reason: 'extension' | 'empty' | 'too-large';
}

export interface ValidationResult {
  accepted: CandidateFile[];
  rejected: RejectedFile[];
}

/** Hard ceiling per file: 20 GB keeps the proxy pipeline sane on 16 GB RAM. */
export const MAX_FILE_BYTES = 20 * 1024 * 1024 * 1024;

export function extensionOf(name: string): string {
  const index = name.lastIndexOf('.');
  return index === -1 ? '' : name.slice(index + 1).toLowerCase();
}

export function kindOf(name: string): MediaKind | null {
  const extension = extensionOf(name);
  if ((VIDEO_EXTENSIONS as readonly string[]).includes(extension)) return 'video';
  if ((AUDIO_EXTENSIONS as readonly string[]).includes(extension)) return 'audio';
  return null;
}

export function validateFiles(files: readonly CandidateFile[]): ValidationResult {
  const accepted: CandidateFile[] = [];
  const rejected: RejectedFile[] = [];
  for (const file of files) {
    if (kindOf(file.name) === null) {
      rejected.push({ name: file.name, reason: 'extension' });
    } else if (file.size === 0) {
      rejected.push({ name: file.name, reason: 'empty' });
    } else if (file.size > MAX_FILE_BYTES) {
      rejected.push({ name: file.name, reason: 'too-large' });
    } else {
      accepted.push(file);
    }
  }
  return { accepted, rejected };
}

/** 1.4e9 -> "1.4 GB" (locale-independent for stable tests). */
export function formatBytes(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const rounded = value >= 10 || unit === 0 ? Math.round(value) : Math.round(value * 10) / 10;
  return `${rounded} ${units[unit]}`;
}
