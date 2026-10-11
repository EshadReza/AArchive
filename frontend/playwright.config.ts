import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results/foundation',
  fullyParallel: true,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:5178', browserName: 'chromium', screenshot: 'only-on-failure' },
  projects: [
    { name: 'desktop', testIgnore: '**/production.spec.ts', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', testIgnore: '**/production.spec.ts', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
    { name: 'production', testMatch: '**/production.spec.ts', use: { baseURL: 'http://127.0.0.1:5179' } },
  ],
  webServer: [
    { command: 'npm run dev -- --port 5178 --strictPort', url: 'http://127.0.0.1:5178', reuseExistingServer: false },
    { command: 'npm run preview -- --port 5179 --strictPort', url: 'http://127.0.0.1:5179', reuseExistingServer: false },
  ],
});
