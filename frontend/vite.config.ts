import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': process.env.API_URL ?? 'http://localhost:8000' } },
  test: { include: ['src/**/*.test.ts'] },
})
