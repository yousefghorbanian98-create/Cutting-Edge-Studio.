import { useEffect } from 'react';
import { MenuBar } from './components/layout/MenuBar';
import { Panel } from './components/layout/Panel';
import { StatusBar } from './components/layout/StatusBar';
import { api } from './lib/api';
import { translate } from './lib/i18n';
import { useAppStore } from './store/useAppStore';

/** Application shell: menu bar, three-column workspace, timeline, status bar. */
export default function App() {
  const language = useAppStore((state) => state.language);
  const setBackend = useAppStore((state) => state.setBackend);

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then((health) => {
        if (!cancelled) setBackend('online', health.version);
      })
      .catch(() => {
        if (!cancelled) setBackend('offline');
      });
    return () => {
      cancelled = true;
    };
  }, [setBackend]);

  return (
    <div className="flex h-full flex-col bg-bg-primary text-text-primary">
      <MenuBar />
      <main className="flex min-h-0 flex-1 gap-2 p-2">
        <Panel title={translate(language, 'panel.media')} as="aside" className="w-[280px] shrink-0">
          <p className="text-xs text-text-secondary">{translate(language, 'media.empty')}</p>
        </Panel>
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <Panel title={translate(language, 'panel.preview')} className="flex-1">
            <div className="flex h-full items-center justify-center rounded-md bg-black/40 text-xs text-text-secondary">
              {translate(language, 'preview.empty')}
            </div>
          </Panel>
          <Panel title={translate(language, 'panel.timeline')} className="h-[280px] shrink-0">
            <p className="text-xs text-text-secondary">{translate(language, 'timeline.empty')}</p>
          </Panel>
        </div>
        <Panel title={translate(language, 'panel.properties')} as="aside" className="w-[300px] shrink-0">
          <p className="text-xs text-text-secondary">{translate(language, 'wizard.title')}</p>
        </Panel>
      </main>
      <StatusBar />
    </div>
  );
}
