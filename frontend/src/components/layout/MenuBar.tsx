import { useAppStore } from '../../store/useAppStore';
import { translate } from '../../lib/i18n';
import type { Theme } from '../../store/useAppStore';

const MENU_KEYS = ['menu.file', 'menu.edit', 'menu.view', 'menu.ai', 'menu.help'] as const;
const THEMES: readonly Theme[] = ['pro', 'glass', 'minimal'];

/** Top menu bar (32px per layout spec). Theme switch is a real control, not a mock. */
export function MenuBar() {
  const language = useAppStore((state) => state.language);
  const theme = useAppStore((state) => state.theme);
  const setTheme = useAppStore((state) => state.setTheme);
  const setLanguage = useAppStore((state) => state.setLanguage);

  return (
    <nav
      aria-label="main menu"
      className="flex h-8 shrink-0 items-center gap-1 border-b border-white/5 bg-bg-secondary px-2 text-xs"
    >
      <span className="me-3 font-semibold text-accent">{translate(language, 'app.title')}</span>
      {MENU_KEYS.map((key) => (
        <button
          key={key}
          type="button"
          className="rounded px-2 py-1 text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary"
        >
          {translate(language, key)}
        </button>
      ))}
      <div className="ms-auto flex items-center gap-2">
        <select
          aria-label="theme"
          value={theme}
          onChange={(event) => setTheme(event.target.value as Theme)}
          className="rounded bg-bg-tertiary px-2 py-1 text-text-secondary"
        >
          {THEMES.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setLanguage(language === 'fa' ? 'en' : 'fa')}
          className="rounded bg-bg-tertiary px-2 py-1 text-text-secondary hover:text-text-primary"
        >
          {language === 'fa' ? 'EN' : 'فا'}
        </button>
      </div>
    </nav>
  );
}
