# CI baselines

Each file holds the current number of outstanding issues for one check. CI fails if
the count rises above the recorded number, and prints a notice when it falls so the
baseline can be lowered.

This is deliberate. The repository carries existing lint debt, and a check that fails
from its first run gets switched off rather than fixed. A ratchet stops new problems
arriving while the backlog is paid down at whatever pace suits.

Lower a baseline whenever CI says you can. Do not raise one to make a build pass.

| File | Check | Goal |
|------|-------|------|
| `flake8-baseline.txt` | `flake8 app tests scripts` | 0, then drop the ratchet and fail on any issue |
| `complexity-baseline.txt` | `ruff check --select C901` at `max-complexity = 5` | 0, then drop the ratchet |

Most of the current count is long lines, unused imports, and trailing whitespace.
`black` and `isort` are already dev dependencies and would clear most of it, but that
was left alone deliberately: `autoflake` removing an "unused" import would break the
model modules whose imports exist to register ORM metadata.

## Complexity

`max-complexity = 5` in `pyproject.toml` is stricter than the usual 10. That is the
intent: at 5 the check flags branching early enough to be a prompt for a second look,
not a demand for a refactor. Most of the 86 functions currently over the line are fine
as they are. The ones worth attention sit far above it: `create_events_bulk` at 32 and
`create_lifespan` at 26.

The count is specific to ruff. The `mccabe` bundled with flake8 reports the same
functions with somewhat higher numbers and misses nested functions such as the
`asgi_app` closures in `app/middleware/`, so it reports a different total against the
same threshold. Do not compare the two baselines, and do not regenerate this one with
flake8.

Alembic migrations are excluded (`extend-exclude` in `pyproject.toml`). They are
written once and never refactored, so a complexity number for them is noise.
