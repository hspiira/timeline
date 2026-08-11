# CI baselines

Each file holds the current number of outstanding findings for one check. CI fails if
the count rises above the recorded number, and prints a notice when it falls so the
baseline can be lowered.

This is deliberate. The repository carries existing debt, and a check that fails from
its first run gets switched off rather than fixed. A ratchet stops new problems
arriving while the backlog is paid down at whatever pace suits.

Lower a baseline whenever CI says you can. Do not raise one to make a build pass.

| File | Check | Goal |
|------|-------|------|
| `tsc-baseline.txt` | `tsc --noEmit` | 0, then fold `tsc --noEmit` into the build script and drop the ratchet |
| `biome-baseline.txt` | `biome check src` (errors + warnings) | 0, then fail on any finding |

## About the biome number

Almost all of it is formatting: the project has biome configured but the source was
never formatted with it, so nearly every file differs on quote style and indentation.

`pnpm exec biome check --write src` fixes the bulk in one command. It was left alone
on purpose — it rewrites around 245 files, which would bury unrelated changes in
review and conflict with anything in flight. Worth doing as a single commit of its
own, on a quiet day, then lowering this baseline sharply.

## About the type errors

Two clusters. Router search-parameter objects that omit now-required keys, and
workflow action arrays typed as `{type: string}` where the API expects a discriminated
union. Both are real and neither is cosmetic; they were simply never surfaced, because
`pnpm build` runs `vite build` with no type checking at all.
