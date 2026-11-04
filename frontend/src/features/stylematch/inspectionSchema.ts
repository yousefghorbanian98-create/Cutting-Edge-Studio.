import { z } from 'zod';

export type InspectionOperation = 'decode' | 'rhythm' | 'scenes';
const identity = {
  asset_id:z.string(), role:z.string(), name:z.string(), sha256:z.string().regex(/^[a-f0-9]{64}$/),
  size_bytes:z.number().nonnegative(), mtime_ns:z.string(), duration:z.number().finite().positive(),
  has_audio:z.boolean(),
};
const estimate = z.object({
  time_origin:z.literal('extracted-pcm-start').default('extracted-pcm-start'),
  sha256:z.string().regex(/^[a-f0-9]{64}$/), samples_analyzed:z.number().int().min(22050).max(13230000),
  duration_seconds:z.number().finite().min(1).max(600), tempo_bpm:z.number().finite().positive().nullable(),
  beat_times_seconds:z.array(z.number().finite().nonnegative()).max(30000),
  library_version:z.literal('0.11.0'), method:z.literal('librosa.beat.beat_track'),scope:z.literal('audio-rhythm-only'),
}).refine(e => (e.tempo_bpm === null) === (e.beat_times_seconds.length === 0)
  && Math.abs(e.samples_analyzed / 22050 - e.duration_seconds) <= 1 / 22050
  && e.beat_times_seconds.every((t,i,a) => t <= e.duration_seconds && (i === 0 || t > a[i-1]!)),
{message:'Invalid PCM rhythm measurement'});
const rhythmFile = z.object({...identity,status:z.enum(['estimated','no-beats','no-audio']),estimate:estimate.nullable()})
  .refine(f => f.status === 'no-audio' ? !f.has_audio && f.estimate === null : f.has_audio && f.estimate !== null
    && (f.status === 'estimated') === (f.estimate.beat_times_seconds.length > 0),{message:'Inconsistent rhythm state'});
const sceneEstimate = z.object({
  method:z.literal('ffmpeg.scdet'),time_origin:z.literal('first-decoded-video-frame'),threshold_percent:z.literal(10),scaled_width:z.literal(320),
  frames_analyzed:z.number().int().min(1).max(36000),first_frame_pts_seconds:z.number().finite(),decoded_span_seconds:z.number().finite().min(0).max(600.25),
  candidates:z.array(z.object({frame_index:z.number().int().min(1),time_seconds:z.number().finite().positive(),score_percent:z.number().finite().min(10).max(100)})).max(36000),
}).refine(e => e.candidates.every((c,i,a) => c.frame_index < e.frames_analyzed && c.time_seconds <= e.decoded_span_seconds+1e-5
  && (i===0 || c.time_seconds>a[i-1]!.time_seconds && c.frame_index>a[i-1]!.frame_index)),{message:'Invalid observed cut candidates'});
const sceneFile = z.object({...identity,has_video:z.boolean(),status:z.enum(['candidates','no-candidates','no-video']),estimate:sceneEstimate.nullable()})
  .refine(f => f.status==='no-video' ? !f.has_video && f.estimate===null : f.has_video && f.estimate!==null
    && (f.status==='candidates')===(f.estimate.candidates.length>0),{message:'Inconsistent video candidate state'});
const scopeForOperation={decode:'media-inspection-only',rhythm:'audio-rhythm-only',scenes:'shot-candidates-only'};
const report = z.discriminatedUnion('scope',[
  z.object({version:z.literal(1),method:z.literal('ffprobe-lavfi+scdet'),scope:z.literal('shot-candidates-only'),
    unavailable:z.array(z.string()),files:z.array(sceneFile).min(1).max(101)}),
  z.object({
    version:z.literal(1), method:z.literal('ffprobe+ffmpeg-full-decode'), scope:z.literal('media-inspection-only'),
    unavailable:z.array(z.string()), files:z.array(z.object({...identity,
      width:z.number(),height:z.number(),fps:z.number().finite(),video_codec:z.string().nullable(),
      audio_codec:z.string().nullable(),decoded_frames:z.number().int().nonnegative(),decoded_seconds:z.number().finite().nonnegative(),
    })).max(101),
  }),
  z.object({version:z.literal(1),method:z.literal('ffmpeg-pcm+librosa.beat.beat_track'),scope:z.literal('audio-rhythm-only'),
    unavailable:z.array(z.string()),files:z.array(rhythmFile).min(1).max(101)}),
]);
export const inspectionSchema = z.object({
  operation:z.enum(['decode','rhythm','scenes']).default('decode'),
  id:z.string().min(1), project_id:z.string().min(1), reference_asset_id:z.string(), source_asset_ids:z.array(z.string()).max(100),
  state:z.enum(['queued','running','done','failed','cancelled','interrupted']), percent:z.number().finite().min(0).max(100),
  message:z.string(), error:z.string().nullable(), stale:z.boolean(), report:report.nullable(),
}).refine(job => job.state !== 'done' || (job.report !== null && job.percent === 100), {message:'Completed inspection has no committed measured report'})
  .refine(job => !job.report || job.report.scope === scopeForOperation[job.operation],{message:'Report scope disagrees with operation'});
export const inspectionCapabilitiesSchema = z.object({
  cache_recovery:z.object({removed:z.number().int().nonnegative(),retained:z.number().int().nonnegative(),scanned:z.number().int().nonnegative(),limited:z.boolean(),message:z.string()}).optional(),
  operation:z.enum(['decode','rhythm','scenes']).default('decode'),
  inspection:z.object({available:z.boolean(),reason:z.string().nullable()}),
  model_analysis:z.object({available:z.literal(false),reason:z.string(),unavailable:z.array(z.string()),models_directory:z.string()}),
});
export type InspectionResponse = z.infer<typeof inspectionSchema>;
export type InspectionCapabilities = z.infer<typeof inspectionCapabilitiesSchema>;
