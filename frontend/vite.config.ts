import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    proxy: {
      '^/api(?:/|$)': {
        target: process.env.AARCHIVE_API_TARGET ?? 'http://127.0.0.1:8000',
        // Preserve browser Host/Origin and cookies so Django checks the same origin.
        changeOrigin: false,
        xfwd: false,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    clearMocks: true,
    restoreMocks: true,
  },
});
