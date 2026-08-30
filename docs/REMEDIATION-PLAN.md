# Remediation Plan

**Date:** 2026-08-29
**Input:** `CTO-TECHNICAL-AUDIT.md`
**Scope directive:** every finding, no triage, no deferrals by severity.

## Relationship to the build freeze

`COO-DECISION.md` directive 1 imposes a 90-day feature freeze. **This plan does not violate it.** Producing the plan costs nothing; executing Phases 2 onward does. Phases 0 and 1 are explicitly exempt: Phase 0 is read-only diagnosis, Phase 1 is a documentation and claim-scope action. Both should happen now regardless of what discovery finds.

Everything from Phase 2 onward is held until either the 90-day gates clear or the freeze is deliberately overridden.

## Three corrections to the audit, found while planning

The audit was directionally right on all three but understated each. The plan is built on the corrected version.

### C1. The append-only trigger blocks TSA anchoring itself

The audit said three `UPDATE event` paths conflict with the trigger. Verified, and the identity of those paths matters more than the count:

| Path | File | What it writes |
|------|------|----------------|
| `set_tsa_anchor_for_events` | `event_repo.py:290-298` | `tsa_anchor_id`, `integrity_status=VALID` |
| `mark_event_integrity_status` | `event_repo.py:300-309` | `integrity_status` |
| `mark_events_repaired_from_seq` | `event_repo.py:311-327` | `integrity_status=REPAIRED` |

The trigger function is **unconditional**, with no column exemption whatsoever:

```sql
CREATE OR REPLACE FUNCTION prevent_event_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'event rows are immutable; create a compensating event instead'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$
```
(`migrations/versions/i9j0k1l2m3n4_immutable_audit_event_triggers.py`)

So the sharper statement is: **if the trigger is deployed, TSA anchoring cannot write back its own results.** The integrity feature is not merely dead on serverless; it is structurally blocked by the immutability guarantee it exists to serve. Mutable integrity metadata is living on an immutable table. That is a design conflict, not a bug, and it needs an architectural fix (R-07).

### C2. The `event` table has no actor column at all

The audit said the actor is not covered by the hash. It is worse: **`event` records no actor whatsoever.** No `created_by`, no `user_id`, no actor field (`app/infrastructure/persistence/models/event.py`). Attribution exists only in `audit_log.user_id`, a separate table with no structural join to the event.

For the money-lender vertical this is severe. Under Tier 4 Act s.88(1) the lender produces the loan record in court; "who entered this repayment" is precisely what opposing counsel challenges. The product currently cannot answer it from the chain. This is reclassified **P0**, not P2.

### C3. No hash versioning exists, so changing hash coverage is a breaking migration

No `hash_version`, `algorithm_version` or equivalent exists anywhere in the codebase. The hash content dict in `hash_service.py:57-64` is hardcoded. Adding fields to it invalidates every chain ever written. R-08 therefore requires a versioned hash scheme and a dual-verification path, not a one-line edit.

### Three things that are cheaper than the audit implies

| Finding | Why it helps |
|---------|--------------|
| **S3 storage backend already exists** (`app/infrastructure/external/storage/s3_storage.py`, `factory.py`, `protocol.py`) | R-12 is configuration and testing, not implementation |
| **Background jobs are already declaratively structured.** `_background_jobs(settings)` returns descriptors with `enabled`, `attr`, `label`, `task_name`, `make_coro` (`lifespan.py:95-113`) | R-05 extraction into a worker process is a re-host of an existing abstraction, not a rewrite |
| **`document` already has a nullable `event_id` column** (`models/document.py:29`) | R-06 has its linkage in place; the fix is to emit the event and populate it |

---

## Workstream summary

| Phase | Theme | Items | Est. effort | Gate |
|-------|-------|-------|-------------|------|
| **0** | Ground truth | R-01, R-02 | **2 days** | None. Do now |
| **1** | Claim containment | R-03 | **1 day** | None. Do now |
| **2** | Platform and residency | R-04, R-05 | **3-4 weeks** | Freeze lift |
| **3** | Integrity correctness | R-06 to R-14 | **5-6 weeks** | Phase 2 |
| **4** | Security hardening | R-15 to R-21 | **2 weeks** | Phase 2 (partial) |
| **5** | Test backfill | R-22 to R-25 | **2 weeks** | Interleaved |
| **6** | Scale and cost | R-26 to R-30 | **2 weeks** | Phase 3 |
| **7** | Deletion | R-31 | **1 week** | Phase 3 |
| **8** | Compliance and external validation | R-32 to R-34 | **2 weeks + external** | Phases 2-4 |

**Total: approximately 17 to 20 engineer-weeks**, single engineer, sequential. *These are estimates, not measured figures. They exclude the money primitives and court-pack work the money-lender vertical requires, which is separate product build, not remediation.*

**Critical path:** R-01 → R-04 → R-05 → R-07 → R-08 → R-11 → R-13 → R-34.

---

## Phase 0 — Ground truth

**No code changes. Exempt from the freeze. Nothing else in this plan is trustworthy until both are answered.**

### R-01. Determine whether RLS is live or the app role bypasses it
**Audit ref:** P0-1
**Problem:** All three background jobs open `AsyncSessionLocal()` with no tenant context and never call `apply_tenant_context` or `set_tenant_id` (`anchor_job.py:50`, `tsa_batch_job.py:88`, `projection_engine_job.py:38`). Under working FORCE RLS with no session variable, every policy evaluates NULL: the jobs see zero rows and write nothing, silently. So either RLS is live and anchoring is dead, or anchoring works and the app role bypasses RLS.

