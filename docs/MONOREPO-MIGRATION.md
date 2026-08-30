# Monorepo migration runbook

**Status:** preparation done, move not started.
**Goal:** one repository holding the API, the web client, the packs and the docs.

## Preconditions — do not start before all four

1. **`identity-and-email-signin` merged to `main`.** 31 commits as of 2026-08-30.
2. **`timeline-ui`'s `email-signin` merged to its `main`.** 50 commits.
3. **The other open branches resolved deliberately**, not discovered mid-move:
   `5-external-chain-anchoring-architecture-brief`, `7-concurrent-write-race-condition-on-event-chains`,
   and the dependabot branches in both repositories. Land or close each one.
4. **Both working trees clean**, both `main` branches green.

Moving files while branches are outstanding forces every one of them to be rebased
across a path change. That is the whole reason to wait.

## Target layout

```
timeline/
  apps/
    api/          <- everything currently at this repository root
    web/          <- timeline-ui
  packs/          <- promoted out of apps/api
  docs/           <- this file, plus the untracked docs/ at the sandbox root
  .github/workflows/
```

**Packs move to the top level** because they are domain content, not backend code.
They sit inside the Python project today only because the seed loader does. A pack
author should not have to clone a FastAPI service.

**The verifier does not belong here.** When it exists it stays in its own repository:
it is the trust anchor, and "a small program you can read in an afternoon" is a
weaker claim from a subdirectory of a large service. It also needs a permissive
licence while the server is copyleft, and per-directory licensing is harder to
believe than a separate repository. See `OSS-POSITIONING-REFERENCES.md`.

## Preparation already applied

| Change | Why |
|---|---|
| Deleted the root `migrations/` directory | An untouched `alembic init` scaffold. Its `env.py` still carried the "add your model's MetaData object here" placeholder and synchronous `engine_from_config`. The real migrations — 70 of them — live in `app/infrastructure/persistence/migrations/`, which is what `alembic.ini` points at. Nothing referenced the scaffold |
| `.env` anchored to the project directory in `app/core/config.py` | `env_file=".env"` resolved against the process working directory, so the API picked up a different file, or none, depending on where you launched it. Under `apps/api` that becomes a silent failure |
| `defaults.run.working-directory` added to `.github/workflows/ci.yml` | Every one of the 12 run steps assumed the repository root was the Python project. They now inherit one line |

## The move

Run from a clean `main` in `timeline`.

```bash
git switch -c monorepo-layout

# 1. API into apps/api. git mv keeps history; --follow traces across it.
mkdir -p apps/api
git mv app tests scripts ci alembic.ini pyproject.toml uv.lock \
       Makefile .flake8 .python-version .env.example apps/api/
git mv packs packs.tmp && git mv packs.tmp packs   # stays at root, no-op if already there

# 2. Web in, history preserved, as a subtree.
git remote add web ../timeline-ui
git fetch web
git subtree add --prefix=apps/web web main

# 3. CI: one line.
#    .github/workflows/ci.yml -> working-directory: apps/api
#    Add a paths filter so backend changes do not run the web job and vice versa.

# 4. Docs.
mkdir -p docs && cp -r ../docs/* docs/   # the untracked sandbox-root docs
```

## What breaks, and the fix

Verified against the current tree. Everything here has a known cause.

| Breaks | Cause | Fix |
|---|---|---|
| Every CI run step | 12 steps assumed repo root | Already indirected: change `working-directory` to `apps/api` |
| `alembic upgrade head` from the repo root | `prepend_sys_path = .` in `alembic.ini` is relative to the invocation directory | Run alembic from `apps/api`, which CI now does by default. `script_location` uses `%(here)s` and survives the move untouched |
| `storage_root` default | `"./storage"` resolves against the working directory | Set `STORAGE_ROOT` explicitly in every deployed environment. It is a development default and production should never rely on it |
| `vercel.json` | Points at a platform the roadmap replaces, and would need a `rootDirectory` | Delete it as part of the Phase 2 re-platform, not during the move. One change at a time |
| Two `.claude/`, two `.mcp.json`, two `graft/` | Both repositories carry their own | Reconcile into one set at the new root. `graft/workspace.json` already exists at the sandbox root and is multi-repository aware, but the index needs rebuilding |
| `pnpm verify` and the Python gate | Separate pipelines today | Two jobs in one workflow with `paths:` filters. The `ci/*.txt` ratchet baselines carry over unchanged in both |

**Not broken, checked:** `scripts/seed_dev_data.py` and `scripts/seed_from_registration.py`
anchor with `Path(__file__).resolve().parent.parent`, so they follow the move.
`pyproject.toml`'s `testpaths` and exclude globs resolve against the config file.

## Verification checklist

Run from the new root. All of these pass today and must still pass.

```bash
cd apps/api
uv run python -c "from app.main import app; print('app loads')"
uv run pytest -q -m 'not requires_db'      # expect 150 passed
uv run mypy app                            # expect clean, 352 files
uv run ruff check app --output-format=concise | wc -l   # expect 77, the standing baseline

cd ../web
pnpm install && pnpm verify                # expect verify passed
```

Then the one the split repositories could never check, and the strongest single
argument for doing this at all:

```bash
# with the API running
cd apps/web && pnpm run generate:api && npx tsc --noEmit
git diff --exit-code src/lib/timeline-api.ts
```

A non-empty diff means the committed client types had drifted from the API. In two
repositories that drift was invisible until something broke at runtime; here it is
a failing check.

## After the move

- Add the `generate:api` drift check to CI as a required job.
- Decide the licence split before outside contributors arrive: permissive for the
  specification, verifier and any SDKs; copyleft for the server. Relicensing later
  needs every contributor's agreement.
- `git log --follow` works across the move for API files. The subtree gives the web
  history a second root, which is expected and harmless.
