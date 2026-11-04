import { z } from 'zod';

const id = z.string().min(1).max(200);
const time = z.number().finite().min(0).max(864000);
const track = z
  .object({ id, name: id, kind: z.enum(['video', 'audio']), locked: z.boolean(), muted: z.boolean() })
  .strict();
const clip = z
  .object({
    id,
    mediaId: z.string().min(1).max(4096),
    name: z.string().min(1).max(1024),
    trackId: id,
    start: time,
    duration: z.number().finite().positive().max(864000),
    inPoint: time,
    kind: z.enum(['video', 'audio']),
  })
  .strict();
const bookmark = z.object({ id, time, label: z.string().max(200), color: z.string().max(100) }).strict();
export const snapshotSchema = z
  .object({
    version: z.literal(1),
    timeline: z
      .object({
        tracks: z.array(track).min(1).max(100),
        clips: z.array(clip).max(10000),
        bookmarks: z.array(bookmark).max(10000),
        duration: z.number().finite().min(1).max(864000),
        playhead: time,
        pxPerSecond: z.number().finite().min(8).max(400),
        snapEnabled: z.boolean(),
      })
      .strict(),
    mediaOrder: z.array(id).max(10000),
    selectedAssetId: id.nullable(),
    referenceAssetId: id.nullable(),
    wizardStep: z.number().int().min(0).max(4),
    post: z
      .object({
        enabled: z
          .object({
            replay: z.boolean(),
            comparison: z.boolean(),
            captions: z.boolean(),
            broll: z.boolean(),
            loudness: z.boolean(),
            thumbnail: z.boolean(),
            templates: z.boolean(),
          })
          .strict(),
        presetId: z.enum(['tiktok', 'shorts', 'youtube', 'instagram_feed', 'archive']),
        layout: z.enum(['side_by_side', 'stacked', 'picture_in_picture']),
        captionFormat: z.enum(['ass', 'srt']),
        quality: z.enum(['preview', 'final']),
      })
      .strict(),
    appearance: z.object({ language: z.enum(['fa', 'en']), theme: z.enum(['pro', 'glass', 'minimal']) }).strict(),
  })
  .strict();
export const workspaceSchema = z
  .object({
    name: z.string().min(1).max(200),
    revision: z.string().regex(/^[a-f0-9]{64}$/),
    snapshot: snapshotSchema.nullable(),
  })
  .strict();
export type WorkspaceSnapshot = z.infer<typeof snapshotSchema>;
export type WorkspaceResponse = z.infer<typeof workspaceSchema>;
