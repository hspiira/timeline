# Timeline

A tamper-evident record engine. Each subject owns an append-only, hash-chained
event log with documents, retention and an audit trail attached, so an
organisation can prove to a third party both what happened and that the file is
complete.

Domains are data, not code. A **pack** is a JSON manifest declaring subject types,
event schemas, document categories with retention, and workflows; installing one
turns the engine into something specific without a plugin or a deployment. See
[`packs/`](packs/).

Licensed under Apache 2.0. See [LICENSE](LICENSE).

## Layout

```
apps/api/     FastAPI service. Also serves the built client and the public pages.
apps/web/     React single-page client.
packs/        Domain manifests. Data, installed per tenant.
docs/         Assessments, the remediation plan, and the migration runbook.
```

Packs sit at the top level rather than inside the API because they belong to
neither side: authoring one should not mean cloning a Python service.

## Running it

Requires Python 3.12, Node 22, pnpm and PostgreSQL.

```bash
cp .env.example .env          # then fill in SECRET_KEY, ENCRYPTION_SALT, DATABASE_URL
make install                  # both applications
make migrate                  # database schema
make dev                      # starts both; one Ctrl-C stops both
```

The API answers on `:8000`, the client on `:3000`, and the client's `/api` calls are
proxied to the API so the request path matches production.

**One `.env` at the root configures both.** A deployment is a single process with a
single environment, so keeping one file here means development cannot drift from
production. Vite reads the same file but only exposes `VITE_`-prefixed values to the
browser, so the API's secrets stay server-side.

## Commands

Everything runs from this directory. There is one virtual environment at the root
with the API installed into it, and one `pyproject.toml` here holding the tool
configuration, so `uv run <anything>` works from the root as well as `make`.

```
make help        list every target
make install     install both applications
make dev         run the API and the web client together
make test        backend tests that need no database
make test-all    every backend test; needs DATABASE_URL
make lint        flake8 and ruff over the API
make typecheck   mypy over the API
make check       lint, typecheck and test
make web-check   the client's gate: build, types, lint, unit tests
make migrate     apply database migrations
make revision    create one:  make revision m="what changed"
```

Ad-hoc commands work the same way, with no directory changes:

```bash
uv run pytest apps/api/tests/unit/test_merkle_service.py -v
uv run alembic downgrade -1
uv run uvicorn app.main:app --reload
uv run python -m scripts.create_test_user <tenant_code> <username> [password]
uv run python -m scripts.seed_dev_data packs/tenancy/pack.json
uv run python -m scripts.seed_rbac <tenant_id_or_code>
uv run python -m scripts.reset_password <user_id> <new_password>
```

Scripts need `DATABASE_URL`. To regenerate the client's API types after a schema
change, with the API running:

```bash
cd apps/web && pnpm run generate:api && git diff --exit-code src/lib/timeline-api.ts
```

That file is generated and should never be hand-edited. A non-empty diff means the
committed types had drifted from the API — the check that only became possible once
the two lived in one repository.

### Optional backend extras

`make install` takes everything. For a narrower install:

| Extra | For |
|---|---|
| `email` | Gmail, Outlook and IMAP ingestion |
| `storage` | S3 document storage. The default `local` backend needs nothing extra |
| `dev` | Tests, lint, type checking |

```bash
uv sync --all-packages --extra storage
```

## Checks

`make check` runs lint, types and tests. CI runs the same commands from this
directory, plus the client's `pnpm verify`.

`apps/api/ci/` and `apps/web/ci/` hold ratchet baselines: a check fails when its
count rises and reports when the count falls so the baseline can be lowered.
Neither may be raised to make a build pass. See
[`docs/CI-RATCHETS.md`](docs/CI-RATCHETS.md).

## Documentation

- [`docs/MONOREPO-MIGRATION.md`](docs/MONOREPO-MIGRATION.md) — this layout, and how it deploys as one origin
- [`docs/IMPLEMENTATION-ROADMAP.md`](docs/IMPLEMENTATION-ROADMAP.md) — sequenced work, remediation and platform merged
- [`docs/CTO-TECHNICAL-AUDIT.md`](docs/CTO-TECHNICAL-AUDIT.md) — findings with `file:line` evidence
- [`docs/CI-RATCHETS.md`](docs/CI-RATCHETS.md) — how the baselines work and why the API runs two linters

### Before quoting the integrity guarantee

It is not yet true as shipped. Anchoring is off by default, documents are outside
the chain, and the verification page requires a login. `docs/CTO-TECHNICAL-AUDIT.md`
sets out exactly what holds today and `docs/REMEDIATION-PLAN.md` sequences the fix.
Do not put the broader claim in a proposal, a demo or a contract before then.
