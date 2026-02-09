# new-timeline

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
