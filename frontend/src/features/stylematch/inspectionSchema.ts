import { z } from 'zod';

export const inspectionSchema = z.object({
  id:z.string().min(1), project_id:z.string().min(1), reference_asset_id:z.string(), source_asset_ids:z.array(z.string()),
  state:z.enum(['queued','running','done','failed','cancelled','interrupted']), percent:z.number().finite().min(0).max(100),
  message:z.string(), error:z.string().nullable(), stale:z.boolean(),
  report:z.object({
    version:z.literal(1), method:z.literal('ffprobe+ffmpeg-full-decode'), scope:z.literal('media-inspection-only'),
    unavailable:z.array(z.string()), files:z.array(z.object({
      asset_id:z.string(), role:z.string(), name:z.string(), sha256:z.string().regex(/^[a-f0-9]{64}$/),
      size_bytes:z.number().nonnegative(), mtime_ns:z.string(), duration:z.number().finite().nonnegative(),
      width:z.number(), height:z.number(), fps:z.number().finite(), video_codec:z.string().nullable(),
      audio_codec:z.string().nullable(), has_audio:z.boolean(), decoded_frames:z.number().int().nonnegative(),
      decoded_seconds:z.number().finite().nonnegative(),
    })),
  }).nullable(),
}).refine(job => job.state !== 'done' || (job.report !== null && job.percent === 100), {message:'Completed inspection has no committed measured report'});
export const inspectionCapabilitiesSchema = z.object({
  inspection:z.object({available:z.boolean(),reason:z.string().nullable()}),
  model_analysis:z.object({available:z.literal(false),reason:z.string(),unavailable:z.array(z.string()),models_directory:z.string()}),
});
export type InspectionResponse = z.infer<typeof inspectionSchema>;
export type InspectionCapabilities = z.infer<typeof inspectionCapabilitiesSchema>;
