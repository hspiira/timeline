# Tenancy pack (`tenancy`) — reference domain module

A **domain pack** that turns the generic timeline engine into a *tamper-proof rental record*. It is the concrete proof-of-concept for the open-source "engine + swappable packs" model: one real, everyday-Uganda use, built entirely from the engine's existing primitives (no new engine features required).

## What it does

For each **tenancy** (one subject per rental agreement between tenant and landlord):

- **Rent paid** — hash-chained event per month (amount, currency, method, receipt ref).
- **Deposit paid / refunded** — events.
- **Lease signed / eviction notice / dispute opened / dispute resolved** — events with transition-able lifecycle.
- **Documents with retention** — lease agreement, ID proof, rent receipts, notices (10-year retention).
- **Free verification story** — because every event is hash-chained, the record can be verified without trusting the platform host (the engine's core value).

**Wedge for a tenant:** present a single verification URL / court-ready record pack to a landlord, a bank (when applying for a loan), or a court — proving "I paid my rent, on time, and the record cannot have been silently altered."

## What the pack installs (per this manifest, into tenant `tenancy-demo`)

| Engine primitive | Count | What |
|---|---|---|
| `subject_types` | 1 | `tenancy` with schema (tenant, landlord, property, rent) |
| `event_schemas` | 7 | lease_signed, rent_paid, deposit_paid, deposit_refunded, eviction_notice, dispute_opened, dispute_resolved |
| `document_categories` | 4 | lease_agreement, id_proof, rent_receipt, notice (+ retention) |
| `workflows` | 1 | side-effect on `rent_paid` |
| `subjects` | 1 | sample tenancy `TEN-0001` |
| `events` | 5 | sample ledger (lease, deposit, 3 months rent) |

## Install

`scripts/seed_dev_data.py` now processes all of this pack's sections, including `subject_types` and `document_categories`. Install once:

```
uv run python -m scripts.seed_dev_data packs/tenancy/pack.json
```

**Operational note (idempotent re-runs):** the loader re-uses the existing check-before-insert pattern, which is idempotent under the **administrator/migration role** (BYPASSRLS) — the documented contract for these scripts (see `scripts/_session.py`). Running under an RLS-scoped application role, the tenant-existence pre-check (`get_by_code`) cannot see an already-created tenant, so a second run collides on the unique tenant code. **Run pack installs with the admin connection string**, not `timeline_app`.

Fresh install verified on a real Postgres (app role): subject type, 7 event schemas, 4 document categories (10-yr retention), subject, workflow, and 5 hash-chained events all created.

If you prefer manual setup instead of a single command:
1. Drop the engine-compatible sections (`tenants`, `event_schemas`, `workflows`, `subjects`, `events`) into `scripts/seed-data.json` and run `seed_dev_data`, then create the subject type + categories via the API (`POST /subject-types`, `POST /document-categories`).
2. Or run the file directly once the admin role is configured.

Idempotency rule (match `seed_dev_data.py`): skip any subject_type / event_schema / document_category that already exists for the tenant; skip any subject already present by `external_ref`.

## Authoring packs

See `packs/README.md` — this pack is the reference for how any domain (money lending, SACCO groups, employment/income proof, audit trail) becomes a versioned, shareable `pack.json`.
