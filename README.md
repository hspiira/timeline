# new-timeline

## Run

Copy `.env.example` to `.env`. For **Firestore** (default) set `DATABASE_BACKEND=firestore`, `FIREBASE_SERVICE_ACCOUNT_PATH`, `SECRET_KEY`, and `ENCRYPTION_SALT`. For **Postgres** set `DATABASE_BACKEND=postgres` and `DATABASE_URL`, then run `uv run --extra dev python -m alembic upgrade head`.

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

## Firestore (no migrations)

When using Firestore, there are no database “tables” or migrations. Firestore uses **collections** (like tables), which are **created automatically** when you first write a document to that collection. Use the collection names in `app.infrastructure.firebase.collections` so the “schema” stays in one place. For complex queries you may need [composite indexes](https://firebase.google.com/docs/firestore/query-data/indexing); define them in `firestore.indexes.json` and deploy with `firebase deploy --only firestore:indexes` if you use the Firebase CLI.