**Action:**
```sql
SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user;
```
Run as the application role against each environment.

**Acceptance:** a written answer per environment (dev, staging, production if one exists), recorded in this file.
**Branches:**
- Returns `true` (bypass): **tenant isolation has no database layer.** R-16 becomes P0 and jumps the queue.
- Returns `false` (RLS enforced): **all anchoring has been silently dead.** Every "verified" chain in the database is unanchored. R-05 and R-09 become the critical path, and every existing tenant needs re-anchoring from scratch.

**Effort:** 1 hour. **Depends on:** nothing.

### R-02. Determine whether the append-only trigger is deployed
**Audit ref:** P0-7
**Problem:** See C1. Three write paths conflict with an unconditional trigger.

**Action:**
```sql
SELECT tgname, tgrelid::regclass, tgenabled
FROM pg_trigger
WHERE tgname IN ('prevent_event_update_delete', 'prevent_audit_log_update_delete');
```
Then confirm which alembic revisions are applied: `alembic current`.

**Acceptance:** written answer per environment.
**Branches:**
- Trigger present: TSA anchoring, integrity status marking and chain repair **all raise at runtime**. R-07 is blocking.
- Trigger absent: `event` is mutable at the database level, so the append-only guarantee is application-layer only. R-07 is still required, plus deploying the trigger.

**Effort:** 1 hour. **Depends on:** nothing.

---

## Phase 1 — Claim containment

### R-03. Narrow every written and spoken integrity claim to what is presently true
**Audit ref:** P0-2, P0-4, P0-5
**Problem:** The claim the product rests on is not true as shipped. Anchoring flags default `False` (`config.py:99,105,107`); STANDARD-profile tenants are never anchored; the verification page requires login (`verify/$subjectId.tsx:33`); documents carry no tamper-evidence; the tenant-tip anchor commits only to whichever subject wrote last. The exposure is a customer relying on the claim in court and opposing counsel finding this.

**Action:** produce a one-page **Integrity Claim Statement** that says only what the code does today, and use it verbatim in every deck, demo script, proposal and contract until the phase-3 items land. Retire all broader language.

Presently defensible, subject to R-01 and R-02: per-subject epoch sealing with a Merkle root anchored to an RFC 3161 TSA, which refuses to seal without the anchor (`epoch_sealing_job.py:88,107,127-141`), **when explicitly enabled on the COMPLIANCE or LEGAL_GRADE profile and when running on a host that can execute background loops.**

Not presently claimable: tamper-evidence of documents; tamper-evidence of actor attribution; independent third-party verification; any guarantee for STANDARD-profile tenants; any guarantee on serverless.

**Acceptance:** the statement exists, is dated, and every outward-facing artefact matches it. No artefact claims anything absent from it.
**Effort:** 1 day. **Depends on:** R-01, R-02 (which determine what is true).

---

## Phase 2 — Platform and residency

### R-04. Re-platform off Vercel serverless to a long-lived process host in Uganda
**Audit ref:** P0-6, A6
**Problem:** `vercel.json` declares a serverless FastAPI deployment. Against that, `lifespan.py:104-110` starts four infinite `while True` background loops. Serverless cannot run them, cannot hold websockets, cannot persist the process-local `DEFAULT_TSA_BATCH_QUEUE` (`tsa_batch_queue.py:23-30`, self-documented "Not durable"), cannot rate-limit in memory, and cannot store files on an ephemeral filesystem. Separately, DPPA 2019 s.19 restricts processing personal data outside Uganda without adequacy or per-subject consent, and there is no consent-capture mechanism.

**Action:** move once, to Ugandan hosting, on a long-lived process model (containers or VMs). Do not re-platform twice. Expect self-managed Postgres, since Uganda has thin managed options.

Sub-tasks: select provider and region; provision Postgres with backup, PITR and monitoring; provision Redis; containerise API and worker; migrate object storage to the existing S3-compatible backend; set up CI/CD, secrets management and TLS; cut over with a rehearsed rollback.

**Acceptance:** API and worker run as long-lived processes in Uganda; a background job demonstrably executes on a schedule and writes to the database; personal data at rest is in-country; a documented rollback exists and has been rehearsed once.
**Effort:** 3 to 4 weeks *(estimate)*. **Depends on:** R-01.
**Note:** blocks R-05, R-15, R-12, and is a precondition for every integrity item that requires a running job.

### R-05. Extract background jobs into a separate worker process with tenant context
**Audit ref:** P0-6, P0-1
**Problem:** Jobs are coroutines started inside the API lifespan, which couples job execution to API process lifetime and to request-serving capacity. They also run with no tenant context set.

**Action:** the descriptor structure at `lifespan.py:95-113` already models jobs declaratively, so extract that list into a standalone worker entrypoint. For each job, wrap per-tenant work in an explicit tenant context using `set_tenant_id` (`app/core/tenant_context.py:16`) and the repository-level `apply_tenant_context` (`event_repo.py:67`), so each unit of work runs under the correct RLS session variable. Replace the in-memory `DEFAULT_TSA_BATCH_QUEUE` with a durable queue table or Redis-backed queue. Add leader election or advisory locks so multiple worker replicas do not double-anchor.

