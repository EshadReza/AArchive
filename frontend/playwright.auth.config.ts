import { defineConfig } from '@playwright/test';

if (!process.env.AUTH_E2E_BASE_URL) throw new Error('Run scripts/check_auth_browser.py to provision the isolated auth test server.');

export default defineConfig({
  testDir: './e2e-auth', workers: 1, reporter: 'list',
  outputDir: './test-results/auth',
  use: { baseURL: process.env.AUTH_E2E_BASE_URL, browserName: 'chromium', screenshot: 'only-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
});
