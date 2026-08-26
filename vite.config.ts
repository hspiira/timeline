/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import { devtools } from '@tanstack/devtools-vite'
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'
import viteTsConfigPaths from 'vite-tsconfig-paths'
import tailwindcss from '@tailwindcss/vite'
import { nitro } from 'nitro/vite'
import { visualizer } from 'rollup-plugin-visualizer'

const config = defineConfig({
  plugins: [
    devtools(),
    nitro(),
    // this is the plugin that enables path aliases
    viteTsConfigPaths({
      projects: ['./tsconfig.json'],
    }),
    tailwindcss(),
    tanstackStart({
      router: {
        // Enable route-level code splitting. Start's types omit this; runtime may still apply it.
        autoCodeSplitting: true,
      } as { entry?: string; basepath?: string },
    }),
    viteReact(),
    ...(process.env.ANALYZE === '1'
      ? [
          visualizer({
            open: false,
            gzipSize: true,
            brotliSize: true,
            filename: 'dist/stats.html',
          }),
        ]
      : []),
  ],
  test: {
    // e2e/ holds Playwright specs. Vitest's default patterns match them, and it
    // then fails on the @playwright/test import rather than reporting no tests.
    exclude: ['**/node_modules/**', '**/dist/**', '**/.output/**', 'e2e/**'],
    passWithNoTests: true,
  },
})

export default config