**Acceptance:** jobs run in a process independent of the API; each job's database work executes under an explicit tenant context; the TSA batch queue survives a worker restart with zero lost items, proven by a restart test; two concurrent workers produce exactly one anchor per epoch, proven by a test.
**Effort:** 1.5 weeks *(estimate)*. **Depends on:** R-04.

---

## Phase 3 — Integrity correctness

This phase is what makes the product claim true. Nothing here is optional under a no-compromises directive.

### R-06. Bring documents into the hash chain
**Audit ref:** P0-3
**Problem:** `document_operations.py` computes SHA-256 (`:67-72, :147`) and writes it to `document.checksum`, and contains **no `create_event` call** (verified). Replace the file, update the column, nothing detects it.

**Action:** emit chain events on every document mutation, carrying the checksum, storage reference, size, MIME type and version, and populate the existing nullable `document.event_id` (`models/document.py:29`). Minimum event set: `DOCUMENT_ATTACHED`, `DOCUMENT_REPLACED`, `DOCUMENT_VERSIONED`, `DOCUMENT_DELETED`. Deletion must be a compensating event, never a chain mutation. Verification must re-read the stored object, recompute the checksum, and compare against the chained value, not against the `document` row.

**Acceptance:** a test that alters a stored file and its `checksum` column, then shows verification fails. A test that a deleted document leaves an intact, verifiable chain record of its prior existence.
**Effort:** 1 week *(estimate)*. **Depends on:** R-07 (event write path must be settled first).

### R-07. Move mutable integrity metadata off the immutable `event` table
**Audit ref:** P0-7. See C1.
**Problem:** `integrity_status`, `tsa_anchor_id` and `epoch_id` are mutable columns on a table an unconditional database trigger forbids updating. The three write paths in C1 cannot execute where the trigger is deployed.

**Action, and this is a design decision rather than a patch.** Two options:

| Option | Approach | Assessment |
|--------|----------|------------|
| **A. Side table (recommended)** | New `event_integrity_state` table keyed by `event_id`, holding `integrity_status`, `tsa_anchor_id`, `epoch_id`, `merkle_leaf_hash`. `event` becomes genuinely immutable and the trigger stays unconditional | **Take this.** It preserves the guarantee without exception. The immutable table stays immutable; derived, revisable state lives where revision is legitimate |
| **B. Column-aware trigger** | Amend the trigger to permit updates touching only integrity metadata columns | Rejected. It puts a permanent, auditable hole in the immutability claim, and the hole is exactly where an attacker would aim. Under a no-compromises directive this is not acceptable |

Sub-tasks: create the table and migration; backfill from existing `event` rows; repoint the three write paths and all readers; drop the moved columns from `event` in a later migration once readers are confirmed; deploy the trigger everywhere it is absent; add RLS policy and FORCE RLS to the new table, and extend `test_every_tenant_scoped_table_has_a_policy` to cover it.

**Acceptance:** all three former UPDATE paths write to the side table and succeed with the trigger deployed; an attempted `UPDATE event` raises in every environment; the new table is covered by the existing RLS policy test.
**Effort:** 1.5 weeks *(estimate)*. **Depends on:** R-02.
**Blocks:** R-06, R-09, R-13.

### R-08. Add an actor column to `event` and cover it in the hash
**Audit ref:** P2-1. See C2.
**Problem:** `event` has no actor column at all. Attribution exists only in `audit_log`, joined by nothing structural. Under s.88(1) court production, "who entered this" is unanswerable from the chain.

**Action:** add `created_by` (and `actor_type` to distinguish human, connector, workflow and system actors) to `event`, populate from the authenticated principal on every write path including connectors and workflow actions, and include both in the hash under the versioned scheme from R-09. Backfill is impossible for historical events; mark them `actor_unknown` explicitly rather than guessing, and make verification report that honestly.

**Acceptance:** every event write path populates an actor; a test proves re-attribution changes the hash and fails verification; historical events are visibly labelled unknown rather than silently null.
**Effort:** 1 week *(estimate)*. **Depends on:** R-09.

### R-09. Introduce a versioned hash scheme and close the coverage gaps
**Audit ref:** P2-1. See C3.
**Problem:** `hash_service.py:47-66` covers six fields. Missing: `tenant_id` (an event moved between tenants still verifies clean), `event_seq` (ordering is not committed to), actor (R-08), and server receipt time (only user-supplied `event_time` is hashed, so backdating is invisible until the next anchor). No hash versioning exists, so changing coverage breaks every existing chain.

**Action:** add a `hash_version` column to `event`. Define **v2** covering `tenant_id`, `event_seq`, `created_by`, `actor_type`, `server_received_at` plus the existing six. Keep **v1** verification logic permanently for historical events and dispatch on the stored version. Write v2 for all new events. Document the cutover epoch per tenant so an auditor can see exactly where coverage changed, and why.

**Acceptance:** v1 chains still verify; v2 chains verify; a test proves each newly covered field, when altered, causes verification to fail; the version is visible in verification output and in the court-pack artefact.
**Effort:** 1.5 weeks *(estimate)*. **Depends on:** R-07.
**Blocks:** R-08, R-13.

### R-10. Fix `detect_and_flag` to recompute hashes
**Audit ref:** P2-4
**Problem:** `chain_repair_service.py:134-153` only compares `ev.previous_hash != last_hash` and never recomputes. A payload edited without touching the hash column passes it clean, while `VerificationService._verify_event` (`verification_service.py:243-320`) correctly recomputes. Two functions in one codebase disagree on what verification means.

