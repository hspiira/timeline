# CTO Technical Audit: `timeline` / `timeline-ui`

**Date of audit:** 2026-08-29
**Method:** read-only. No files modified. Test suite deliberately not run (see [Test coverage](#test-coverage-reality)).
**Scope:** `timeline/` (FastAPI backend, ~43,552 lines app code, 467 files, 39 tables) and `timeline-ui/` (React 19 SPA, ~47 routes).

## How to read this document

Every claim carries a `file:line` citation. Claims without one are labelled as inference or estimate.

Uganda regulatory claims are secondary-sourced where the primary host was unreachable, and are labelled accordingly. The Tier 4 Act sections in [Vertical analysis](#vertical-analysis) are primary, extracted from the UMRA-published PDF.

Severity levels used in the backlog:

| Level | Meaning |
|-------|---------|
| **P0** | Blocks any sale to a regulated buyer, or the product claim is untrue as shipped |
| **P1** | Security or correctness defect that survives to production |
| **P2** | Integrity design weakness. Not exploitable today, undermines the guarantee under scrutiny |
| **P3** | Scale and cost. Breaks at volumes below what the roadmap assumes |
| **P4** | Test coverage gaps on critical paths |
| **P5** | Deletion candidates. Unvalidated surface area carrying maintenance tax |

---

## Executive summary

1. The integrity story is half-built and **shipped off by default**. `epoch_sealing_enabled`, `chain_anchor_enabled` and `tsa_batch_enabled` all default `False` (`app/core/config.py:99,105,107`). Out of the box there is no external anchoring at all.
2. When enabled, epoch sealing is genuinely sound: per-subject Merkle root, TSA-anchored, refuses to seal without it (`app/core/epoch_sealing_job.py:127-141`). This is the best code in the repo.
3. The other anchoring path, `AnchorChainTipsUseCase`, anchors one arbitrary subject's tip per tenant (`app/infrastructure/persistence/repositories/event_repo.py:398-407`) and proves nothing about any other subject.
4. All anchoring runs in `while True` background loops that **cannot execute on Vercel serverless**. The declared deploy target structurally cannot run the feature the product sells.
5. Three code paths issue `UPDATE event`; a DB trigger unconditionally forbids it (migration `i9j0k1l2m3n4`). Either the trigger is not deployed, or chain repair and COMPLIANCE anchoring raise at runtime. Both cannot be true.
6. The public third-party verification pages **require login** (`apps/web/src/routes/verify/$subjectId.tsx:34`). Independent verification does not exist today.
7. **Tenant isolation is the strongest part of the system.** FORCE RLS on all 39 tables, plus an app-layer check on 158 call sites. No cross-tenant leak found. Residual risk is outage, not leak.
8. No Ugandan regulator mandates cryptographic tamper-evidence anywhere. The cryptography is not the purchase trigger. The mandated record set, retention and court production are.
9. **Codebase production readiness: 4/10. Business idea technical merit and defensibility: 3/10.**

---

## Remediation backlog

### P0: blocks any sale to a regulated buyer

#### P0-1. Resolve the RLS / anchoring contradiction

Two facts in this codebase cannot both be false:

> Either RLS is live and all integrity anchoring is silently dead, or the anchoring works and the app role bypasses RLS, meaning tenant isolation has no database layer at all.

All three background jobs open `AsyncSessionLocal()` with no tenant context, and none of the three files contains any call to `apply_tenant_context` / `set_tenant_id`:

- `app/core/anchor_job.py:50` calls `get_distinct_tenant_ids()`, a cross-tenant scan
- `app/core/tsa_batch_job.py:88`
- `app/core/projection_engine_job.py:38`

Under working FORCE RLS with no session variable set, every policy evaluates NULL, and these jobs see zero rows and write nothing, silently.

**Diagnostic, run as the app role:**

```sql
SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user;
```

This is read-only and does not count as feature work under a build freeze. **Do this first.** Everything else in the integrity backlog depends on knowing which of the two worlds you are in.

#### P0-2. The integrity claim is not true as shipped

| Flag | Default | File |
|------|---------|------|
| `epoch_sealing_enabled` | `False` | `app/core/config.py:99` |
| `chain_anchor_enabled` | `False` | `app/core/config.py:105` |
| `tsa_batch_enabled` | `False` | `app/core/config.py:107` |

Integrity profile behaviour (`app/application/integrity_config.py:25-46`):

| Profile | Seal interval | TSA | Merkle | Unanchored attack window |
|---------|---------------|-----|--------|--------------------------|
| STANDARD | 24h / 10,000 events | off | off | **unbounded, no anchoring ever** |
| COMPLIANCE | 1h / 1,000 events | on | off | up to 1h or 1,000 events |
| LEGAL_GRADE | 15m / 100 events | on | on | up to 15m or 100 events |

**The attack that breaks the marketing claim:** an operator with database access, against a STANDARD tenant (the default) or any tenant during an unsealed window, rewrites payloads, recomputes the chain forward, and deletes superseded `chain_anchor` rows. Every verification endpoint returns green.

**Action:** either fix the product or narrow the written claim to what `epoch_sealing_job.py:127-141` actually delivers. That path is real. Do not put the broader claim in a contract, a pitch deck, or a demo script until it holds. A customer relying on this in court, with opposing counsel discovering anchoring was off, is a fraud-exposure risk, not a bug.

#### P0-3. Documents have no tamper-evidence at all

`app/application/use_cases/documents/document_operations.py` computes a SHA-256 (`:67-72, :147`) and stores it in the `document` table. It contains **no `create_event` call**.

Documents are entirely outside the hash chain. Replace the file, update the checksum column, nothing detects it. For a product whose second pillar is documents with categories and per-workflow requirements, this is a hole in the core claim.

**Action:** emit a `DOCUMENT_ATTACHED` event carrying the checksum into the subject's chain on every upload, and a `DOCUMENT_REPLACED` / `DOCUMENT_DELETED` event on mutation.

#### P0-4. Public verification requires authentication

`apps/web/src/routes/verify/$subjectId.tsx:34` gates the verification page behind login.

Independent third-party verification is the reason a buyer would choose this product. It does not currently exist.

Compounding this, `/integrity/verify/{subject_id}` is documented "events only, no TSA/Merkle" (`app/api/v1/endpoints/integrity.py:90`). The headline verification endpoint never checks an anchor.

**Action:** a genuinely unauthenticated verification route that checks the TSA anchor, plus rate limiting that survives the deploy target (see P1-1).

#### P0-5. Verification is not independent of the server

Three separate reasons, all of which must be fixed for the claim to mean anything:

1. The verify pages require login (P0-4)
2. The headline endpoint does not check anchors (P0-4)
3. Events, Merkle nodes and TSA receipts all come from **the same database being verified**

There is no external log, mirror, or bulletin board. A server that rewrites history serves a self-consistent new world with no old anchors to contradict it.

**Note on keys:** there are no signing keys anywhere in the cryptographic sense. The TSA holds its own key; the platform holds the receipt. Credential encryption derives from an env var falling back to `SECRET_KEY` (`app/infrastructure/external/email/encryption.py:22-38`), so the JWT signing secret doubles as the credential encryption key. No KMS, no HSM.

**Action (minimum viable):** publish sealed epoch roots and TSA receipts to an append-only location outside the application database. Even a daily digest to a third party is a material improvement over self-attestation.

#### P0-6. Vercel serverless cannot run this product

`vercel.json` declares `"framework": "fastapi"`; `app/index.py` is the zero-config entrypoint. Against that, `app/core/lifespan.py:104-110` starts four `asyncio.create_task` background loops, each an infinite `while True` with `asyncio.sleep`.

| Component | Why it breaks on serverless |
|-----------|------------------------------|
| Epoch sealing (`epoch_sealing_job.py`) | `while True` loop, no long-lived process. **The integrity guarantee dies here** |
| Chain anchoring (`anchor_job.py:43`) | Same, plus a 30s startup delay exceeding typical function lifetime |
| TSA batch (`tsa_batch_job.py:49,64`) | Same, and it drains `DEFAULT_TSA_BATCH_QUEUE`, a process-local, non-durable in-memory list (`tsa_batch_queue.py:23-30`, self-documented "Not durable"). Enqueued on the write path, lost when the invocation ends. COMPLIANCE events never get anchored |
| Projection engine (`projection_engine_job.py`) | Same |
| Websockets (`websocket.py`, `ConnectionManager`) | Serverless cannot hold connections. `broadcast_to_tenant` is a placeholder comment anyway (`websocket.py:97-98`) |
| Email polling (`connector_email_poll_interval_seconds: 60.0`) | Same |
| Rate limiting | In-memory, per-invocation (see P1-1) |
| Local file storage | Ephemeral filesystem (see P1-2) |

This is not tunable. It requires a re-platform.

**Action:** re-platform to a long-lived process host. Estimated 3 to 4 weeks (CTO estimate, not measured). Because DPPA 2019 s.19 also pushes toward Ugandan hosting, **re-platform once, not twice.** See [Uganda regulatory](#uganda-regulatory-layer).

#### P0-7. Three UPDATE paths contradict the append-only trigger

Migration `i9j0k1l2m3n4:65-77` puts `BEFORE UPDATE OR DELETE ... RAISE EXCEPTION` triggers on `event` and `audit_log`. Three application code paths issue `UPDATE event` regardless, including chain repair and COMPLIANCE anchoring.

Either the trigger is not deployed in your environment, or those paths raise at runtime. This is the same class of unknown as P0-1: **nobody currently knows which is true in production.**

**Action:** verify trigger deployment, then reconcile. If the trigger is correct, the UPDATE paths need redesign.

---

### P1: security and correctness defects reaching production

#### P1-1. Rate limiting does not exist in production

`Limiter(key_func=get_remote_address)` plus a module-level `defaultdict` (`app/core/limiter.py:16,32-48`). On serverless every invocation is a fresh process.

**Login brute-force protection does not exist in production.**

Also unverified: whether Vercel's proxy passes a usable client IP to `get_remote_address`, or whether it sees the proxy IP. Confirm against current Vercel and SlowAPI documentation before relying on any rate-limit behaviour.

#### P1-2. File storage and encryption salt are ephemeral

| Finding | Evidence |
|---------|----------|
| `storage_backend: "local"`, `storage_root: "./storage"`. Uploads vanish between invocations unless S3 is configured | `app/core/config.py:64-65` |
| `EnvelopeEncryptor` writes a generated KDF salt to `storage_root/.encryption_kdf_salt` if unset. On serverless this differs per invocation, making credentials **undecryptable on the next request** | `app/infrastructure/security/envelope_encryption.py:36-45` |
| Credential encryption falls back to `SECRET_KEY`. Rotating the JWT secret destroys every stored OAuth credential simultaneously | `app/infrastructure/external/email/encryption.py:25-29` |
| No KMS or HSM anywhere. Key material is an environment variable | (inference from absence) |

#### P1-3. File upload accepts anything

`allowed_mime_types: "*/*"` default, 100MB limit (`app/core/config.py:72-73`), and the MIME type is taken from the client's `content_type` with no server-side sniffing (`app/api/v1/endpoints/documents.py:86,95`).

Filename sanitisation itself is sound: `os.path.basename` plus null-strip plus reserved-name rejection (`document_operations.py:52-64`).

#### P1-4. The RLS safeguard is inert in production

`app/infrastructure/persistence/rls_check.py:75-86` asserts the app role lacks `BYPASSRLS`. It is wired to `/health/ready`, and `rls_check_policies` defaults `False` (`config.py:127-129`; `_core.py:83-102`).

**Vercel does not poll readiness endpoints.** The safeguard never runs.

**Action:** move it to startup and default it on.

#### P1-5. `X-Tenant-ID` takes precedence over the JWT

`app/middleware/tenant_context.py:20-33` prefers the unauthenticated, attacker-controlled header over the JWT. `get_tenant_id` (`_core.py:222-265`) validates format and existence but never checks the user belongs to that tenant.

This **stops** at `require_permission:738`, and `get_current_user_optional` loads the user via `get_by_id_and_tenant(user_id, tenant_id_from_JWT)` (`:628`) under RLS context B, so under live RLS the lookup returns nothing and the request 401s first.

Correct today, but it is the same check twice, in two places, both of which must hold.

**Action:** invert the precedence so the JWT wins. Costs nothing, removes the entire class.

#### P1-6. Missing tenant predicates on two write paths

| Issue | Evidence | Risk |
|-------|----------|------|
| `mark_event_integrity_status` has no tenant predicate, `.where(Event.id == event_id)` only | `event_repo.py:300-309` | Cross-tenant write primitive if RLS is ever off |
| `complete_repair(repair_id)` takes no `tenant_id` and performs no tenant check, unlike `approve_repair` which does (`:201`) | `chain_repair_service.py:219-236` | Same |

Both are reachable only under RLS protection. Given P0-1 is unresolved, that protection is unconfirmed.

#### P1-7. Session and transaction handling defects

| Issue | Evidence | Risk |
|-------|----------|------|
| `_set_tenant_context` silently returns when tenant context is unset | `app/infrastructure/persistence/database.py:97-99` | Fail-closed for reads (`current_setting(...,true)` returns NULL, no rows) and writes (WITH CHECK fails). Outage, not leak |
| `get_db` runs `SET LOCAL` outside an explicit transaction, relying on SQLAlchemy autobegin | `database.py:110-127` | Code comments show this **has already broken in production**: "which it did, on both the API and the seed scripts, with nothing covering it" (`create_event.py:150-151`) |
| `_release_ambient_transaction` rolls back the caller's session | `create_event.py:138-171` | Latent data loss for any future caller that writes first |
| One global `EMAIL_WEBHOOK_SECRET` shared across all tenants | `email_accounts.py:255-261` | Low. `get_by_id_and_tenant` still scopes |

#### Not a defect, verified

`SET LOCAL` f-string interpolation (`database.py:107`, `auth.py:91`) is **not injectable**. Both are gated on `is_valid_tenant_id_format`, a `^[a-zA-Z0-9_-]{1,64}$` fullmatch (`tenant_validation.py:11-20`), plus quote-doubling. Correct, if uncomfortable to read.

---

### P2: integrity design weaknesses

#### P2-1. What the hash does not cover

`app/application/services/hash_service.py:47-66` covers exactly six fields: `subject_id`, `event_type`, `schema_version`, `event_time`, `payload`, `previous_hash`.

| Not covered | Consequence |
|-------------|-------------|
| `tenant_id` | An event moved between tenants still verifies clean |
| `event_seq` | Sequence is not committed to. Ordering rests only on `previous_hash` links |
| actor / `created_by` | **Who created the record is not tamper-evident.** Re-attribution is undetectable |
| server receipt time | Only user-supplied `event_time` is hashed. Backdating is invisible until the next TSA anchor |
| document checksum | See P0-3 |

The actor omission is the one to fix first. In a court-production scenario, "who entered this" is exactly what gets challenged.

#### P2-2. Tenant-tip anchoring proves almost nothing

`AnchorChainTipsUseCase.run_for_tenant` (`app/application/use_cases/anchoring/anchor_chain_tips.py:55`) calls `get_chain_tip_hash(tenant_id)`, which is `ORDER BY event_seq DESC LIMIT 1` across the whole tenant (`event_repo.py:398-407`).

Each subject has an independent chain. That anchor commits only to whichever subject happened to write last.

`chain_anchor.subject_tips` and `event_count` exist for exactly this fix, are labelled "Option C (Merkle) readiness" (`app/infrastructure/persistence/models/chain_anchor.py:6`), and are read in `_to_result` (`chain_anchor_repo.py:38-39`) but **never written by any code**.

**Action:** either populate `subject_tips` with a Merkle root over all subject tips, or remove this path and rely solely on per-subject epoch sealing, which is correct.

#### P2-3. Merkle implementation weaknesses

`app/application/services/merkle_service.py:183-198`:

| Weakness | Detail |
|----------|--------|
| **Odd-node duplication** (`right_hash = left_hash`, `:190`) | The CVE-2012-2459 shape. Leaf sets `[A,B,C]` and `[A,B,C,C]` produce an identical root. The root does not commit to leaf count |
| **No domain separation** (`:191-192`, plain `left+right` concatenation) | RFC 6962 prefixes leaves `0x00` and internal nodes `0x01` precisely to prevent presenting an internal node as a leaf |
| **Rebuild replaces silently** | `build_and_store` calls `delete_for_epoch` then rebuilds (`:176`) |

**Action:** adopt RFC 6962 construction. This is a well-specified standard and the fix is mechanical.

#### P2-4. Two functions disagree on what "verify" means

`VerificationService._verify_event` (`app/application/services/verification_service.py:243-320`) genuinely recomputes the hash from stored fields and compares (`:285-296`), then checks the `previous_hash` link. Genesis is checked for a null `previous_hash` (`:299-304`). Head-truncation is caught. Tail-truncation is not, which is what anchoring is for. **This is correct.**

`ChainRepairService.detect_and_flag` (`app/application/services/chain_repair_service.py:134-153`) **only** compares `ev.previous_hash != last_hash` and never recomputes. A payload edited without touching the hash column passes it clean.

**Action:** `detect_and_flag` should call the same verification primitive.

#### P2-5. Chain repair: the docstring is wrong and dangerous

`complete_repair` (`chain_repair_service.py:219-320`) docstring says "Re-hash from break". **It does not re-hash anything.** It opens a new epoch from the last good hash, appends a `CHAIN_REPAIR` event, and marks the broken tail `REPAIRED`. History is abandoned, not rewritten.

That is the correct design choice. The docstring describes a different, far more dangerous operation, and anyone reading it will draw the wrong conclusion about the guarantee.

Guardrails present: four-eyes approval (`:206-207`), `repair_reference` mandatory for LEGAL_GRADE (`:171-172`), tenant ownership checked in `approve_repair` (`:201`).

Guardrail missing: see P1-6.

**Action:** fix the docstring. It is a one-line change with outsized value.

---

### P3: scale and cost

Problems arrive earlier than volume suggests. At 10 tenants nothing hurts.

| Issue | Evidence | Breaks at |
|-------|----------|-----------|
| `_fetch_all_events_for_tenant` loads **every event for a tenant into memory** in 500-row batches, then sorts and groups. `max_events` and `timeout_seconds` guards exist (`:151-160`) but the failure mode is a hard limit, not graceful degradation | `verification_service.py:80-95` | 10M events: impossible, not slow |
| `MerkleService.generate_proof` issues one DB round-trip per tree level, acknowledged at `:91-92` | `merkle_service.py:116` | ~24 sequential queries at 10M leaves |
| `build_and_store` writes every node one INSERT at a time in a Python loop | `merkle_service.py:200-212` | ~2N sequential round-trips per epoch of N leaves |
| `anchor_job` iterates tenants **serially**, fresh session each, each making a synchronous external TSA HTTP call | `anchor_job.py:53-56` | 100 tenants with a 10s TSA timeout: one failing TSA stalls the loop ~17 minutes |

#### The cost line nobody has modelled

LEGAL_GRADE seals every 15 minutes or 100 events **per subject**. At 100 tenants with 1,000 subjects each, that is 100,000 epoch seals per 15-minute window at the interval bound, each a TSA HTTP call plus a full Merkle rebuild.

Commercial TSAs charge per timestamp. **Model this before selling a LEGAL_GRADE tier.** Serverless invocation-seconds for background polling loops, if forced into cron functions, is the second surprise.

---

### P4: test coverage reality

3,649 test lines against 43,552 app lines is **8.4%**. The distribution is smarter than the headline, but the gaps map almost exactly onto the features you would demo to a regulated buyer.

| Critical path | Covered | Evidence |
|---------------|---------|----------|
| Tenant isolation | **Yes, well** | `tests/integration/test_tenant_isolation.py` (205 lines). The `rls_session` fixture **asserts the test role cannot bypass RLS** (`conftest.py:118-127`), so these tests cannot pass with policies dropped. Includes `test_every_tenant_scoped_table_has_a_policy` (`:167`) |
| Hash chain integrity | **Yes** | `test_event_chain_integrity.py` (200 lines): trigger enforcement, edited-payload detection, concurrent-append fork safety |
| Merkle | **Yes** | `test_merkle_service.py` (294 lines) |
| Hash service | Yes | `test_hash_service.py` (107 lines) |
| Auth, password reset, hardening | Yes | 3 files, 493 lines |
| **TSA anchoring / RFC 3161** | **No** | no test file |
| **Epoch sealing** | **No** | no test file |
| **Chain repair** | **No** | no test file. The highest-risk code in the system is untested |
| **RBAC / permission matrix** | **Thin** | `test_protected_endpoints.py`, 92 lines |
| **Erasure / retention** | **No** | zero matches across `tests/` |
| **Documents / workflows / flows** | **Near-zero** | `test_document_operations.py`, 41 lines, against ~2,199 document and ~2,168 flow lines |

#### Why the suite was not run

`.env` exists, `Settings` loads `env_file=".env"` (`config.py:175-177`), and `tests/conftest.py` executes `CREATE ROLE` and `GRANT USAGE, SELECT ON ALL SEQUENCES` against whatever `DATABASE_URL` that file contains (`conftest.py:85-89`). Running pytest would have written to a possibly-live database using production secrets.

**To run it safely:** point `DATABASE_URL` at a throwaway Postgres, run `alembic upgrade head`, then `uv run pytest`. Without `DATABASE_URL` all `requires_db` tests skip and you learn nothing about the paths that matter.

---

### P5: deletion candidates

Ranked by (maintenance tax) times (probability the first customer never asks for it). Roughly **11,000 to 12,000 lines, about 25% of the codebase**, none of which a first paying customer would notice.

| Delete | Approx. lines | Why |
|--------|---------------|-----|
| **Email ingestion (Gmail/Outlook/IMAP) + OAuth provider config** | ~3,364 | The single largest unvalidated block. Drags in `msal`, `google-api-python-client`, envelope encryption, KDF salt files, OAuth state tables, a webhook endpoint, token refresh counters. **Highest maintenance tax in the repo** |
| **`app/pages`, server-rendered pages** | 1,549 | You have a React SPA. This is a second, parallel presentation layer |
| **Projections engine** | ~1,171 | Two tables, a background job, six endpoints, a rebuild path. No consumer |
| **Workflow automation** (create_event / create_task / notify) | ~1,335 | Distinct from the document-compliance engine, which is worth keeping |
| **Webhooks** | ~822 | Nobody to call |
| **Analytics + search** | ~571 | Plus a full-text migration with two triggers (`r5s6t7u8v9w0`) |
| **Kafka / CDC / file-watch connectors** | ~528 | Self-labelled: "CDC, Kafka, and file_watch are pending" (`lifespan.py:193`). Scaffolding for integrations no named buyer has asked for |
| **Chain repair** | ~365 + endpoints + table | Untested, tenant-check gap, blocked by your own trigger, and it exists to fix a problem the append-only design should prevent. It is a hole in the guarantee that costs money to maintain |
| **LEGAL_GRADE / Merkle** | ~328 + tables | Keep epoch + TSA anchoring at COMPLIANCE. Merkle inclusion proofs serve a buyer who does not exist and carry the P2-3 weaknesses |
| **Websockets** | ~110 + `ConnectionManager` | Cannot run on the deploy target. `broadcast_to_tenant` is a placeholder comment |

#### Keep and invest in

The event and subject core, RLS and RBAC, the append-only triggers, the audit log, documents plus categories plus `get_flow_document_compliance`, retention, epoch sealing plus TSA at COMPLIANCE profile, and the verification service.

---

## What is genuinely strong

Recorded deliberately, because the backlog above reads as unrelieved criticism and that would be a false picture.

### Tenant isolation: no leak found

**Layer 1, RLS, complete.** Two migrations: `w1x2y3z4a5b6` (21 tables) and `d2e3f4g5h6i7` (13 direct, 4 indirect, dated 2026-08-11). The second applies `FORCE ROW LEVEL SECURITY` **catalogue-driven rather than from a hardcoded list** (`d2e3f4g5h6i7:66-78`), explicitly because "without FORCE a table's owner silently bypasses its own policies". All 39 `__tablename__` declarations were enumerated against the covered sets: **coverage is complete.** Indirect tables (`merkle_node`, `password_set_token`, `flow_subject`, `projection_state`) get `EXISTS` policies against the parent's `tenant_id` (`:88-97`).

**Layer 2, application check.** `require_permission` (`app/api/v1/dependencies/_core.py:730-745`) enforces `current_user.tenant_id != tenant_id` returns 403. Graft shows **158 incoming edges**: it is on essentially every route. `get_enrichment_context` repeats the check (`:719-720`). Path-tenant routes use `get_verified_tenant_id` (`:268-274`).

**Layer 3, DB triggers.** `event` and `audit_log` are append-only at the database level (`i9j0k1l2m3n4:65-77`).

**Layer 4, readiness check** asserting the app role lacks `BYPASSRLS` (`rls_check.py:75-86`), with pooler-username handling for Supabase-style `postgres.abcdefgh` roles. Currently inert in production: see P1-4.

### Auth and secrets: no findings

- JWT: HS256, `algorithms` pinned, `require: ["exp","sub"]`, token-type check so a refresh token cannot be presented as an access token (`app/infrastructure/security/jwt.py:104-113`)
- Passwords: bcrypt with SHA-256 pre-hash to defeat the 72-byte truncation (`password.py:15,32-34`), dummy-hash comparison against user enumeration (`user_repo.py:28`)
- Secrets typed `SecretStr`. `SECRET_KEY` required at startup (`config.py:189-191`)
- The three apparently unguarded routes are each protected by an alternate mechanism: `create_tenant` by a shared-secret header (`tenants.py:66-72`), the email webhook by HMAC-SHA256 with `hmac.compare_digest` (`email_accounts.py:225,258`), the websocket by JWT in `Sec-WebSocket-Protocol` (`websocket.py:66-88`)

### Epoch sealing

`_seal_one_epoch` (`epoch_sealing_job.py:127-141`) builds the Merkle root, anchors `merkle_root or terminal_hash` to the TSA, and **raises rather than sealing without it** (`:88, :107`). Per subject, per epoch. This is the design the product should be sold on.

### Honest code comments

The comments document real production incidents rather than hiding them (`create_event.py:150-151`). That is a cultural asset and it is rarer than it should be.

---

## Uganda regulatory layer

All claims stamped **as of 2026-08-29**. The primary NITA-U PDF returned HTTP 404 and ULII returned HTTP 403, so **DPPA section numbers below are from converging Ugandan legal-practice secondary sources and must be verified against the Gazette before appearing in any contract.**

| Obligation | What the architecture does | Gap and action |
|------------|---------------------------|----------------|
| **DPPA 2019 s.29(2)**: the PDPO registers every person or institution collecting or processing personal data | Nothing. No registration | **Register with the PDPO before the first customer.** Penalty for non-registration reported as approximately UGX 120,000 and/or up to 3 months imprisonment. *Verify this figure, it is secondary-sourced* |
| **DPPA 2019 s.19**: processing or storing personal data outside Uganda requires the destination country to have "at least equivalent" protection, or data-subject consent | **Directly violated by the current architecture.** Vercel, foreign-hosted Postgres and a third-party TSA are all extraterritorial. The system has **no consent-capture mechanism at all** | Either obtain and record per-data-subject consent, demonstrate adequacy to the PDPO, or host in Uganda |
| DPP Regulations 2021 (SI, 12 Mar 2021): records producible to the PDPO on request | Audit log exists and is append-only (`i9j0k1l2m3n4`) | **Genuine asset.** The one place the architecture is ahead of the requirement |
| Data security | Bcrypt, Fernet, RLS, TLS | Adequate. Absence of a KMS is the weak point |
| **ETA 2011 ss.7-8** | Hash chain plus TSA is direct evidence for the s.7 integrity test | This is an **asset, not an obligation**. See below |

**Cost to fix:** PDPO registration is days and a nominal fee. Cross-border is the expensive one. Moving to Ugandan hosting means abandoning Vercel, which P0-6 requires anyway, and Uganda has thin managed-Postgres options, so expect self-managed Postgres on a local IaaS provider plus a part-time ops burden not currently staffed.

**NO VERIFIED SOURCE for a shilling figure.** No pricing data for Ugandan IaaS or PDPO fees was obtainable.

---

## Vertical analysis

### The finding that reframes the question

**No Ugandan regulator mandates cryptographic tamper-evidence.** UMRA, the NGO Bureau, IRA and PPDA all mandate *keeping* records, *producing* them and *retaining* them. None mandates *proving they were not altered*.

What Ugandan law does provide is **Electronic Transactions Act 2011 (Act 8 of 2011), ss.7-8**: the party adducing an electronic record bears the burden of proving its authenticity; the best-evidence rule is satisfied "upon proof of the authenticity of the electronic records system in or by which the data was recorded or stored"; and the s.7 integrity test is that the information "is complete and has not been altered."

So the product is not sold against a mandate. It is sold against an **evidentiary burden a specific buyer must discharge in court on a recurring, revenue-affecting basis.**

### Scoring

| Vertical | Engineering to first production | Mandate | Integration | Infra fit | Verdict |
|----------|-------------------------------|---------|-------------|-----------|---------|
| **Money lenders / non-deposit MFIs (UMRA)** | Medium. Needs money primitives, none exist | **Strongest available.** Tier 4 Act s.87 mandates the exact record fields, s.75(2) mandates 7-year retention, **s.88(1) requires producing those records in court to recover a loan** | Low-medium. s.8(2)(l) mandates a CRB reporting mechanism | Good. Branch office, mains or generator, laptop. Not field-based | **PICK** |
| **NGO / donor grant compliance** | **Lowest.** Document requirements, retention and audit log all built | Weak-medium. NGO Act 2016 mandates accounting records and annual returns. Donor audit trails are **contractual, not statutory** | Low. Donors accept exports | Good. Kampala offices | **RUNNER-UP** |
| Clinical trials / research (UNCST) | High. GCP/ALCOA+ needs e-signatures, CSV/GAMP5 validation | Strong in principle | High | Good | Best technical fit, unsellable market size and cycle |
| Insurance (IRA) | Medium | Insurance Act 2017 and Licensing and Governance Regs 2020 | High. Incumbent core systems | Good | Defer |
| Public procurement (PPDA) | Medium | Retention mandated | **High.** EGP already exists | Good | Slow government cycle |
| BoU-supervised institutions | High. Real core banking | Strong | Very high | Good | Out of reach pre-revenue |
| Coffee / cocoa EUDR | High | **Misdirected**, see below | High | **Fatal** | **KILL** |
| Land records | High | — | State monopoly (MLHUD/NLIS) | — | **KILL** |

### Why EUDR is killed

Confirmed via the European Commission's Access2Markets page: the amended EUDR applies from **30 December 2026** (large and medium operators, plus downstream operators and traders of all sizes) and **30 June 2027** (natural persons and micro-enterprises for remaining products), under **Regulation (EU) 2025/2650**, published in the Official Journal in December 2025.

Three reasons it still dies:

1. **The obligation sits on the wrong side of the ocean.** The due diligence statement is filed by the operator first placing goods on the EU market, the EU importer. The Ugandan cooperative is that importer's supplier, providing geolocation data *contractually*, not because any Ugandan regulator compels it.
2. **The 2025 amendment cut the surface further.** Downstream operators and traders now only retain the reference number of the initial declaration rather than filing their own.
3. **Infrastructure fit is fatal.** EUDR compliance is farm-plot geolocation capture by field agents. Uganda's electricity access is approximately 51.5% nationally and **42.4% rural** (2023, aggregator source). This system has **no offline mode whatsoever**: no service worker, no Workbox, no `vite-plugin-pwa`, no IndexedDB usage anywhere in `apps/web/src`. Building offline-first sync for a hash-chained append-only store is not a feature, it is a different product, because offline append means conflicting chain tips and there is no CRDT or merge story.

Sector context, from a UCDA monthly report already on disk (June 2026): Robusta exports 668,216 60-kg bags at USD 147.3M, Arabica 76,324 bags at USD 28.2M for the month, both down year-on-year (-23.9% and -26.8% by volume).

### Why money lenders wins

The Tier 4 Microfinance Institutions and Money Lenders Act 2016 provides a statutory record schema mapping onto this architecture almost line for line. **Extracted verbatim from the Act's own UMRA-published PDF:**

**s.87, Money lender to issue receipts and keep records:**

> "(1) A money lender shall issue a receipt to a borrower for every repayment made on a loan. (2) The receipt shall be issued immediately after the payment is made. (3) Every money lender shall keep a record which shall contain: (a) the date on which the loan was disbursed; (b) the amount of the principal; (c) the rate of interest; and (d) the sum repaid on the loan and the date on which the repayment is made."

That is an **event schema defined by statute**. `subject` = loan. Events = `LOAN_DISBURSED`, `REPAYMENT_MADE`. The `event_schemas` and `event_transition_rules` features exist for exactly this and have never had a real schema to hold.

**s.88(1), Powers of court:**

> "Where a money lender applies to court for the recovery of any money lent... the moneylender **shall produce the records referred to in section 87**."

**This is the commercial trigger.** The chain of reasoning:

> lender sues, s.88(1) compels production of s.87 records, ETA s.8 puts the authenticity burden on the lender, ETA s.7 defines integrity as "complete and not altered", and a hash chain with a TSA anchor is direct evidence of exactly that.

That is the only place in Uganda where this technology converts into money the buyer can count.

Supporting sections:

| Section | Provision | Maps to |
|---------|-----------|---------|
| s.75(1)-(2) | Proper books of accounts, inspectable "at anytime", kept **at least seven years** | The `retention` module finally has a statutory number |
| s.74 | Annual report to the Authority within 3 months of financial year end | Reporting |
| s.32 | Periodic reports as prescribed. Failure is an offence, fine up to 20 currency points | Reporting |
| s.31 | Supervision via audited accounts, statutory returns, record inspection | Audit log |
| s.9(1)(b) | Authority may "inspect and examine books of accounts, records, returns and any other document" | RBAC, export |
| s.8(2)(l) | Authority shall "establish a mechanism of reporting by tier 4 microfinance institutions to the Credit Reference Bureau" | **A named integration target.** A UMRA data submission portal exists at `reg.cisumra.com`, status and API unverified |

**Market size:** from the UMRA-published list of licensed institutions **as of March 2022**, approximately **408 non-deposit-taking MFIs, ~1,050 money lenders, ~46 SACCOs**. *These are counts derived from row numbering in that PDF, they are four years stale, and current figures must be verified with UMRA before use in any plan.*

**Infrastructure fit:** a money lender operates from a fixed trading-centre office with a laptop and a router, not a farm. Uganda internet penetration is approximately 22%, mobile network coverage reaches approximately 96% of the population, and UCC Q4 2025 figures report approximately 18.5M mobile internet subscriptions and 36.3M active mobile money users. *Secondary-source figures from aggregators and press coverage of a UCC report not directly opened. Indicative only.* This is the one candidate vertical where the missing offline mode is not disqualifying.

### The honest counterweight

The system has **no financial primitives at all.** Every persistence model was checked: there is not one `Numeric`, `Decimal`, `currency` or `amount` column. Money would live in untyped JSONB event payloads.

It can *record* a repayment. It cannot compute a balance, apply interest, age a portfolio, or produce a statement. **That is the real engineering bill.**

---

## Thinnest credible first product

**"Loan file of record" for a single licensed money lender.**

- `subject` = one loan. Event types `LOAN_DISBURSED`, `REPAYMENT_MADE`, `LOAN_CLOSED`, `WRITTEN_OFF`, with a JSON schema enforcing the four s.87(3) fields
- Receipt generation at the moment of repayment (s.87(1)-(2))
- Document requirements per loan: signed contract, borrower ID, collateral schedule
- COMPLIANCE integrity profile, epoch sealing and TSA anchoring **on by default**
- One killer artefact: **a printed, court-ready loan record pack**. The full s.87 record, every document, the epoch seal, the TSA receipt, and a plain-English page a magistrate can read explaining why it could not have been altered. That is the demo and that is the whole sale
- 7-year retention, RBAC, audit log

**Engineering estimate: 10 to 14 weeks**, one engineer, re-platform in parallel. *This is an estimate, not a measured figure.*

| Work | Weeks |
|------|-------|
| Re-platform off Vercel (non-negotiable, P0-6) | 3-4 |
| Money and decimal primitives, balance projection | 3 |
| Receipt and court-pack generation | 2 |
| Loan schema and document requirements | 1-2 |
| PDPO registration and data-residency work | 1-2 |
| Hardening the tested paths | 2 |

**Cut before starting:** everything in P5.

---

## The three technical risks that kill this company

1. **The integrity claim goes in writing before it is true.** Anchoring off by default, STANDARD tenants never anchored, "public verification" behind a login, documents outside the chain, tenant-tip anchor proving almost nothing. The first customer whose opposing counsel examines the claim will find this, in a courtroom, while that customer is trying to recover a loan. **This is a fraud-exposure risk, not a code risk.**

2. **The platform choice is incompatible with the product, and the re-platform will eat runway.** Vercel cannot run the four background loops producing every integrity guarantee sold, cannot hold websockets, cannot persist the in-memory TSA batch queue, cannot rate-limit, cannot store files. Budget 3 to 4 weeks minimum, and re-platform **once**, toward Ugandan hosting, given DPPA s.19.

3. **Unvalidated surface area has outgrown the team's ability to verify it.** 43,552 lines, 39 tables, 8.4% coverage, and the untested paths are precisely the demo features. Meanwhile the codebase contains a mutually exclusive pair of facts (P0-1) that nobody noticed, and a trigger forbidding three UPDATE paths the application performs (P0-7). **When you cannot tell which of two contradictory things is true in your own production system, every pivot costs weeks and every demo is a coin flip.**

---

## Ratings

### Codebase production readiness: 4/10

**Above 3** because the parts a competent auditor checks first are genuinely well built: FORCE RLS across all 39 tables applied catalogue-driven, a double-checked authorization layer on 158 call sites, DB-level append-only triggers, a test fixture asserting its own role cannot bypass RLS, JWT and password handling with no findings, and an epoch-sealing design that refuses to seal without its TSA anchor. Someone here thinks carefully.

**Below 5** because the deploy target cannot run the product, the flagship feature is off by default, three write paths are forbidden by the application's own trigger, "public verification" requires authentication, documents have no tamper-evidence, rate limiting and file storage do not survive the platform, and the critical paths are untested. **Not shippable to a regulated buyer without the P0 fixes.**

### Business idea, technical merit and defensibility: 3/10

**Merit** is real but narrow. Multi-tenant, RLS-isolated, append-only event sourcing with a document-compliance engine is a legitimate foundation, and the ETA 2011 ss.7-8 plus Tier 4 Act s.88(1) argument is a sharp commercial wedge most competitors will not find.

**Defensibility is the problem.** Every cryptographic primitive here is 25-year-old commodity: SHA-256 chaining, Merkle trees, RFC 3161. `rfc3161ng` is a pip install. No novel cryptography, no patent, no proprietary data, no network effect, no switching cost beyond data migration. Worse, the crypto is not what the buyer pays for, since no Ugandan regulator requires it, so the moat is not even in the part that is hard to build. What is actually defensible is the document-requirement compliance engine plus statutory workflow knowledge, and those are defended by **distribution and domain relationships, not technology.**

What caps the score is ~43,500 lines built ahead of a single customer conversation. In engineering terms that surface area is now a liability taxing every future decision: 39 tables to migrate, 467 files to keep compiling, four background jobs to keep alive, and a quarter of it deletable without a customer noticing.

> **The single highest-value action available is not a code change.** It is ten conversations with licensed money lenders about what happens when they go to court to recover a defaulted loan. If s.88(1) hurts them, there is a company here. If it does not, there are 43,500 lines of very well-isolated infrastructure and no business, discovered for the price of ten conversations instead of another six months.

---

## Sources

### Primary, opened and extracted directly

- **UMRA, Tier 4 Microfinance Institutions and Money Lenders Act 2016.** `http://umra.go.ug/wp-content/uploads/2021/09/Tier-4-Microfinance-Institutions-Money-Lenders-Act-2016-PUBLISHED.pdf` Fetched, text-extracted locally with `pypdf`. All s.8, s.9, s.31, s.32, s.74, s.75, s.87, s.88 quotations are verbatim from this file.
- **UMRA, Licensed Institutions as of March 2022.** `https://umra.go.ug/wp-content/uploads/2022/05/LICENSED-INSTITUTIONS.pdf` Institution counts are extracted from row numbering.
- **European Commission, Access2Markets, EUDR delay.** `https://trade.ec.europa.eu/access-to-markets/en/news/delay-until-december-2026-and-other-developments-implementation-eudr-regulation` EUDR dates 30 Dec 2026 / 30 Jun 2027, Regulation (EU) 2025/2650, 5-year retention, simplified DDS regime.
- **Uganda NGO Bureau**, DPPA registration requirement notice. `https://ngobureau.go.ug/index.php/en/news-and-notices/reminder-of-the-requirement-to-register-under-the-data-protection-and-privacy-act`

### Secondary, used where primary was unreachable

- `https://www.mondaq.com/privacy-protection/926740/data-protection-and-privacy-act-2019-what-you-need-to-know` (DPPA s.19, s.29)
- `https://www.kaa.co.ug/registration-compliance-under-the-data-protection-and-privacy-act-2019/` (s.29(2) registration, penalty figure)
- `https://www.statista.com/outlook/co/digital-connectivity-indicators/uganda` (internet penetration ~21.88%, 2025, aggregator)
- `https://www.macrotrends.net/global-metrics/countries/uga/uganda/electricity-access-statistics` (electricity access 51.5%, 2023, aggregator)
- `https://businesstimesug.com/ugandas-digital-leap-fast-connections-slow-adoption-gsma-report/` (GSMA coverage figures, press)
- `https://parliamentwatch.ug/news-amp-updates/7-5-million-ugandans-cut-off-as-mobile-access-gap-widens-ucc/` (UCC Q4 2025 subscriber figures, press reporting a UCC report not directly opened)

### Could not be opened

- `https://www.nita.go.ug/sites/default/files/2021-12/Data%20Protection%20and%20Privacy%20Act%20No.%209%20of%202019.pdf` HTTP 404
- `https://ulii.org/akn/ug/act/2016/18/eng@2016-10-28` HTTP 403
- `https://ulii.org/akn/ug/act/2011/8/eng@2011-03-18/source` Electronic Transactions Act 2011, search listing only. **ss.7-8 content is from converging secondary sources, not read directly**
- `https://faolex.fao.org/docs/pdf/uga172004.pdf` FAOLEX copy of the Tier 4 Act, scanned JBIG2, not text-extractable

### Local copies in `docs/sources/`

**Provenance correction.** These were originally described as pre-existing files in `timeline/`. They were not. They were written into the `timeline/` repo root on 2026-08-28 by an earlier, rate-limited research run of this same assessment, as extracted text from fetched PDFs. They have been moved to `docs/sources/` and the repo is clean. See `COO-DECISION.md`.

- UCDA Monthly Coffee Report, June 2026
- USDA FAS, *Coffee Annual, Uganda*, Report UG2025-0001, 12 May 2025
- Insurance Act 2017 (Act 6), Uganda Gazette No. 33 Vol. CX, 8 June 2017
- Insurance (Licensing and Governance) Regulations 2020, SI 2020 No. 101
- NSSF (Amendment) Act 2021
- UNCST, Accredited Research Ethics Committees in Uganda
- NCHE, *The State of Higher Education and Training in Uganda* **2019/20** (not the 2020/21 edition the HR report sought). Contains enrolment by discipline, not graduate output. See `HR-PEOPLE-PLAN.md` gap 2.

---

## Explicit gaps: no verified source

1. Current (2025-26) UMRA licensed-institution counts. Figures used are March 2022, self-extracted.
2. Shilling cost of PDPO registration and of Ugandan data-residency hosting.
3. Whether `reg.cisumra.com` exposes an API, and its current status.
4. Exact ETA 2011 and DPPA section numbering against the Gazette. Blocked by 404 and 403 on both primary hosts.
5. Whether Vercel's proxy passes a usable client IP to `get_remote_address`. Verify against current Vercel and SlowAPI documentation before relying on any rate-limit behaviour.
6. Healthcare/pharma (NDA) and legal/judiciary verticals were not assessed in depth.
