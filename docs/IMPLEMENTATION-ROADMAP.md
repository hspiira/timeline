# Implementation Roadmap

**Date:** 2026-08-29
**Merges:** `REMEDIATION-PLAN.md` (34 items, R-01…R-34, fixing what is broken) and `research/PACK-PLATFORM-INSIGHTS.md` + `OSS-POSITIONING-REFERENCES.md` (the substrate to build).
**Supersedes neither.** Both remain the detail; this is the sequence.

## Why one roadmap and not two

The remediation plan and the pack-platform research compete for the same single engineer. Run separately they would deadlock, because a third of the platform work **is** remediation work under a different name.

| Platform insight | Is the same work as | Consequence |
|---|---|---|
| Trigger.dev Steals A–C, durable idempotent side effects | The post-create hook swallow pattern (3 subsystems) | One outbox fixes the defect **and** delivers durable pack workflows |
| Relaticle Steal E, single write path with a lint rule | R-18, missing tenant predicates | The lint rule is what stops R-18 recurring |
| Plane Steal A, tenant FK in a base model | R-16 / R-18 tenancy hardening | Structural guarantee behind RLS |
| Plane Steal F, self-host as a first-class product | R-04 re-platform, R-32 data residency | Docker/Helm packaging during the re-platform is nearly free |
| Frappe Steal C, submittable/sealed lifecycle | R-07, moving mutable state off `event` | Must be **designed together** or R-07 is done twice |
| Relaticle Steal F, agent-addressable schema | R-08, actor column | Agent provenance is worthless without a recorded actor |
| Lago Steal E, per-tenant OLAP store | R-26, streaming verification | **Competing solutions.** Pick one, see D-06 |
| Plane Steal D, realtime only where it pays | R-31, delete websockets | Supplies the principle behind the deletion |

Genuinely new, with no remediation counterpart: Frappe A (schema → UI generation), Frappe G (pack migration hash), Frappe B (field types carry meaning), Frappe E / Plane B (advisory-lock sequence IDs), Relaticle B (EAV custom fields), Relaticle C / Plane C (states as data), Lago A–B (metering and wallet semantics), Plane E / G (editioning and community).

---

## Phase 0 — Decisions before code

**No engineering. All are expensive or impossible to reverse later.** Nothing downstream should start until these are answered in writing.

| # | Decision | Why it must come first |
|---|---|---|
| **D-01** | **Is RLS live, or does the app role bypass it?** (R-01) | One SQL query. Branches the entire integrity plan |
| **D-02** | **Is the append-only trigger deployed?** (R-02) | One SQL query. Determines whether anchoring currently raises at runtime |
| **D-03** | **EAV custom fields, or JSON-schema, for pack field variation?** | Relaticle Steal B. JSON-schema is simpler to validate; EAV is cheaper to vary and index, and needs no migration per pack. This decides the shape of the pack contract, so it cannot be deferred past Phase 5. The research doc's own guidance is "choose per pack", which is a third option and needs a written rule for when each applies |
| **D-04** | **Licence split: permissive spec/verifier/SDKs, AGPL server?** | Relicensing later requires **every** contributor's agreement. The window closes the moment the first outside PR lands |
| **D-05** | **Direct or Embedded first?** | An institution keeping its own records, versus a regulator or apex body offering record-keeping to everyone it supervises. Changes who the adopter is, and therefore what gets built first |
| **D-06** | **R-26 streaming verification, or Lago's per-tenant OLAP path?** | Competing answers to the same scale problem. OLAP avoids rewriting verification; streaming avoids a second datastore |
| **D-07** | **Which pack is the reference: tenancy or money lending?** | `packs/tenancy/pack.json` is built; `COO-REVISED-DECISION.md` confirms UMRA Tier 4 lenders. **These are different domains.** Deliberate demo choice, or drift? |
| **D-08** | **Dual-use posture.** Does the subject of a record get their own verifiable copy by right? | Carried from `OSS-POSITIONING-REFERENCES.md`; not covered in the research doc. Tamper-evident records of people are a surveillance instrument as readily as a protective one. This shapes defaults, and defaults in infrastructure are policy |
| **D-09** | **Does the build freeze hold, and over what?** | See below. The repo already contradicts the docs |

