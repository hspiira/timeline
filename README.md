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
cd apps/api && uv sync --all-extras && uv run alembic upgrade head && cd ../..
cd apps/web && pnpm install && cd ../..

make dev                      # starts both; one Ctrl-C stops both
```

The API answers on `:8000`, the client on `:3000`, and the client's `/api` calls are
proxied to the API so the request path matches production.

**One `.env` at the root configures both.** A deployment is a single process with a
single environment, so keeping one file here means development cannot drift from
production. Vite reads the same file but only exposes `VITE_`-prefixed values to the
browser, so the API's secrets stay server-side.

### Optional backend extras

`uv sync` installs the API, auth, database, cache and observability. Add what you
use:

| Extra | For |
|---|---|
| `email` | Gmail, Outlook and IMAP ingestion |
| `storage` | S3 document storage. The default `local` backend needs nothing extra |
| `dev` | Tests, lint, type checking |

```bash
uv sync --extra storage        # one
uv sync --all-extras           # everything, including dev
```

## Checks

```bash
make test                                    # backend, no database needed
cd apps/api && uv run pytest                 # backend, all of it; needs DATABASE_URL
cd apps/web && pnpm verify                   # what CI runs for the client
```

## Working on it

```bash
# Database schema. Alembic lives in apps/api.
cd apps/api && uv run alembic upgrade head
cd apps/api && uv run alembic revision --autogenerate -m "what changed"

# Regenerate the client's API types after changing a schema. With the API up:
cd apps/web && pnpm run generate:api && git diff --exit-code src/lib/timeline-api.ts

# Add a UI component. Always extend shadcn rather than building from scratch.
cd apps/web && pnpm dlx shadcn@latest add button
```

`generate:api` writes `apps/web/src/lib/timeline-api.ts`, which is generated and
should never be hand-edited. A non-empty diff after regenerating means the
committed types had drifted from the API — the check that only became possible
once the two lived in one repository.

Operational scripts, all needing `DATABASE_URL`:

```bash
cd apps/api
uv run python -m scripts.create_test_user <tenant_code> <username> [password]
uv run python -m scripts.seed_dev_data    ../../packs/tenancy/pack.json
uv run python -m scripts.seed_rbac        <tenant_id_or_code>
uv run python -m scripts.reset_password   <user_id> <new_password>
```

CI runs both, each scoped to its own directory. `apps/api/ci/` and `apps/web/ci/`
hold ratchet baselines: a check fails when its count rises and reports when the
count falls so the baseline can be lowered. Neither may be raised to make a build
pass.

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
