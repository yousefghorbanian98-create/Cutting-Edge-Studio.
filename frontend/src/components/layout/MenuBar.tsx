import { useAppStore, type Theme } from '../../store/useAppStore';
import { translate } from '../../lib/i18n';
import { Select, type SelectOption, Tooltip } from '../ui';

const MENU_KEYS = ['menu.file', 'menu.edit', 'menu.view', 'menu.ai', 'menu.help'] as const;
const THEMES: readonly Theme[] = ['pro', 'glass', 'minimal'];

/** Top menu bar (32px per layout spec). Theme/language are the only live controls in P1. */
export function MenuBar() {
  const language = useAppStore((state) => state.language);
  const theme = useAppStore((state) => state.theme);
  const setTheme = useAppStore((state) => state.setTheme);
  const setLanguage = useAppStore((state) => state.setLanguage);

  const themeOptions: SelectOption[] = THEMES.map((item) => ({ value: item, label: item }));

  return (
    <nav
      aria-label="main menu"
      className="flex h-8 shrink-0 items-center gap-1 border-b border-white/5 bg-[var(--bg-secondary)] px-2 text-xs"
    >
      <span className="me-3 font-semibold text-[var(--accent-primary)]">{translate(language, 'app.title')}</span>
      {MENU_KEYS.map((key) => (
        <button
          key={key}
          type="button"
          className="rounded px-2 py-1 text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
        >
          {translate(language, key)}
        </button>
      ))}
      <div className="ms-auto flex items-center gap-2">
        <Select
          label={translate(language, 'menu.theme')}
          value={theme}
          onValueChange={(value) => setTheme(value as Theme)}
          options={themeOptions}
        />
        <Tooltip content={translate(language, 'menu.language')}>
          <button
            type="button"
            onClick={() => setLanguage(language === 'fa' ? 'en' : 'fa')}
            aria-label={translate(language, 'menu.language')}
            className="rounded bg-[var(--bg-tertiary)] px-2 py-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            {language === 'fa' ? 'EN' : 'فا'}
          </button>
        </Tooltip>
      </div>
    </nav>
  );
}
