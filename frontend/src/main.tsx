import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
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