**Action:** extract the verification primitive into one shared function and have both call it. There must be exactly one definition of "verified" in the system.

**Acceptance:** a test that edits a payload without touching the hash and proves both call sites detect it.
**Effort:** 2 days *(estimate)*. **Depends on:** R-09.

### R-11. Replace tenant-tip anchoring with a commitment over all subject tips
**Audit ref:** P2-2
**Problem:** `AnchorChainTipsUseCase.run_for_tenant` (`anchor_chain_tips.py:55`) calls `get_chain_tip_hash(tenant_id)`, which is `ORDER BY event_seq DESC LIMIT 1` across the whole tenant (`event_repo.py:398-407`). Each subject has an independent chain, so the anchor commits only to whichever subject wrote last. The `chain_anchor.subject_tips` and `event_count` fields exist for this fix, are read in `_to_result` (`chain_anchor_repo.py:38-39`), and are **never written**.

**Action:** compute a Merkle root over every subject tip in the tenant, anchor that root, and populate `subject_tips` and `event_count`. Use the R-12 RFC 6962 construction.

**Acceptance:** an anchor commits to every subject in the tenant; a test proves altering any subject's tip invalidates the tenant anchor; `subject_tips` and `event_count` are populated on every new anchor.
**Effort:** 1 week *(estimate)*. **Depends on:** R-12.

### R-12. Adopt RFC 6962 Merkle construction
**Audit ref:** P2-3
**Problem:** `merkle_service.py:183-198` duplicates the odd node (`right_hash = left_hash`, `:190`), the CVE-2012-2459 shape, so `[A,B,C]` and `[A,B,C,C]` produce an identical root and the root does not commit to leaf count. There is no leaf/internal domain separation (`:191-192`, plain concatenation), which RFC 6962 prevents by prefixing leaves `0x00` and nodes `0x01`. `build_and_store` calls `delete_for_epoch` then rebuilds (`:176`), silently replacing a stored tree.

**Action:** implement RFC 6962 exactly, including domain separation and correct odd-node handling. Commit leaf count in the sealed epoch record. Make rebuild an explicit, audited operation that refuses to overwrite a sealed epoch's tree.

**Acceptance:** a test proving `[A,B,C]` and `[A,B,C,C]` produce different roots; a test proving an internal node cannot be presented as a leaf; a test proving a sealed epoch's tree cannot be silently replaced. Validate against RFC 6962 test vectors.
**Effort:** 1 week *(estimate)*. **Depends on:** nothing. **Can start in parallel with Phase 2.**

### R-13. Enable integrity by default and remove the STANDARD blind spot
**Audit ref:** P0-2
**Problem:** `chain_anchor_enabled`, `epoch_sealing_enabled` and `tsa_batch_enabled` all default `False` (`config.py:99,105,107`). The STANDARD profile has no anchoring at all, giving an unbounded attack window, and it is the default.

**Action:** default all three to `True`. Give STANDARD a real anchoring interval, so no profile is ever unanchored; if a genuinely unanchored tier is wanted for cost reasons, name it explicitly (for example `NONE`) so choosing it is a deliberate, logged act rather than a silent default. Refuse to start if a profile requiring TSA has no reachable TSA configured, mirroring the existing fail-closed behaviour at `epoch_sealing_job.py:88,107`.

**Acceptance:** a fresh install anchors without configuration; a test proves startup fails when a TSA-requiring profile has no TSA; no tenant can be in an unanchored state without an explicit, audited choice.
**Effort:** 3 days *(estimate)*. **Depends on:** R-05, R-07, R-11.

### R-14. Correct the chain repair docstring and close its guardrail gap
**Audit ref:** P2-5, P1-6
**Problem:** The `complete_repair` docstring (`chain_repair_service.py:219-320`) says "Re-hash from break". It does not re-hash; it opens a new epoch from the last good hash, appends a `CHAIN_REPAIR` event and marks the broken tail `REPAIRED`. The design is right; the docstring describes a far more dangerous operation and will mislead anyone reasoning about the guarantee. Separately, `complete_repair(repair_id)` takes no `tenant_id` and performs no tenant check, unlike `approve_repair` (`:201`).

**Action:** rewrite the docstring to describe abandonment rather than rewriting, and state explicitly that history is preserved. Add the tenant check to `complete_repair`.

**Acceptance:** docstring matches behaviour; a test proves `complete_repair` rejects a cross-tenant `repair_id`.
**Effort:** 1 day *(estimate)*. **Depends on:** R-07.
**Note:** `CTO-TECHNICAL-AUDIT.md` P5 also lists chain repair as a deletion candidate. **Fix it here rather than delete it.** Deletion is only correct if discovery shows no buyer needs a repair path, and that is a Phase 7 decision, not a Phase 3 one.

---

## Phase 4 — Security hardening

### R-15. Make rate limiting durable and correct behind a proxy
**Audit ref:** P1-1
**Problem:** `Limiter(key_func=get_remote_address)` plus a module-level `defaultdict` (`limiter.py:16,32-48`). On serverless every invocation is a fresh process, so **login brute-force protection does not exist in production**. It is also unverified whether the proxy passes a usable client IP or whether `get_remote_address` sees the proxy address, in which case all clients share one bucket.

**Action:** move limiter state to Redis. Verify and correctly configure trusted proxy headers for the new host from R-04, and pin the trusted-proxy list rather than trusting `X-Forwarded-For` blindly. Apply strict limits to authentication, password reset and the public verification endpoints from R-33.

