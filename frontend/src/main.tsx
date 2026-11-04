import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

// Bundled OFL-1.1 fonts: no CDN, no runtime font download (LOCK-05).
import '@fontsource/vazirmatn/400.css';
import '@fontsource/vazirmatn/600.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/jetbrains-mono/400.css';

import App from './App';
import './index.css';
import { useAppStore } from './store/useAppStore';

// Apply persisted/initial theme + language before first paint.
const { theme, language, setTheme, setLanguage } = useAppStore.getState();
setTheme(theme);
setLanguage(language);

const container = document.getElementById('root');
if (!container) {
  throw new Error('root container missing in index.html');
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
