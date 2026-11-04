/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary: 'var(--bg-tertiary)',
        },
        surface: {
          DEFAULT: 'var(--surface-default)',
          hover: 'var(--surface-hover)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
        },
        accent: {
          DEFAULT: 'var(--accent-primary)',
          hover: 'var(--accent-hover)',
        },
        state: {
          success: 'var(--success)',
          warning: 'var(--warning)',
          error: 'var(--error)',
        },
      },
      borderRadius: {
        panel: 'var(--radius-panel)',
        control: 'var(--radius-control)',
      },
      fontFamily: {
        sans: ['Vazirmatn', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