**Acceptance:** a test proving limits hold across process restarts; a test proving two distinct client IPs get distinct buckets through the proxy; documented limits per endpoint class.
**Effort:** 3 days *(estimate)*. **Depends on:** R-04.

### R-16. Confirm and enforce that the app role cannot bypass RLS
**Audit ref:** P1-4, A2
**Problem:** `rls_check.py:75-86` asserts the app role lacks `BYPASSRLS`, but it is wired to `/health/ready` and `rls_check_policies` defaults `False` (`config.py:127-129`; `_core.py:83-102`). **Vercel does not poll readiness endpoints, so the safeguard never runs.**

**Action:** move the check to application startup, fail closed on violation, and default `rls_check_policies` to `True`. Keep the readiness wiring as well. If R-01 returned `true`, provision a new non-bypassing role first and migrate to it, and treat that as P0.

**Acceptance:** the application refuses to start against a bypassing role; the check runs in every environment; a test covers the refusal path.
**Effort:** 2 days *(estimate)*. **Depends on:** R-01, R-04.

### R-17. Invert `X-Tenant-ID` precedence so the JWT wins
**Audit ref:** P1-5
**Problem:** `tenant_context.py:20-33` prefers the unauthenticated, attacker-controlled header over the JWT. `get_tenant_id` (`_core.py:222-265`) validates format and existence but never checks the user belongs to that tenant. It stops at `require_permission:738` and again at `get_current_user_optional` (`:628`) under live RLS, so no leak was found. But it is the same check twice, in two places, both of which must hold.

**Action:** make the JWT authoritative for authenticated requests. Permit the header only where no JWT tenant exists, such as pre-authentication routes, and only after format validation. Keep both existing checks; this removes the class rather than replacing the defence.

**Acceptance:** a test proving an authenticated tenant-A user sending `X-Tenant-ID: B` is scoped to A, and that the outcome no longer depends on RLS being live.
**Effort:** 2 days *(estimate)*. **Depends on:** nothing. **Can start in parallel.**

### R-18. Add missing tenant predicates to write paths
**Audit ref:** P1-6
**Problem:** `mark_event_integrity_status` uses `.where(Event.id == event_id)` with no tenant predicate (`event_repo.py:300-309`). `complete_repair` performs no tenant check (`chain_repair_service.py:219-236`). Both are cross-tenant write primitives if RLS is ever off, which R-01 may reveal it is.

**Action:** require `tenant_id` on both signatures and predicate every statement on it. Audit every other repository method for the same shape and fix all instances, not only these two.

**Acceptance:** no repository write method lacks a tenant predicate; a test asserts this by introspection where feasible; cross-tenant attempts fail with RLS disabled as well as enabled.
**Effort:** 3 days *(estimate)*. **Depends on:** R-07 (which relocates one of these paths).

### R-19. Fix session and transaction handling
**Audit ref:** P1-7
**Problem:** Three defects. `_set_tenant_context` silently returns when tenant context is unset (`database.py:97-99`), which fails closed but produces an outage rather than an error. `get_db` runs `SET LOCAL` outside an explicit transaction, relying on SQLAlchemy autobegin (`database.py:110-127`), and the code comments record that this **has already broken in production**: "which it did, on both the API and the seed scripts, with nothing covering it" (`create_event.py:150-151`). `_release_ambient_transaction` rolls back the caller's session (`create_event.py:138-171`), latent data loss for any future caller that writes first.

**Action:** raise explicitly rather than silently returning when tenant context is required and absent. Open an explicit transaction before `SET LOCAL` rather than depending on autobegin. Remove or contain `_release_ambient_transaction` so it cannot discard a caller's uncommitted work, and cover the previously-broken path with the test the comment says was missing.

**Acceptance:** a regression test for the specific production breakage the comments describe; a test proving a caller that writes before invoking the event path does not lose its writes.
**Effort:** 3 days *(estimate)*. **Depends on:** R-04.

### R-20. Constrain file uploads
**Audit ref:** P1-3
**Problem:** `allowed_mime_types: "*/*"` by default with a 100MB limit (`config.py:72-73`), and the MIME type is taken from the client's `content_type` with no server-side sniffing (`documents.py:86,95`). Filename sanitisation itself is sound (`document_operations.py:52-64`).

**Action:** default to an explicit allowlist appropriate to a loan file: PDF, common images, and office documents if genuinely required. Sniff content server-side and reject on mismatch with the declared type. Lower the default size limit and make it configurable per category. Store uploads outside any web root and serve only through authenticated, signed URLs.

**Acceptance:** a test proving a file whose declared type contradicts its content is rejected; a test proving a disallowed type is rejected regardless of declared type.
**Effort:** 3 days *(estimate)*. **Depends on:** nothing. **Can start in parallel.**

### R-21. Separate key material and introduce managed key storage
**Audit ref:** P1-2, A1
**Problem:** Credential encryption falls back to `SECRET_KEY` (`encryption.py:25-29`), so the JWT signing secret doubles as the credential encryption key, and rotating the JWT secret destroys every stored OAuth credential simultaneously. `EnvelopeEncryptor` writes a generated KDF salt to `storage_root/.encryption_kdf_salt` if unset (`envelope_encryption.py:36-45`), which on ephemeral storage differs per invocation and makes credentials undecryptable on the next request. There is no KMS or HSM anywhere; key material is an environment variable.