### D-09 in detail, because it is live now

`COO-DECISION.md` directive 1 and `COO-REVISED-DECISION.md` both say build freeze, zero features, 90 days. The repository disagrees: `scripts/seed_dev_data.py` is modified with 85 insertions, and `packs/` is untracked and new.

**Recommended resolution.** Split the freeze rather than keeping or dropping it wholesale:

- **Frozen:** vertical features, new surface area, anything that adds unvalidated code
- **Not frozen:** *truth-making* work, because the integrity claim being false is a liability that exists whether or not a customer ever appears, and *one* substrate proof, because the pack thesis is cheap to test and it is the thesis the whole open-source direction rests on
- **Runs in parallel, consuming no engineering hours:** the 30 discovery conversations

On that reading the seed-script change and the tenancy pack were legitimate. Make it explicit rather than leaving the docs and the repo in contradiction.

---

## Phase 1 — Ground truth and claim containment

Already exempt from the freeze under both COO decisions.

| Item | Source | Effort |
|---|---|---|
| Run the two diagnostics | R-01, R-02 | 2 hours |
| Write the Integrity Claim Statement, narrowed to what ships today, and use it verbatim everywhere | R-03 | 1 day |

**Gate:** nothing in Phases 2 onward is trustworthy until D-01 and D-02 are answered.

---

## Phase 2 — Platform foundation

| Item | Source | Notes |
|---|---|---|
| Re-platform off Vercel to long-lived processes, in Uganda | R-04 | `COO-REVISED-DECISION.md` reports this as cheaper than the original estimate: 1–2 weeks on AWS `af-south-1` or Raxio Namanve. **Verify that estimate before planning on it** |
| Extract background jobs into a worker with explicit tenant context | R-05 | The descriptor structure at `lifespan.py:95-113` already models jobs declaratively |
| **Ship self-host as a product in the same motion** | Plane Steal F | `setup.sh`, Docker, Helm, external Postgres/Redis/S3 via env vars. Near-free while re-platforming, and it is the wedge into regulated buyers and the DPPA residency story |

**Estimate:** 3–4 weeks, or 2–3 if the revised re-platform figure holds.

---

## Phase 3 — The write path and the outbox

The densest fusion of remediation and platform. Do it as one piece of work.

| Item | Source | Notes |
|---|---|---|
| Single write path for all subject/event writes, shared by API, web and any agent surface | Relaticle Steal E | Ownership checks **inside** the path |
| **An architecture test that fails any write bypassing it** | Relaticle Steal E | Relaticle uses a PHPStan rule. The Python equivalent is a lint or import-graph test. This is what stops R-18 recurring |
| Add missing tenant predicates | R-18 | `mark_event_integrity_status`, `complete_repair`, plus an audit of every other repository write |
| Tenant FK in a base model so no query can forget the boundary | Plane Steal A | Structural guarantee behind RLS |
| **Transactional outbox replacing the swallow-and-log hook pattern** | Trigger.dev A–C, R-05 | Fixes `WorkflowTriggerHook`, `WebhookDispatchHook`, `EventStreamBroadcastHook` in one change. Per-action declared retry policy with jittered backoff, an explicit abort path for permanently-invalid, and idempotency keys per action |
| Idempotent ingestion keyed on a client-supplied identifier | Lago Steal C | **First check whether `event.external_id` already serves this.** Not optional for field devices on unreliable connections |
| Persist workflow run history as events on the subject | Trigger.dev Steal D | The ledger of what the system did becomes as verifiable as the ledger of what happened |
| Fix session and transaction handling | R-19 | Same code region. Includes the TOCTOU fix: move transition validation inside the append transaction |

**Estimate:** 3–4 weeks.

---

## Phase 4 — Making the integrity claim true

