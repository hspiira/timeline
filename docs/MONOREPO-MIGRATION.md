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

---

# Deployment: one origin, one process

The API serves the web client rather than the two running on separate ports. This
is a decision about what sits at `/`, not about demoting the API: `/api/v1/*` stays
a first-class, documented surface, because the Embedded model and the planned MCP
surface both need it directly addressable.

## What it buys

| | |
|---|---|
| **CORS stops existing** | `allowed_origins` becomes dead configuration, and the CORS troubleshooting section in the web README stops being needed |
| **Cookies stop being fragile** | `_set_refresh_cookie` currently needs `SameSite=None; Secure` to survive a cross-origin request, which browsers restrict further every year. Same-origin it works with `SameSite=Lax` |
| **CSP collapses** | `connect-src 'self'`, with no per-environment origin list |
| **One container** | The point of self-host as a product. A district office runs one thing, not two |

## The path split

`app/pages/` already serves `/` today through `render_root_page` (`app/main.py:77`).
Keep it and give it the rest of the public surface.

| Path | Served by | Why there |
|---|---|---|
| `/`, `/verify/*` | `app/pages/` | Public and crawlable, works without JavaScript, and a third party verifying a record does not wait on a bundle. The verify page is the one thing that must work for someone who does not trust you |
| `/app/*` | the built SPA | Everything behind a login, where server rendering buys nothing |
| `/api/v1/*` | `api_router` | Unchanged |
| `/docs`, `/openapi.json` | Scalar | See the gating note below |

This settles a contradiction in the audit. `CTO-TECHNICAL-AUDIT.md` lists `app/pages/`
as a delete-unconditionally candidate on the grounds that the React client already
renders these screens. Once the client is purely client-rendered, that reasoning
inverts and `app/pages/` becomes the right home for the public surface. Deleting it
today would remove the handler for `/`.

## Route ordering — the trap

Starlette matches routes in the order they are registered. A catch-all for client
routing must therefore be registered **after** everything else in `create_app`:
after `include_router(api_router, prefix="/api/v1")` at `app/main.py:75`, after `/`,
after `/docs`, and after `/openapi.json`.

Register it earlier and API requests return **200 with an HTML body** instead of
JSON. Nothing raises, no log line looks wrong, and the client simply receives
nonsense. It is the most expensive mistake available here because it does not
announce itself.

```python
# LAST in create_app(), after every other route is registered.
from fastapi.responses import FileResponse

SPA_DIR = Path(__file__).resolve().parent.parent / "web"   # built dist/, copied in
SPA_INDEX = SPA_DIR / "index.html"

app.mount("/app/assets", StaticFiles(directory=SPA_DIR / "assets"), name="spa-assets")

@app.get("/app/{spa_path:path}", include_in_schema=False)
def spa(spa_path: str) -> FileResponse:
    """Hand every client route the shell; the router resolves it in the browser."""
    return FileResponse(
        SPA_INDEX,
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )
```

Scoping the catch-all under `/app/` rather than `/` is what makes the ordering safe
by construction instead of by discipline. A future route added below it cannot be
shadowed.

**Health endpoints must not fall through.** A catch-all at `/` would answer a
mistyped health path with 200 HTML, and an orchestrator would call that healthy.
Under `/app/` this cannot happen, which is a second reason to scope it.

## Cache headers — the one that will bite

This is the same failure the SPA rebuild fixed at build time, arriving again at
deploy time.

| Asset | Header | Consequence of getting it wrong |
|---|---|---|
| `index.html` | `Cache-Control: no-cache, must-revalidate` | A cached shell keeps naming chunk files that the next deploy deleted. The browser requests a hashed file that no longer exists and the app fails with "Failed to fetch dynamically imported module" — the exact symptom this project already spent time on |
| `assets/*.js`, `assets/*.css` | `Cache-Control: public, max-age=31536000, immutable` | Safe because the filenames are content-hashed. Without it every navigation refetches the whole bundle, which matters on a slow connection |

`StaticFiles` does not do this by default. The `FileResponse` above sets the shell's
header explicitly; give the mounted assets theirs in the same middleware that
already sets security headers, keyed on the path prefix. Both halves are required:
an immutable `index.html` breaks deploys, and a `no-cache` bundle wastes bandwidth
on exactly the connections that can least afford it.

## Keep development and production identical

The remaining asymmetry: in development vite serves the client on 3000 and the API
answers on 8000; in production they are one origin. Anything that only works in one
of those will ship.

Remove the difference rather than documenting it:

1. Have the client call **relative** `/api/v1/...` always. `VITE_API_URL` stops existing.
2. Add a dev proxy so the relative path resolves:

```ts
// vite.config.ts
server: {
  proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
}
```

The request path is then byte-identical in both environments, and no code branches
on which one it is running in. Worth doing whether or not the repositories merge.

## Gate the API documentation

`docs_url` and `redoc_url` are already `None` (`app/main.py:45-46`) and Scalar is
mounted at `/docs`. Once the application answers on a public origin, so does the
full API surface, and `openapi.json` is served unauthenticated by default.

For a product sold to institutions that run vendor due diligence, an open API
reference is a finding. Require authentication in production, or disable both and
publish the reference separately.

There is a second reason. `SecurityHeadersMiddleware` currently carries
`script-src 'unsafe-inline'` and `cdn.jsdelivr.net` **only** so Scalar renders.
Dropping documentation from the production image lets the policy tighten to
`script-src 'self'`, which is what the client rebuild made possible by removing the
last inline bootstrap.

## Build and release

Multi-stage, so Node is a build dependency and never a runtime one:

```dockerfile
FROM node:22-slim AS web
WORKDIR /web
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build                      # -> /web/dist

FROM python:3.12-slim
WORKDIR /srv
COPY apps/api/ ./
RUN pip install uv && uv sync --frozen --extra storage
COPY --from=web /web/dist ./web     # what SPA_DIR points at
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Releases become atomic**, which removes client/API version skew — half the reason
the `generate:api` drift check exists. The cost is that a client-only change
restarts the API, so use a rolling restart: this system takes writes that must not
be interrupted mid-transaction.

## Known costs, accepted

- **Python serves static files more slowly than a dedicated proxy.** Fine at current
  scale. If the public verify pages ever take real traffic, put a reverse proxy in
  front rather than adding workers.
- **CI gets slower**, because the image build now needs a Node stage.
- **`vercel.json` becomes meaningless.** Delete it with the Phase 2 re-platform, not
  during this move. One change at a time.