**Action:** separate the signing key from the encryption key, with independent rotation procedures for each. Persist the KDF salt in the database or a secret store, never on an ephemeral filesystem, and fail closed if it is absent rather than generating a new one. Move key material into the managed secret store of the R-04 host, and document a rotation runbook. Evaluate an HSM or KMS as a follow-on rather than a precondition, since the R-33 external assessor will have a view on what a regulated buyer requires.

**Acceptance:** rotating the JWT secret leaves stored credentials decryptable, proven by test; a missing KDF salt causes a startup failure rather than silent key divergence; a written rotation runbook exists.
**Effort:** 4 days *(estimate)*. **Depends on:** R-04.
**Note:** if R-21 is deferred, email ingestion is a deletion candidate under R-31 anyway, which removes most of the credential-encryption surface. Sequence R-31's decision before doing the full R-21 work, to avoid hardening code you are about to delete.

---

## Phase 5 — Test backfill

Coverage is 3,649 test lines against 43,552 app lines, roughly 8.4%. The existing tests are well designed; the gaps map almost exactly onto the features a regulated buyer would be shown.

**Standing rule for this plan: every R-item above ships with the tests named in its own acceptance criteria.** Phase 5 is the backfill for what already exists untested, not the whole testing effort.

### R-22. Make the suite safe to run
**Audit ref:** A4
**Problem:** `.env` exists, `Settings` loads it (`config.py:175-177`), and `tests/conftest.py` executes `CREATE ROLE` and `GRANT USAGE, SELECT ON ALL SEQUENCES` against whatever `DATABASE_URL` that file contains (`conftest.py:85-89`). Running pytest can write to a live database using production secrets. This is why the audit did not run it.

**Action:** make the suite refuse to run against any database not explicitly marked as a test database, by naming convention or a required environment guard. Provide a documented one-command throwaway Postgres, containerised. Add this to CI.

**Acceptance:** running pytest against a non-test `DATABASE_URL` fails immediately with a clear message; a documented command spins up a disposable database and runs the full suite green.
**Effort:** 3 days *(estimate)*. **Depends on:** nothing. **Do this first in the phase; everything else depends on being able to run tests safely.**

### R-23. Cover the untested integrity paths
**Audit ref:** A4
**Problem:** No test file exists for TSA anchoring, epoch sealing, or chain repair. Chain repair is the highest-risk code in the system and is entirely untested.

**Action:** integration tests covering epoch seal and refusal to seal without a TSA anchor; TSA client behaviour against a stub, including timeout, malformed token and unavailable service; the full chain repair lifecycle including four-eyes approval, the `repair_reference` requirement for LEGAL_GRADE, and cross-tenant rejection; and the R-05 durable queue surviving restart.

**Acceptance:** each path has tests exercising both success and failure; no integrity code path ships to a customer untested.
**Effort:** 1 week *(estimate)*. **Depends on:** R-22, and the Phase 3 items whose behaviour they encode.

### R-24. Cover erasure, retention and RBAC
**Audit ref:** A4
**Problem:** Zero matches for erasure or retention tests across `tests/`. RBAC coverage is `test_protected_endpoints.py` at 92 lines, which is thin for a permission matrix. Erasure and retention are exactly the features a DPPA-conscious buyer will probe.

**Action:** a permission matrix test enumerating every route against every role, generated rather than hand-written so it cannot drift. Erasure tests proving personal data is removed while the chain remains verifiable, which is the hard case and the one worth demonstrating. Retention tests proving the statutory seven-year Tier 4 Act s.75(2) schedule is enforced and that nothing is deleted early.

**Acceptance:** the matrix test fails when a new route is added without an explicit permission decision; erasure leaves a verifiable chain; retention refuses premature deletion.
**Effort:** 1 week *(estimate)*. **Depends on:** R-22.

### R-25. Cover documents, workflows and flows
**Audit ref:** A4
**Problem:** `test_document_operations.py` is 41 lines against roughly 2,199 document and 2,168 flow lines.

**Action:** cover the document compliance engine (`get_flow_document_compliance`) thoroughly, since it is the piece worth keeping and selling, including `all_satisfied` and `blocked_reasons` across requirement permutations. Cover document versioning and the R-06 chain events.
**Scope note:** if R-31 deletes workflow automation, do not write tests for it first. Sequence R-31's decision ahead of this item.

**Acceptance:** the compliance engine has full branch coverage on requirement satisfaction logic.
**Effort:** 4 days *(estimate)*. **Depends on:** R-22, R-06, R-31 decision.

---

## Phase 6 — Scale and cost

### R-26. Make tenant verification streaming rather than in-memory
**Audit ref:** P3
**Problem:** `_fetch_all_events_for_tenant` loads every event for a tenant into memory in 500-row batches, then sorts and groups (`verification_service.py:80-95`). Guards exist (`:151-160`) but the failure mode is a hard ceiling, not graceful degradation. At 10M events this is impossible, not slow.

**Action:** verify per subject chain in a streaming pass, ordered by the database, with bounded memory independent of tenant size. Make tenant-level verification an aggregation over per-subject results, resumable and checkpointed.

**Acceptance:** a load test verifies a tenant with 10M events within bounded memory; verification is resumable after interruption.
**Effort:** 1 week *(estimate)*. **Depends on:** R-09.

### R-27. Fetch Merkle proofs in one query
**Audit ref:** P3
**Problem:** `generate_proof` issues one database round-trip per tree level (`merkle_service.py:116`, acknowledged at `:91-92`), roughly 24 sequential queries at 10M leaves.

