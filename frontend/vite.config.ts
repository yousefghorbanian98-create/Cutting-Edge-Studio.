import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Loopback backend sidecar. The browser never talks to it directly: Vite proxies
// /api so the UI works under any preview host without CORS surprises.
const BACKEND = process.env.CUTTING_EDGE_BACKEND ?? 'http://127.0.0.1:8756';

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    host: '0.0.0.0',
    port: 1420,
    strictPort: true,
    // Preview/mirror hosts are dynamic; the app is read-only and local.
    allowedHosts: true,
    proxy: { '/api': { target: BACKEND, changeOrigin: false } },
  },
  preview: {
    host: '0.0.0.0',
    port: 1420,
    strictPort: true,
    allowedHosts: true,
    proxy: { '/api': { target: BACKEND, changeOrigin: false } },
  },
  build: { outDir: 'dist', sourcemap: false, target: 'chrome110' },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
