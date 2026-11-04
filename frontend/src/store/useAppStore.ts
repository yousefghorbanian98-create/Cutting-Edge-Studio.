import { create } from 'zustand';
import { directionOf, type Language } from '../lib/i18n';

export type Theme = 'pro' | 'glass' | 'minimal';
export type BackendStatus = 'checking' | 'online' | 'offline';

interface AppState {
  language: Language;
  theme: Theme;
  backend: BackendStatus;
  backendVersion: string | null;
  setLanguage: (language: Language) => void;
  setTheme: (theme: Theme) => void;
  setBackend: (status: BackendStatus, version?: string | null) => void;
}

/** Apply language + direction to the document root so RTL is global. */
function applyLanguage(language: Language): void {
  document.documentElement.lang = language;
  document.documentElement.dir = directionOf(language);
}

/** Apply the theme by switching a single data attribute (CSS variables do the rest). */
function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export const useAppStore = create<AppState>((set) => ({
  language: 'fa',
  theme: 'pro',
  backend: 'checking',
  backendVersion: null,
  setLanguage: (language) => {
    applyLanguage(language);
    set({ language });
  },
  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },
  setBackend: (backend, backendVersion = null) => set({ backend, backendVersion }),
}));
