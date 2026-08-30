# Web client

React client for the Timeline API. Vite, React 19, TanStack Router and Query,
Tailwind, shadcn/ui.

It is a single-page app with no server rendering. Almost every route sits behind a
login, where rendering on the server buys nothing, and dropping it means the API
serves the built bundle and a deployment is one process rather than two. The public
landing and verification pages are rendered by the API from `apps/api/app/pages`,
so they stay crawlable and need no bundle to read.

## Running

From the repository root, `make dev` starts this and the API together. To run only
this side:

```bash
pnpm install
pnpm dev            # http://localhost:3000
```

The client calls `/api/...` relatively. In development vite proxies that to the API;
in production the API serves this bundle from the same origin. The request path is
identical either way, so nothing can work in one and fail in the other. Point the
proxy elsewhere with `VITE_PROXY_TARGET`.

Configuration comes from the single `.env` at the repository root. Only
`VITE_`-prefixed values reach the browser.

## Checks

```bash
pnpm verify         # what CI runs: build, typecheck, lint, style, unit tests
pnpm test           # unit tests only
pnpm test:e2e       # Playwright; needs the app and API running
```

`verify` ratchets against the counts in `ci/`. It fails when a count rises and tells
you when one has fallen so the baseline can be lowered. See `ci/README.md`.

## API types

`src/lib/timeline-api.ts` is generated from the API's OpenAPI schema and should never
be edited by hand.

```bash
# with the API running
pnpm run generate:api
git diff --exit-code src/lib/timeline-api.ts
```

A non-empty diff means the committed types had drifted from the API. While the two
lived in separate repositories that drift was invisible until something failed at
runtime; in one repository it is a check.

## Adding components

```bash
pnpm dlx shadcn@latest add button
```
