# CI ratchets

Each file under an application's `ci/` directory holds the current number of
outstanding findings for one check. `pnpm verify` and the CI workflow run the same
checks and compare against those numbers. A build fails when a count **rises**, and
prints a notice when one **falls** so the baseline can be lowered.

This is deliberate. Both applications carry existing debt, and a check that fails
from its first run gets switched off rather than fixed. A ratchet stops new
problems arriving while the backlog is paid down at whatever pace suits.

**Lower a baseline whenever CI says you can. Never raise one to make a build pass.**

## The baselines

| File | Check | Goal |
|---|---|---|
| `apps/api/ci/flake8-baseline.txt` | `flake8 app` | 0, then fail on any finding |
| `apps/api/ci/complexity-baseline.txt` | `ruff check app` (C901 only) | 0, then drop the ratchet |
| `apps/web/ci/tsc-baseline.txt` | `tsc --noEmit` | 0, then fail on any error |
| `apps/web/ci/biome-lint-baseline.txt` | `biome lint src` | 0, then fail on any finding |
| `apps/web/ci/biome-style-baseline.txt` | `biome check --linter-enabled=false src` | 0, once the source is formatted |

Build and tests carry no baseline on either side: they simply have to pass.

## Why the API runs two linters

`ruff` is configured for `C901` only. The repository's lint debt is already
ratcheted through `flake8`, and enabling ruff's default rules would report the same
findings again under different codes, making both baselines meaningless. Collapsing
onto ruff alone is worth doing once `flake8-baseline.txt` reaches zero; until then
the split keeps each number honest.
