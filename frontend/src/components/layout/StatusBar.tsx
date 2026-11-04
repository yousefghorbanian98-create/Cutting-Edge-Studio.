import { useAppStore } from '../../store/useAppStore';
import { translate } from '../../lib/i18n';

/** Bottom status bar: backend reachability, offline badge, version. */
export function StatusBar() {
  const language = useAppStore((state) => state.language);
  const backend = useAppStore((state) => state.backend);
  const version = useAppStore((state) => state.backendVersion);

  const label =
    backend === 'online'
      ? translate(language, 'status.backend.online')
      : backend === 'offline'
        ? translate(language, 'status.backend.offline')
        : '…';

  const dot = backend === 'online' ? 'bg-state-success' : backend === 'offline' ? 'bg-state-warning' : 'bg-text-secondary';

  return (
    <footer className="flex h-7 shrink-0 items-center gap-3 border-t border-white/5 bg-bg-secondary px-3 text-[11px] text-text-secondary">
      <span className="flex items-center gap-1.5" role="status" aria-live="polite" aria-label="backend status">
        <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />
        {label}
      </span>
      <span className="rounded bg-bg-tertiary px-1.5 py-0.5">{translate(language, 'status.offline.mode')}</span>
      {version ? (
        <span className="ms-auto">
          {translate(language, 'status.version')} {version}
        </span>
      ) : null}
    </footer>
  );
}