**Action:** fetch the full sibling path in a single query, by recursive CTE or by storing the path.
**Acceptance:** proof generation issues one query regardless of tree depth, asserted by a query-count test.
**Effort:** 3 days *(estimate)*. **Depends on:** R-12.

### R-28. Batch Merkle node writes
**Audit ref:** P3
**Problem:** `build_and_store` writes every node one INSERT at a time in a Python loop (`merkle_service.py:200-212`), roughly 2N sequential round-trips per epoch of N leaves.
**Action:** bulk insert.
**Acceptance:** a query-count test proving node writes are constant in round-trips, not linear.
**Effort:** 2 days *(estimate)*. **Depends on:** R-12.

### R-29. Make anchoring concurrent and failure-isolated
**Audit ref:** P3
**Problem:** `anchor_job` iterates tenants serially with a fresh session each, making a synchronous external TSA HTTP call per tenant (`anchor_job.py:53-56`). At 100 tenants with a 10s TSA timeout, a single failing TSA stalls the loop for roughly 17 minutes.

**Action:** bounded concurrency across tenants, per-tenant timeouts, a circuit breaker on the TSA client, and a dead-letter path so one tenant's failure never delays another's anchor. Add a configurable secondary TSA and fail over to it.

**Acceptance:** a test with a deliberately hanging TSA proves other tenants still anchor on time; failures land in a retry queue with alerting.
**Effort:** 4 days *(estimate)*. **Depends on:** R-05.

### R-30. Model and cap TSA cost
**Audit ref:** P3
**Problem:** LEGAL_GRADE seals every 15 minutes or 100 events **per subject**. At 100 tenants with 1,000 subjects each, that is 100,000 epoch seals per 15-minute window at the interval bound, each a TSA call plus a full Merkle rebuild. Commercial TSAs charge per timestamp. Nobody has modelled this.

**Action:** build the cost model per profile before any LEGAL_GRADE tier is sold. Batch multiple subject roots into a single timestamped root so cost scales with time rather than with subject count. Add per-tenant anchor budgets with alerting, and price the tier from the model.

**Acceptance:** a written cost model per profile at 10, 100 and 1,000 tenants; anchoring cost per tenant is bounded and alertable; no tier is offered commercially without a model behind it.
**Effort:** 4 days *(estimate)*. **Depends on:** R-11, R-13.

---

## Phase 7 — Deletion

### R-31. Delete unvalidated surface area
**Audit ref:** P5
**Problem:** 43,552 lines, 39 tables, 467 files, with roughly a quarter deletable without a first paying customer noticing. Every retained line is maintenance tax and pivot drag.

**Sequencing rule: do not delete before Phase 0 discovery answers what the buyer needs, and do not harden in Phase 4 what you intend to delete here.** Two items in this plan explicitly wait on this decision (R-21, R-25).

| Candidate | Approx. lines | Decision rule |
|-----------|---------------|---------------|
| Email ingestion, Gmail/Outlook/IMAP, plus OAuth provider config | ~3,364 | Delete unless discovery finds a buyer who ingests loan correspondence by email. Largest single block, and it drags in `msal`, `google-api-python-client`, envelope encryption, KDF salt files, OAuth state tables, a webhook endpoint and token refresh |
| `app/pages`, server-rendered pages | 1,549 | **Delete unconditionally.** A second presentation layer beside the React SPA, with no scenario in which both are wanted |
| Projections engine | ~1,171 | Delete unless the loan balance projection from the money-lender product build reuses it. **Check before deleting**, since balance computation is exactly what that vertical needs |
| Workflow automation, create_event / create_task / notify | ~1,335 | Delete unless discovery finds a needed automation. Keep the document-compliance engine, which is separate |
| Webhooks | ~822 | Delete unless a named integration requires callbacks |
| Analytics and search | ~571 | Delete, plus the full-text migration and its two triggers (`r5s6t7u8v9w0`) |
| Kafka, CDC, file-watch connectors | ~528 | **Delete unconditionally.** Self-labelled pending (`lifespan.py:193`), scaffolding for integrations no buyer has requested |
| Websockets | ~110 plus `ConnectionManager` | **Delete unconditionally.** `broadcast_to_tenant` is a placeholder comment (`websocket.py:97-98`) |
| Chain repair | ~365 plus endpoints and table | **Do not delete without a decision.** Fixed in R-14. Delete only if discovery shows no buyer needs a repair path |
| LEGAL_GRADE and Merkle | ~328 plus tables | **Do not delete.** R-11 makes tenant anchoring depend on the Merkle construction. Superseded by the fix |

**Acceptance:** each deletion is a separate reviewable commit with its migration; the suite is green after each; no dead configuration, dependency or table is left behind; `pyproject.toml` extras are pruned to match.
**Effort:** 1 week *(estimate)*. **Depends on:** Phase 0 discovery outcome, R-11, R-14.

---

## Phase 8 — Compliance and external validation

### R-32. Register with the PDPO and build consent capture
**Audit ref:** A6
**Problem:** DPPA 2019 s.29(2) requires the PDPO to register every person or institution collecting or processing personal data, and no registration exists. DPPA 2019 s.19 requires that processing or storing personal data outside Uganda have "at least equivalent" protection or data-subject consent, and there is **no consent-capture mechanism at all**.
**Source caveat:** these section numbers are secondary-sourced. NITA-U returned HTTP 404 and ULII returned HTTP 403 during the audit. **Confirm against the Gazette before relying on them contractually.**

