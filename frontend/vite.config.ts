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
  build: {
    outDir: 'dist',
    sourcemap: false,
    target: 'chrome110',
    // The timeline editor and react-virtualized are only needed on the workspace
    // screen; splitting them keeps the initial shell small.
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          timeline: ['@xzdarcy/react-timeline-editor', '@xzdarcy/timeline-engine'],
          radix: [
            '@radix-ui/react-dialog',
            '@radix-ui/react-select',
            '@radix-ui/react-tabs',
            '@radix-ui/react-slider',
            '@radix-ui/react-switch',
            '@radix-ui/react-tooltip',
            '@radix-ui/react-progress',
          ],
          motion: ['framer-motion'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
