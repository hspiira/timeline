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

Most of the current count is long lines, unused imports, and trailing whitespace.
`black` and `isort` are already dev dependencies and would clear most of it, but that
was left alone deliberately: `autoflake` removing an "unused" import would break the
model modules whose imports exist to register ORM metadata.