| Item | Source | Notes |
|---|---|---|
| Move mutable integrity metadata off `event` to a side table | R-07 | **Re-scope first.** 253 references across 88 symbols in 28 files, plus a CHECK constraint, two indexes, and an RLS policy keyed on `epoch_id`. The original 1.5-week estimate was made without enumerating this |
| **Design the submittable/sealed lifecycle in the same change** | Frappe Steal C | Draft → Submitted(sealed) → Cancelled. Semantic finality is a *different axis* from byte-level tamper-evidence, and Timeline has only the second. Doing this after R-07 means opening the same 28 files twice |
| Versioned hash scheme, v1 kept permanently | R-09 | No hash versioning exists today, so any coverage change breaks every existing chain |
| Add the actor column and cover it in the hash | R-08 | **Unblocks the entire agent-provenance story.** Currently `event` records no actor at all |
| Bring documents into the chain | R-06 | `document.event_id` already exists and is unpopulated |
| RFC 6962 Merkle construction | R-12 | Fixes the CVE-2012-2459 shape and the missing domain separation |
| Commit over all subject tips, not one arbitrary tip | R-11 | Populates `subject_tips`, which is read but never written |
| Enable integrity by default; remove the STANDARD blind spot | R-13 | |
| Unify the two definitions of "verified"; fix the chain-repair docstring and tenant check | R-10, R-14 | |

**Estimate:** 5–6 weeks, pending the R-07 re-scope.

---

## Phase 5 — The pack contract

This is the substrate. Everything before it is prerequisite.

| Item | Source | Notes |
|---|---|---|
| **Generate list and form views from `subject_type` + `event_schema`** | Frappe Steal A | **The single highest-leverage item in this document.** It is the whole difference between configurable and plug-and-play. Until it exists, every pack still needs a developer |
| Field types that carry meaning, not just storage | Frappe Steal B | `Link`, `Table`, `Currency`, `Check`, plus `fetch_from` and `depends_on`. Model `relationship_kind` as a first-class link type |
| States as data, not schema | Relaticle C, Plane C, Frappe D | A domain's lifecycle is a field whose options are the states. Three projects converge here |
| Role-gated transitions | Frappe Steal D | Transitions carry an `allowed` role list and a condition. Timeline's workflows trigger on events, not on approved role transitions |
| Per-tenant human-readable IDs under an advisory lock | Frappe E, Plane B | `pg_advisory_xact_lock` per tenant. Loan and tenancy reference numbers need collision safety on day one |
| **Pack versioning and a migration path keyed on a pack hash** | Frappe Steal G, Trigger.dev atomic versioning | v1 → v2 on installed tenants, and a rule for what happens to in-flight flows when a pack changes. **Design before the second pack ships**, not after |
| EAV custom fields, if D-03 says so | Relaticle Steal B | Pack adds fields by seeding attribute rows; physical schema stays stable |
| Batched before/after diff as the event payload | Relaticle Steal D | One save produces one event with a combined diff, not loose independent writes |

**Estimate:** 6–8 weeks. Schema-to-UI generation dominates.

---

## Phase 6 — The agent surface

| Item | Source | Notes |
|---|---|---|
| Expose each pack's contract as machine-readable: subject types, events, states, fields | Relaticle Steal F | A pack becomes addressable by agents, not merely installable by humans |
| MCP server over the single write path from Phase 3 | Relaticle E + F | Rule to adopt: anything reachable in the form must be settable programmatically |

**Depends on:** R-08 (actor), Phase 3 (write path), Phase 5 (contract).
**Estimate:** 2 weeks.
**Strategic note:** as more records are agent-written, provenance and a named actor become *more* valuable, not less. This phase and R-08 are the same bet.

---

## Phase 7 — Verification, security, scale, tests