**Action:** verify the sections against the Gazette; register with the PDPO; build consent capture and per-subject consent records where any processing remains extraterritorial after R-04, including the third-party TSA; document the lawful basis for every processing activity; publish a retention and erasure policy matching what R-24 tests enforce.

**Acceptance:** registration certificate obtained; a documented processing inventory; consent records exist for any extraterritorial processing; section numbers confirmed against primary text.
**Effort:** 1 week plus external lead time *(estimate)*. **Depends on:** R-04.

### R-33. Build genuine independent verification
**Audit ref:** P0-4, P0-5
**Problem:** Three compounding failures. The verify page requires login (`verify/$subjectId.tsx:33`, `requireAuthBeforeLoad()`). The headline endpoint `/integrity/verify/{subject_id}` is documented "events only, no TSA/Merkle" (`integrity.py:90`), so it never checks an anchor. And events, Merkle nodes and TSA receipts all come from the same database being verified, with no external log, mirror or bulletin board, so a server that rewrites history serves a self-consistent new world.

**Action:** three parts, all required.
1. A genuinely unauthenticated verification route, rate-limited per R-15, that exposes only what verification needs and no personal data.
2. Make verification check the TSA anchor and the Merkle inclusion proof, not just event linkage.
3. Publish sealed epoch roots and TSA receipts to an append-only location **outside the application database**, so verification does not rest on the artefact being verified. A daily digest to an independent third party is the minimum acceptable form. Ship an **offline verifier**: a standalone script that takes an exported record pack and validates it against a published root with no access to your servers at all. For the money-lender vertical this is the court-pack artefact, and it is what makes the s.88(1) plus ETA s.7-8 argument real rather than rhetorical.

**Acceptance:** a third party with no credentials can verify a record; verification fails if the anchor is missing or wrong; the offline verifier validates an exported pack on a machine with no network access to your infrastructure.
**Effort:** 2 weeks *(estimate)*. **Depends on:** R-11, R-12, R-13.

### R-34. Commission an external security and cryptographic review
**Audit ref:** A1, C3.5 in `CFO-FINANCIAL-ASSESSMENT.md`
**Problem:** No BoU-supervised institution and no international sponsor will onboard an unaudited single-founder vendor holding regulated records. The CFO estimates USD 15,000 to 40,000 for this, roughly a full year of runway, and flags it as the item that breaks the financial model. HR's guidance is to **buy this as a service and never hire an applied cryptographer**, since the primitives are standardised.

**Action:** commission an independent review once Phases 2 to 4 are complete, scoped to the integrity construction, the multi-tenant isolation model, key management, and the R-33 verification path. Take a scoping call early, before the work is finished, so the design is reviewed rather than only the implementation.

**Acceptance:** a written report; all critical and high findings closed; the report is presentable in a buyer's vendor due diligence pack.
**Effort:** external, 2 to 6 weeks lead *(estimate)*. **Depends on:** Phases 2, 3, 4.
**Commercial note:** do not commission this before the 90-day gates clear. It is the single largest cash item in the plan and it is worthless without a buyer.

---

## Dependency map

```
R-01 ─┬─> R-04 ──> R-05 ─┬─> R-13 ──> R-30
      │        │         └─> R-29
      │        ├─> R-15
      │        ├─> R-19
      │        ├─> R-21
      │        └─> R-32
      └─> R-16

R-02 ──> R-07 ─┬─> R-09 ─┬─> R-08
               │         ├─> R-10
               │         └─> R-26
               ├─> R-06
               ├─> R-14
               └─> R-18

R-12 ─┬─> R-11 ──> R-13 ──> R-33 ──> R-34
      ├─> R-27
      └─> R-28

R-22 ──> R-23, R-24, R-25

No dependencies, start any time: R-12, R-17, R-20, R-22
```

**Critical path:** R-01 → R-04 → R-05 → R-07 → R-08 → R-11 → R-13 → R-33 → R-34.

## Effort summary

| Phase | Weeks *(estimate)* |
|-------|--------------------|
| 0. Ground truth | 0.5 |
| 1. Claim containment | 0.2 |
| 2. Platform and residency | 3-4 |
| 3. Integrity correctness | 5-6 |
| 4. Security hardening | 2 |
| 5. Test backfill | 2 |
| 6. Scale and cost | 2 |
| 7. Deletion | 1 |
| 8. Compliance and validation | 2 plus external |
| **Total** | **approximately 17-20 engineer-weeks** |

Excludes the money primitives, receipt generation and court-pack work the money-lender vertical requires, estimated separately at 10 to 14 weeks in `CTO-TECHNICAL-AUDIT.md`. **The two overlap**: R-33's offline verifier is the court-pack artefact, so building the vertical after this plan is cheaper than the two estimates summed.

## Standing rules

1. **No item is complete without the tests named in its acceptance criteria.** Coverage at 8.4% is how contradictory facts survived unnoticed in the first place.
2. **No outward claim may exceed what has shipped.** R-03's claim statement is updated as items land, never ahead of them.
3. **Do not harden what Phase 7 will delete.** R-21 and R-25 explicitly wait on R-31's decision.
4. **Every estimate here is an estimate**, not a measured figure, and none is based on observed velocity on this codebase.
5. **Phases 2 onward remain frozen** until the `COO-DECISION.md` 90-day gates clear or the freeze is deliberately overridden. Phases 0 and 1 are exempt and should proceed now.
