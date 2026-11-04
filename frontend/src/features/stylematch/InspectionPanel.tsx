import { useEffect, useRef, useState } from 'react';
import { Button, ProgressBar } from '../../components/ui';
import { api, ApiError } from '../../lib/api';
import { translate } from '../../lib/i18n';
import { useAppStore } from '../../store/useAppStore';
import { inspectionCapabilitiesSchema, inspectionSchema, type InspectionCapabilities, type InspectionResponse, type InspectionOperation } from './inspectionSchema';

interface Props {
  projectId: string | null;
  referenceId: string | null;
  sourceIds: string[];
  blocked: boolean;
  operation?: InspectionOperation;
}
const RHYTHM_KEYS=new Set(['title','scope','start','progress','results','none','state.queued','state.running','state.done','state.failed','state.cancelled','state.interrupted']);
const active = (job: InspectionResponse | null) => job?.state === 'queued' || job?.state === 'running';

/** Decode verification is intentionally NOT labelled model analysis/DNA completion. */
export function InspectionPanel({projectId,referenceId,sourceIds,blocked,operation='decode'}: Props) {
  const language=useAppStore(state=>state.language);
  const t=(key:string)=>translate(language,`${operation==='rhythm' && RHYTHM_KEYS.has(key)?'rhythm':'inspection'}.${key}`);
  const [capabilities,setCapabilities]=useState<InspectionCapabilities|null>(null);
  const [job,setJob]=useState<InspectionResponse|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [loading,setLoading]=useState(false);
  const [refresh,setRefresh]=useState(0);
  const alive=useRef(true);
  const context=useRef({projectId,operation});
  context.current={projectId,operation};
  const current=()=>alive.current && context.current.projectId===projectId && context.current.operation===operation;
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);

  useEffect(()=>{
    if (!projectId) return;
    const controller=new AbortController();
    setLoading(true);
    setError(null);
    void Promise.all([
      api.inspectionCapabilities(projectId,controller.signal,operation),
      api.latestInspection(projectId,controller.signal,operation).catch(error=>{
        if(error instanceof ApiError && error.status===404){
          console.warn('inspection.no-saved-job',projectId);
          return null;
        }
        throw error;
      }),
    ]).then(([caps,latest])=>{
      if(controller.signal.aborted)return;
      const parsedCaps=inspectionCapabilitiesSchema.parse(caps);
      if(parsedCaps.operation!==operation)throw new Error("Capabilities operation changed");
      setCapabilities(parsedCaps);
      const parsed=latest?inspectionSchema.parse(latest):null;
      if(parsed && (parsed.project_id!==projectId || parsed.operation!==operation))throw new Error('Inspection belongs to another project or operation');
      setJob(parsed);
    }).catch(error=>{
      if(controller.signal.aborted)return;
      console.error('inspection.restore.failed',error);
      setError(String(error));
    }).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();
  },[projectId,refresh,operation]);

  useEffect(()=>{
    if(!projectId || !job || !active(job) || error || loading)return;
    const controller=new AbortController();
    const timer=setTimeout(()=>{
      void api.getInspection(projectId,job.id,controller.signal,operation).then(response=>{
        if(controller.signal.aborted)return;
        const parsed=inspectionSchema.parse(response);
        if(parsed.project_id!==projectId || parsed.id!==job.id || parsed.operation!==operation)throw new Error('Inspection identity changed');
        setJob(parsed);
      }).catch(error=>{
        if(controller.signal.aborted)return;
        console.error('inspection.poll.failed',error);
        setError(String(error));
      });
    },500);
    return()=>{clearTimeout(timer);controller.abort();};
  },[projectId,job,error,loading,operation]);

  const start=async()=>{
    if(!projectId || !referenceId)return;
    setLoading(true);setError(null);
    try{
      const response=inspectionSchema.parse(await api.startInspection(projectId,referenceId,sourceIds,operation));
      if(response.project_id!==projectId || response.operation!==operation)throw new Error('Inspection belongs to another project or operation');
      if(current())setJob(response);
    }catch(error){
      console.error('inspection.start.failed',error);
      if(current())setError(String(error));
    }finally{if(current())setLoading(false);}
  };
  const cancel=async()=>{
    if(!projectId || !job)return;
    setLoading(true);setError(null);
    try{
      const response=inspectionSchema.parse(await api.cancelInspection(projectId,job.id,operation));
      if(response.project_id!==projectId || response.id!==job.id || response.operation!==operation)throw new Error('Inspection identity changed');
      if(current())setJob(response);
    }catch(error){
      console.error('inspection.cancel.failed',error);
      if(current())setError(String(error));
    }finally{if(current())setLoading(false);}
  };
  const stale=!!job && (job.stale || job.reference_asset_id!==referenceId || JSON.stringify([...job.source_asset_ids].sort())!==JSON.stringify([...sourceIds].sort()));
  const valid=!!projectId && !!referenceId && sourceIds.length>0 && sourceIds.length<=100 && !blocked;
  return <section aria-label={t('title')} className="mt-2 space-y-2" data-testid="inspection-panel">
    <p className="font-semibold">{t('title')}</p>
    <p className="text-[10px]">{t('scope')}</p>
    {!valid ? <p role="status">{t('needsInputs')}</p>:null}
    <div className="flex flex-wrap gap-1">
      <Button size="sm" disabled={!valid || !capabilities?.inspection.available || loading || active(job)} onClick={()=>void start()}>{t('start')}</Button>
      <Button size="sm" variant="ghost" disabled={!projectId || loading} onClick={()=>{setError(null);setRefresh(value=>value+1);}}>{t('refresh')}</Button>
      {active(job)?<Button size="sm" variant="danger" disabled={loading} onClick={()=>void cancel()}>{t('cancel')}</Button>:null}
    </div>
    {loading?<p role="status">{t('loading')}</p>:null}
    {error?<p role="alert">{error}</p>:null}
    {capabilities?.inspection.reason?<p role="alert">{capabilities.inspection.reason}</p>:null}
    {job?<div>
      <p role="status" data-testid="inspection-state">{t(`state.${job.state}`)}</p>
      <ProgressBar value={job.percent} label={t('progress')} />
      <p className="text-[10px]">{job.message}</p>
      {job.error?<p role="alert">{job.error}</p>:null}
      {stale?<p role="alert">{t('stale')}</p>:null}
      {job.state==='done' && job.report?<ul aria-label={t('results')} className="max-h-32 overflow-auto text-[10px]">
        {job.report.scope==='media-inspection-only' ? job.report.files.map(file=><li key={file.asset_id}>{file.name} · {file.duration.toFixed(2)}s · {file.width}×{file.height} · {file.decoded_frames} {t('frames')} · {file.has_audio?t('audio'):t('noAudio')}</li>) : job.report.files.map(file=><li key={file.asset_id}>{file.name} · {translate(language,`rhythm.result.${file.status}`)}{file.estimate && file.estimate.tempo_bpm!==null ? ` · ${file.estimate.tempo_bpm.toFixed(2)} BPM · ${file.estimate.beat_times_seconds.length} ${translate(language,'rhythm.beats')}` : ''}</li>)}
      </ul>:null}
    </div>:!loading?<p role="status">{t('none')}</p>:null}
    <p role="status" className="text-[var(--warning)]">{t('modelsBlocked')}</p>
    {capabilities?<p className="break-all text-[10px]">{t('modelsPath')}: {capabilities.model_analysis.models_directory}</p>:null}
  </section>;
}
