import { useEffect, useRef, useState } from 'react';
import { Button, ProgressBar } from '../../components/ui';
import { api, ApiError, type RenderResponse, type RenderQuality } from '../../lib/api';
import { translate } from '../../lib/i18n';
import { useAppStore } from '../../store/useAppStore';

interface Props {
  projectId: string | null;
  edl: unknown | null;
  blocked?: boolean;
}
const active = (j: RenderResponse | null) => j?.state === 'queued' || j?.state === 'running';

export function RenderPanel({ projectId, edl, blocked }: Props) {
  const language = useAppStore((s) => s.language);
  const t = (k: string) => translate(language, `render.${k}`);
  const [cap, setCap] = useState<{ available: boolean; reason: string | null; encoder: string | null } | null>(null);
  const [job, setJob] = useState<RenderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [quality, setQuality] = useState<RenderQuality>('preview');
  const [refresh, setRefresh] = useState(0);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  useEffect(() => {
    if (!projectId) return;
    const c = new AbortController();
    setLoading(true);
    setError(null);
    Promise.all([
      api.renderCapabilities(projectId, c.signal),
      api.latestRender(projectId, c.signal).catch((e) => {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }),
    ])
      .then(([caps, latest]) => {
        if (c.signal.aborted) return;
        setCap({ available: caps.render.available, reason: caps.render.reason, encoder: caps.encoder });
        if (latest) setJob(latest);
      })
      .catch((e) => {
        if (c.signal.aborted) return;
        setError(String(e));
      })
      .finally(() => {
        if (!c.signal.aborted) setLoading(false);
      });
    return () => c.abort();
  }, [projectId, refresh]);
  useEffect(() => {
    if (!projectId || !job || !active(job) || error || loading) return;
    const c = new AbortController();
    const tm = setTimeout(() => {
      void api
        .getRender(projectId, job.id, c.signal)
        .then((r) => {
          if (!c.signal.aborted) setJob(r);
        })
        .catch((e) => {
          if (!c.signal.aborted) setError(String(e));
        });
    }, 700);
    return () => {
      clearTimeout(tm);
      c.abort();
    };
  }, [projectId, job, error, loading]);
  const valid = !!projectId && !!edl && !blocked;
  const start = async () => {
    if (!projectId || !edl) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.startRender(projectId, edl, quality);
      if (alive.current) setJob(r);
    } catch (e) {
      if (alive.current) setError(String(e));
    } finally {
      if (alive.current) setLoading(false);
    }
  };
  const cancel = async () => {
    if (!projectId || !job) return;
    setLoading(true);
    try {
      const r = await api.cancelRender(projectId, job.id);
      if (alive.current) setJob(r);
    } catch (e) {
      if (alive.current) setError(String(e));
    } finally {
      if (alive.current) setLoading(false);
    }
  };
  return (
    <section aria-label={t('title')} className="mt-3 space-y-2" data-testid="render-panel">
      <p className="font-semibold">{t('title')}</p>
      <p className="text-[10px]">{t('scope')}</p>
      {cap && (
        <p role="status" className="text-[10px] break-all">
          {t('capabilities')}: {cap.available ? `✓ ${cap.encoder}` : cap.reason}
        </p>
      )}
      {!valid && <p role="status">{t('needsEdl')}</p>}
      <div className="flex flex-wrap gap-1">
        <Button size="sm" disabled={!valid || !cap?.available || loading || active(job)} onClick={() => void start()}>
          {quality === 'preview' ? t('start.preview') : t('start.final')}
        </Button>
        <select
          value={quality}
          onChange={(e) => setQuality(e.target.value as RenderQuality)}
          className="text-[11px] bg-[var(--bg-secondary)] border border-white/10 rounded px-1"
        >
          <option value="preview">preview 480p</option>
          <option value="final">final 1080p</option>
        </select>
        <Button
          size="sm"
          variant="ghost"
          disabled={!projectId || loading}
          onClick={() => {
            setError(null);
            setRefresh((v) => v + 1);
          }}
        >
          {translate(language, 'inspection.refresh')}
        </Button>
        {active(job) && (
          <Button size="sm" variant="danger" disabled={loading} onClick={() => void cancel()}>
            {translate(language, 'inspection.cancel')}
          </Button>
        )}
      </div>
      {loading && <p role="status">{translate(language, 'inspection.loading')}</p>}
      {error && <p role="alert">{error}</p>}
      {cap?.reason && !cap.available && <p role="alert">{cap.reason}</p>}
      {job && (
        <div>
          <p role="status" data-testid="render-state">
            {t(`state.${job.state}`)}
          </p>
          <ProgressBar value={job.percent} label={t('progress')} />
          <p className="text-[10px]">{job.message}</p>
          {job.error && <p role="alert">{job.error}</p>}
          {job.state === 'done' && job.report && (
            <div className="text-[10px] space-y-1">
              <p>
                {t('output')}: {job.report.output_path} · {job.report.width}×{job.report.height}@{job.report.fps} ·{' '}
                {job.report.encoder} · {(job.report.size_bytes / 1024).toFixed(0)}KB · {job.report.duration.toFixed(2)}s
              </p>
              <video
                src={`/api/v1/assets/${encodeURIComponent(job.report.output_path)}/content`}
                controls
                crossOrigin="anonymous"
                className="w-full max-h-40"
              />
              <a href={`/api/v1/assets/${encodeURIComponent(job.report.output_path)}/content`} download className="underline">
                {t('download')}
              </a>
            </div>
          )}
        </div>
      )}
      {!loading && !job && <p role="status">{t('none')}</p>}
    </section>
  );
}
