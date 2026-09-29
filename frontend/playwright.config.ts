import { defineConfig } from '@playwright/test'

// Прогон против запущенного стека: BASE_URL (по умолчанию vite dev с прокси на backend).
export default defineConfig({
  testDir: 'e2e',
  timeout: 90_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:5173',
    launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {},
  },
})
