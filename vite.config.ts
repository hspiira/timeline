/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import { devtools } from '@tanstack/devtools-vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import viteReact from '@vitejs/plugin-react'
import viteTsConfigPaths from 'vite-tsconfig-paths'
import tailwindcss from '@tailwindcss/vite'
import { visualizer } from 'rollup-plugin-visualizer'

/**
 * Third-party packages that every route already pulls into the entry chunk.
 * Grouping them does not change what is downloaded on a first visit; it keeps
 * their hashes stable across deploys that only touch app code.
 *
 * The TanStack entry names its packages rather than matching the whole scope:
 * moving @tanstack/react-start and its ssr-query plumbing out of the chunks
 * Start builds them into fails the client render with a rollup export error.
 */
const EAGER_VENDORS: [string, RegExp][] = [
  ['vendor-react', /^(react|react-dom|scheduler|use-sync-external-store)$/],
  [
    'vendor-tanstack',
    /^@tanstack\/(query-core|react-query|table-core|react-table|virtual-core|react-virtual|router-core|react-router|history|store|react-store)$/,
  ],
  ['vendor-ui', /^(radix-ui$|@radix-ui\/|@base-ui\/)/],
]

/** Package name from a module id; reads the last node_modules segment so pnpm paths resolve. */
function packageOf(id: string): string | undefined {
  const marker = 'node_modules/'
  const at = id.lastIndexOf(marker)
  if (at === -1) return undefined
  const [first, second] = id.slice(at + marker.length).split('/')
  if (!first) return undefined
  return first.startsWith('@') && second ? `${first}/${second}` : first
}

function eagerVendorChunk(id: string): string | undefined {
  const pkg = packageOf(id)
  if (!pkg) return undefined
  return EAGER_VENDORS.find(([, match]) => match.test(pkg))?.[0]
}

/**
 * CSP for the dev server only.
 *
 * In production the API serves these files and its SecurityHeadersMiddleware sets
 * the real policy as a response header, which is the stronger form: a meta tag
 * cannot carry frame-ancestors. Dev needs its own because vite serves the files
 * here, and without it the two environments disagree about what is allowed —
 * which is where this class of bug hides.
 *
 * Vite injects its client over a websocket, hence ws:. There is no
 * script-src 'unsafe-inline': nothing inlines a bootstrap script any more.
 */
const DEV_CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' data: https://fonts.gstatic.com",
  "img-src 'self' data:",
  "connect-src 'self' ws: wss: http://localhost:8000",
  "frame-ancestors 'none'",
].join('; ')

const config = defineConfig({
  server: {
    headers: {
      'Content-Security-Policy': DEV_CSP,
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
    },
  },
  plugins: [
    devtools(),
    // this is the plugin that enables path aliases
    viteTsConfigPaths({
      projects: ['./tsconfig.json'],
    }),
    tailwindcss(),
    // Router only. Code splitting stays off until the app is stable: the stale
    // ?tsr-split=component chunk was the reload failure this branch exists to test.
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
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
  environments: {
    client: {
      build: {
        rollupOptions: {
          output: {
            manualChunks: (id) => eagerVendorChunk(id),
          },
        },
      },
    },
  },
  test: {
    // Vitest's defaults match the Playwright specs in e2e/ and die on their import.
    exclude: ['**/node_modules/**', '**/dist/**', '**/.output/**', 'e2e/**'],
    passWithNoTests: true,
  },
})

export default config
