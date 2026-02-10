# timeline

Multi-tenant event sourcing API with FastAPI.

## Install

Base install (API, auth, DB, cache, Firestore, observability):

```bash
uv sync
```

Optional extras (install when you use these features):

| Extra | Use when |
|-------|----------|
| `email` | Gmail/Outlook/IMAP integration (`aioimaplib`, `google-api-python-client`, `msal`) |
| `storage` | **S3** document storage (`boto3`). Default `local` backend uses `aiofiles` (in main deps). |
| `dev` | Tests, lint, type-checking |

Examples:

```bash
uv sync --extra email --extra storage   # Email + storage
uv sync --all-extras                   # Everything including dev
```

## Required environment variables

Copy `.env.example` to `.env` and set:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Min 32 chars; e.g. `openssl rand -hex 32` |
| `ENCRYPTION_SALT` | Yes | e.g. `openssl rand -hex 16` |
| `DATABASE_BACKEND` | Yes | `firestore` or `postgres` |
| Firestore | If firestore | `FIREBASE_SERVICE_ACCOUNT_KEY` (JSON string) or `FIREBASE_SERVICE_ACCOUNT_PATH` (file path) |
| Postgres | If postgres | `DATABASE_URL` (e.g. `postgresql+asyncpg://user:pass@host:5432/db`) |

Optional: `REDIS_*` (cache), `ALLOWED_ORIGINS`, `REQUEST_TIMEOUT_SECONDS`, storage and telemetry settings. See `.env.example` and `app.core.config`.

## Run

```bash
uv run uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

## Project layout

```
app/
├── main.py              # FastAPI app, lifespan, root route
├── core/
│   └── config.py        # Settings (pydantic-settings)
├── api/
│   └── v1/
│       ├── router.py    # Aggregates v1 routes
│       └── endpoints/   # Route modules (e.g. health)
└── schemas/             # Pydantic request/response models
```

API routes are mounted at `/api/v1` (e.g. `/api/v1/health`).

## Checking the build for Vercel

To confirm the project builds and stays under Vercel’s serverless limits before deploying:

**1. Simulate Vercel’s install and app load (no CLI)**

```bash
pip install uv && uv sync --frozen
uv run python -c "from app.main import app; print('App load OK')"
```

This checks that dependencies install and the app module imports. It does **not** check the deployed bundle size.

**2. Full local Vercel build (recommended)**

Install the [Vercel CLI](https://vercel.com/docs/cli) (`npm i vercel`, or `pnpm i vercel` / `yarn add vercel`), then from the project root:

```bash
# Optional: link to your Vercel project so env vars and settings match
vercel link

# Run the same build Vercel runs (output in .vercel/output/)
vercel build
```

If the build succeeds, the same steps will pass on Vercel. To see serverless function sizes in the logs (e.g. to confirm you’re under 250 MB):

```bash
VERCEL_BUILDER_DEBUG=1 vercel build
```

**3. Deploy a preview**

```bash
vercel
```

This deploys a preview and will fail at build time if the bundle is too large or the build breaks.

## Development

- **Guidelines for contributors and agents:** [docs/AGENT_GUIDELINES.md](docs/AGENT_GUIDELINES.md)
- **Run:** `uv run uvicorn app.main:app --reload`
- **Tests:** `uv run pytest tests/ -v` (requires `uv sync --all-extras` or `--extra dev` for pytest, httpx, pytest-asyncio)
- **Scripts:** `uv run python -m scripts.create_test_user <tenant_code> <username> [password]`, `scripts.seed_rbac <tenant_id_or_code>`, `scripts.reset_password <user_id> <new_password>`. Scripts require Postgres (`DATABASE_BACKEND=postgres`).
- **Lint/format:** `uv run black app tests scripts`, `uv run isort app tests scripts`, `uv run flake8 app tests scripts` (or ruff).

## Firestore (no migrations)

When using Firestore, there are no database “tables” or migrations. Firestore uses **collections** (like tables), which are **created automatically** when you first write a document to that collection. Use the collection names in `app.infrastructure.firebase.collections` so the “schema” stays in one place. For complex queries you may need [composite indexes](https://firebase.google.com/docs/firestore/query-data/indexing); define them in `firestore.indexes.json` and deploy with `firebase deploy --only firestore:indexes` if you use the Firebase CLI.
