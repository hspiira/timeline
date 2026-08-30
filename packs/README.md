# Domain packs — the open-source engine + modules model

This is the positioning for the timeline product as a **society-level open-source platform** rather than a single-industry SaaS. It is the umbrella identity; money lending is one pack among many.

## The core idea

The engine is a generic, **tamper-evident record-of-truth platform** with three primitives:

1. **Immutable hash-chained event log** per subject — proves *what happened, when, to whom, and that nothing was altered after the fact — not even by the host.*
2. **Per-subject complete file** — events + documents + retention, tied to one entity.
3. **Plug-in connectors** (`email`, `file_watch`, `kafka`, `cdc`) + schema/transition/workflow configuration — the "module" layer in embryo.

A **domain pack** is a versioned, shareable manifest (this directory) that installs a complete domain on top of the engine — a subject type, its event schemas, its document categories with retention, its workflows, plus sample subjects/events. Anyone can author, version, and share a pack. Money lending is just one pack.

## The unifying sentence

> *A place to keep a record no one — not even the operator — can silently change, that the party who needs to trust it can verify independently.*

That is a "notary layer for the digital economy" — a societal primitive, not an industry product.

## Everyday packs society could run

| Pack | Subject = | Tamper-proof value |
|---|---|---|
| `tenancy` (this) | rental agreement | prove rent paid at dispute/loan time |
| `employment-proof` | consented employment record | escrow-worthy income history for visa/rent/loan |
| `sacco-membership` | member + contributions | dispute-free group money |
| `loan-ledger` | loan file (needs money primitives) | court-ready loan file of record |
| `audit-trail` | any process file | always-on regulator-ready audit log |
| `consent-log` | consented record access | proof of who saw what, when |

## Positioning in the landscape

Generic tamper-evident records exist (DocuSign-style regulated notaries, country PKI / MoMo rails, plain databases). **None is an open-source, per-domain-pack record engine for everyday Ugandan life.** Differentiation:

1. **Open core + pack ecosystem** — anyone can vendor a domain pack; the engine is free.
2. **Independent verification** — a verifier who doesn't trust you (or the host) can still check a proof; also true on self-hosted instances (data residency, DPPA-aware).
3. **Works where deployed** — self-hostable, not only SaaS.
4. **Cheap engine, shared cost of packs** — the crypto is commodity/free; costs live in the packs, which the ecosystem shares.

## The honest two rules (avoid the platform trap)

1. **Earn the platform with one real pack first.** Ecosystems form from people scratching their own itch. **The `tenancy` pack is that reference pack** — built from existing primitives, near-zero new engine features. It attracts the builders of packs 2, 3, 4 (employment-proof, SACCO, loan-ledger).
2. **Do NOT build the pack-authoring SDK before the first packs exist.** Abstract the platform from real packs, not the reverse. One working pack now; the loader/SDK later, generalized from it.

## Next steps to make this real

- [x] Extend `scripts/seed_dev_data.py` to process `subject_types` + `document_categories` so a pack installs in one command, idempotently (run with the admin/BYPASSRLS role; see `packs/tenancy/README.md` and `scripts/_session.py`).
- [ ] Add a "how to author a pack" CSV-of-fields / schema reference (`docs/PACKS.md`) with the exact repo signatures.
- [ ] Land a second pack (`employment-proof` or `sacco-membership`) built by someone else, to prove the ecosystem model.
- [ ] Expose the free verification URL in the UI as the word-of-mouth "prove my record" demo.
