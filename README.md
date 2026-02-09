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

## Firestore (no migrations)

When using Firestore, there are no database “tables” or migrations. Firestore uses **collections** (like tables), which are **created automatically** when you first write a document to that collection. Use the collection names in `app.infrastructure.firebase.collections` so the “schema” stays in one place. For complex queries you may need [composite indexes](https://firebase.google.com/docs/firestore/query-data/indexing); define them in `firestore.indexes.json` and deploy with `firebase deploy --only firestore:indexes` if you use the Firebase CLI.
