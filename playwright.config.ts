import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';

const isCI = process.env.CI === 'true';
const headless = process.env.FORCE_HEADLESS === 'true' || (isCI && process.env.HEADLESS !== 'false');

export default defineConfig({
  testDir: './tests',
  timeout: 15 * 60 * 1000, // 15 分钟全局超时
  expect: { timeout: 30 * 1000 },
  fullyParallel: false,
  retries: isCI ? 1 : 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results.json' }],
    ['list'],
    ['junit', { outputFile: 'test-results.xml' }],
  ],
  use: {
    baseURL: 'https://review-key.newidea.pro',
    headless: headless,
    viewport: { width: 1920, height: 1080 },
    actionTimeout: 15 * 1000,
    navigationTimeout: 30 * 1000,
    screenshot: 'on',
    video: 'on',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // 配置下载目录，不弹出保存对话框
        acceptDownloads: true,
        launchOptions: {
          args: [
            '--disable-blink-features=AutomationControlled',
          ],
        },
      },
    },
  ],
});