| Item | Source | Notes |
|---|---|---|
| **Genuine independent verification + the offline verifier** | R-33 | Unauthenticated route, anchor checking, roots published outside the application database, and a standalone verifier needing no network access. **This is also the court-ready record pack** for the lending vertical, so it serves both directions |
| Durable rate limiting; RLS check at startup; JWT precedence; upload constraints; key separation | R-15…R-17, R-20, R-21 | Sequence R-21 after the D-07/R-31 deletion decision |
| Make the test suite safe to run, then backfill | R-22…R-25 | **Treat coverage as trust collateral.** Relaticle leads with 2,000+ tests; Timeline is at 8.4% with anchoring, sealing, repair, erasure and retention untested |
| Scale: whichever D-06 chose | R-26…R-30 or Lago Steal E | Plus Merkle proof batching and node bulk-insert, which are needed either way |
| Delete ~11–12k lines | R-31 | **Plane Steal D supplies the principle** for the websocket call: realtime only for collaborative authoring, plain request/response everywhere else |
| PDPO registration and consent capture | R-32 | |
| External security and cryptographic review | R-34 | **Do not commission before the 90-day gates clear.** Largest cash item in the plan and worthless without a buyer |

**Estimate:** 6–7 weeks plus external lead time.

---

## Phase 8 — Ecosystem

| Item | Source |
|---|---|
| Pack registry and authoring documentation | Frappe F, Plane G |
| Editioning as extension points inside one codebase, not separate products | Plane Steal E |
| Community mechanics: public repo, labelled issues, CODEOWNERS, release notes | Plane Steal G |
| Metering and wallet semantics, only if packs are ever monetised | Lago A, B |

---

## Totals, and the honest problem

| Phase | Weeks *(estimate)* |
|---|---|
| 0. Decisions | 0.5 |
| 1. Ground truth | 0.3 |
| 2. Platform foundation | 3–4 |
| 3. Write path and outbox | 3–4 |
| 4. Integrity truth | 5–6 |
| 5. Pack contract | 6–8 |
| 6. Agent surface | 2 |
| 7. Verification, security, scale, tests | 6–7 |
| 8. Ecosystem | 3+ |
| **Total** | **approximately 29–35 engineer-weeks** |

**That is seven to nine months for one engineer, with zero customers today.** Stating it plainly because both source documents rate the business 3/10 specifically on the absence of demand evidence, and a nine-month build does not change that number.

Estimates are estimates. None is based on observed velocity on this codebase, and the R-07 figure is known to be wrong pending re-scope.

---

## The minimum viable slice

If only one thing gets built, build this. It produces a true integrity claim, one pack that generates its own interface, and a verifier anyone can run.

| # | Item | Phase | Weeks |
|---|---|---|---|
| 1 | Both diagnostics, and the narrowed claim statement | 1 | 0.3 |
| 2 | Re-platform with self-host packaging | 2 | 3 |
| 3 | Outbox, single write path, tenant predicates | 3 | 3 |
| 4 | R-07 with the submittable lifecycle, R-08 actor, R-09 hash versioning, R-06 documents, R-13 defaults on | 4 | 5 |
| 5 | Schema-to-UI generation for **one** pack | 5 | 4 |
| 6 | Offline verifier and independent verification | 7 | 2 |
| | **Total** | | **approximately 17 weeks** |

What that yields: an integrity claim that is true, a substrate that demonstrably generates a working domain from a data bundle, and a verifier a third party can run with no access to your servers. That is enough to show the thesis to a funder, a contributor, or a first design partner.

Everything else waits for evidence.

---

## Standing rules

1. **No item ships without the tests in its acceptance criteria.** 8.4% coverage is how contradictory facts survived unnoticed in this codebase.
2. **No outward claim may exceed what has shipped.** The claim statement is updated as items land, never ahead of them.
3. **Do not harden what Phase 7 will delete.** R-21 and R-25 wait on the deletion decision.
4. **Any change to a shared symbol gets its dependents enumerated before it gets an estimate.** R-07 was estimated blind and the estimate was wrong.
5. **Discovery runs in parallel and consumes no engineering hours.** The 30 conversations are not blocked by any of this, and none of this is validated without them.
