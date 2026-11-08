import { useEffect } from 'react';
import { Button, Select } from '../../components/ui';
import { translate } from '../../lib/i18n';
import { useAppStore } from '../../store/useAppStore';
import { useMediaStore } from '../../store/mediaStore';
import { useWorkspaceStore, watchWorkspaceChanges } from '../../store/workspaceStore';

/** Local SQLite is authoritative; browser storage holds only the last project ID. */
export function WorkspaceBar() {
  const language = useAppStore((state) => state.language);
  const media = useMediaStore();
  const workspace = useWorkspaceStore();
  const t = (key: string) => translate(language, `workspace.${key}`);
  const busy = workspace.navigating || workspace.status === 'loading' || media.importing;
  const run = (action: () => Promise<void>) => {
    void action().catch((error) => {
      console.error('workspace.control.failed', error);
      useWorkspaceStore.setState({ error: String(error), status: 'error' });
    });
  };
  useEffect(() => {
    const unwatch = watchWorkspaceChanges();
    void useWorkspaceStore.getState().initialize();
    const beforeUnload = (event: BeforeUnloadEvent) => {
      const current = useWorkspaceStore.getState();
      if (current.dirty || current.status === 'saving' || useMediaStore.getState().importing) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', beforeUnload);
    return () => {
      unwatch();
      window.removeEventListener('beforeunload', beforeUnload);
    };
  }, []);
  useEffect(() => {
    if (
      !workspace.initialized ||
      !workspace.dirty ||
      workspace.status !== 'idle' ||
      media.importing ||
      workspace.conflict
    )
      return;
    const timer = setTimeout(() => {
      void useWorkspaceStore
        .getState()
        .save()
        .catch((error) => console.error('workspace.autosave.failed', error));
    }, 800);
    return () => clearTimeout(timer);
  }, [
    workspace.initialized,
    workspace.dirty,
    workspace.generation,
    workspace.status,
    workspace.conflict,
    media.importing,
  ]);
  const projects = [...workspace.projects];
  if (media.projectId && !projects.some((p) => p.id === media.projectId))
    projects.unshift({ id: media.projectId, name: media.projectName });
  return (
    <section
      aria-label={t('title')}
      className="flex shrink-0 flex-col gap-1 border-b border-white/10 px-3 py-1 text-xs"
    >
      <div className="flex flex-wrap items-center gap-2">
        <input
          aria-label={t('name')}
          value={media.projectName}
          maxLength={200}
          disabled={busy || !media.projectId}
          onChange={(event) => useMediaStore.setState({ projectName: event.target.value })}
          className="rounded bg-[var(--bg-secondary)] px-2 py-1"
        />
        <Button size="sm" variant="secondary" disabled={busy} onClick={() => run(workspace.newProject)}>
          {t('new')}
        </Button>
        <Button size="sm" variant="secondary" disabled={busy} onClick={() => run(workspace.refresh)}>
          {t('list')}
        </Button>
        {projects.length ? (
          <Select
            label={t('open')}
            value={media.projectId ?? ''}
            disabled={busy}
            options={projects.map((p) => ({ value: p.id, label: `${p.name} · ${p.id.slice(0, 6)}` }))}
            onValueChange={(id) => run(() => workspace.open(id))}
          />
        ) : null}
        <Button size="sm" disabled={busy || !media.projectId || workspace.conflict} onClick={() => run(workspace.save)}>
          {t('save')}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={busy || !media.projectId}
          onClick={() => {
            if (!workspace.dirty || window.confirm(t('discard'))) run(() => workspace.open(media.projectId!, true));
          }}
        >
          {t('reload')}
        </Button>
        <span role="status" aria-label="workspace save status" data-testid="workspace-status">
          {t(
            workspace.status === 'loading' || !workspace.initialized
              ? 'loading'
              : workspace.status === 'saving'
                ? 'saving'
                : workspace.status === 'error'
                  ? 'failed'
                  : workspace.dirty
                    ? 'unsaved'
                    : media.projectId
                      ? 'saved'
                      : 'empty',
          )}
        </span>
        {media.clips.some((c) => c.available === false) ? <span role="alert">{t('missing')}</span> : null}
      </div>
      {workspace.error ? (
        <p role="alert" className="text-[var(--error)]">
          {t('failed')}: {workspace.error}
        </p>
      ) : null}
      {workspace.warning ? (
        <p role="alert" className="text-[var(--warning)]">
          {workspace.warning}
        </p>
      ) : null}
    </section>
  );
}
