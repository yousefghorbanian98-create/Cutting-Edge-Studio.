import { useEffect, useState } from 'react';
import { MenuBar } from './components/layout/MenuBar';
import { Panel } from './components/layout/Panel';
import { StatusBar } from './components/layout/StatusBar';
import { CommandPalette, SkipLink, Toaster, type CommandAction } from './components/ui';
import { MediaPanel } from './features/media/MediaPanel';
import { StyleMatchWizard } from './features/stylematch/StyleMatchWizard';
import { api } from './lib/api';
import { translate } from './lib/i18n';
import { useAppStore } from './store/useAppStore';

/** Application shell: menu bar, three-column workspace, timeline, status bar (spec §10). */
export default function App() {
  const language = useAppStore((state) => state.language);
  const theme = useAppStore((state) => state.theme);
  const setTheme = useAppStore((state) => state.setTheme);
  const setLanguage = useAppStore((state) => state.setLanguage);
  const setBackend = useAppStore((state) => state.setBackend);
  const [paletteOpen, setPaletteOpen] = useState(false);

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

  const actions: CommandAction[] = [
    {
      id: 'theme',
      label: translate(language, 'palette.action.theme'),
      hint: theme,
      onRun: () => setTheme(theme === 'pro' ? 'glass' : theme === 'glass' ? 'minimal' : 'pro'),
    },
    {
      id: 'language',
      label: translate(language, 'palette.action.language'),
      hint: language,
      onRun: () => setLanguage(language === 'fa' ? 'en' : 'fa'),
    },
    {
      id: 'wizard',
      label: translate(language, 'palette.action.wizard'),
      onRun: () => document.getElementById('style-match-wizard')?.scrollIntoView({ block: 'start' }),
    },
  ];

  return (
    <div className="flex h-full flex-col bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <SkipLink label={translate(language, 'a11y.skip')} targetId="main-content" />
      <MenuBar />
      <main id="main-content" className="flex min-h-0 flex-1 gap-2 p-2">
        <Panel title={translate(language, 'panel.media')} as="aside" className="w-[280px] shrink-0">
          <MediaPanel />
        </Panel>
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <Panel title={translate(language, 'panel.preview')} className="flex-1">
            <div className="flex h-full items-center justify-center rounded-[var(--radius-control)] bg-black/40 text-xs text-[var(--text-secondary)]">
              {translate(language, 'preview.empty')}
            </div>
          </Panel>
          <Panel title={translate(language, 'panel.timeline')} className="h-[280px] shrink-0">
            <p className="text-xs text-[var(--text-secondary)]">{translate(language, 'timeline.empty')}</p>
          </Panel>
        </div>
        <Panel title={translate(language, 'panel.properties')} as="aside" className="w-[320px] shrink-0">
          <div id="style-match-wizard" className="h-full">
            <StyleMatchWizard />
          </div>
        </Panel>
      </main>
      <StatusBar />
      <CommandPalette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        actions={actions}
        label={translate(language, 'palette.label')}
        placeholder={translate(language, 'palette.placeholder')}
      />
      <Toaster />
    </div>
  );
}
