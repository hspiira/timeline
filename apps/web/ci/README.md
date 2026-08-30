# CI baselines

Each file holds the current number of outstanding findings for one check. `pnpm verify`
runs the checks and CI runs nothing but that same command, so local and CI answers
match. It fails if a count rises above the recorded number, and prints a notice when
one falls so the baseline can be lowered.

This is deliberate. The repository carries existing debt, and a check that fails from
its first run gets switched off rather than fixed. A ratchet stops new problems
arriving while the backlog is paid down at whatever pace suits.

Lower a baseline whenever CI says you can. Do not raise one to make a build pass.

| File | Check | Goal |
|------|-------|------|
| `tsc-baseline.txt` | `tsc --noEmit` | 0, then drop the ratchet in `scripts/verify.mjs` and fail on any error |
| `biome-lint-baseline.txt` | `biome lint src` | 0, then fail on any finding |
| `biome-style-baseline.txt` | `biome check --linter-enabled=false src` | 0, once the source is formatted |

Build and tests are absolute: no baseline, they simply have to pass. End-to-end tests
need the app and the API running, so `pnpm verify` reports them as not run unless
`VERIFY_E2E=1` is set.

## Why lint and style are counted separately

They mean different things. Lint findings are potential defects. Style findings are
only the formatter disagreeing with hand-written code. Counted as one number, 399 real
findings sat behind 379 cosmetic ones and no one could tell which had moved.

## About the style number

The source has never been run through a formatter, so it has no single style to match.
`biome.json` now records the dominant one (two-space indent, single quotes, no
semicolons), which matters mostly for what happens next: under the previous config,
`biome check --write` would have converted all 246 files to tabs and double quotes.

`pnpm exec biome check --write src` still fixes the bulk in one command, and is still
worth doing as a commit of its own rather than mixed into other work.

## About the type errors

Two clusters. Router search-parameter objects that omit now-required keys, and
workflow action arrays typed as `{type: string}` where the API expects a discriminated
union. Both are real and neither is cosmetic; they were simply never surfaced, because
`pnpm build` runs `vite build` with no type checking at all.
