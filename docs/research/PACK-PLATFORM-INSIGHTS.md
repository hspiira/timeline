# Deep insights: five open-source models for the record-of-truth platform

**Reviewed (code-level): 2026-08-29**
- frappe/erpnext + frappe/frappe — https://github.com/frappe/erpnext
- triggerdotdev/trigger.dev — https://github.com/triggerdotdev/trigger.dev
- getlago/lago — https://github.com/getlago/lago
- relaticle/relaticle — https://github.com/relaticle/relaticle
- makeplane/plane — https://github.com/makeplane/plane

**Purpose:** Companion to `OSS-POSITIONING-REFERENCES.md` (which reviewed the project READMEs at a high level). This document extracts the **implementation-level mechanisms** worth stealing, verified against each project's source, and maps them onto Timeline's existing primitives. The framing fits the open-source "engine + swappable domain packs" model.

**Timeline's current pack primitives (the mapping target):** `subject_type`, `event_schema`, `event_transition_rule`, `document_category`, `workflow`, `naming_template`, `relationship_kind`, `connector`. A pack is a data bundle installing these per tenant (see `packs/tenancy/pack.json` for a live example).

---

## 1. frappe/erpnext — the origin of the "pack = data, not code" model

**The whole thesis in one line:** here's the twist — a pack's *logic* is where depth hides. In Frappe, business logic is Python controllers (`validate`, `on_update`, `before_submit`) that live next to the declarative DocType. So "configurable" was never the real ceiling; **the ceiling is whether the logic a domain needs can be expressed without forking the core.** ERPNext's answer has four parts.

### Steal A — declarative schema is "meta," and the meta is itself data
A `DocType` record holds child tables for `fields`, `permissions`, `links`, `states`, `actions`; saving it in developer mode auto-generates the DB table (`frappe.db.updatedb`), exports a `.json`, and scaffolds a controller `.py`. **Timeline already has the "meta is data" half via `event_schema`/`subject_type`.** The missing half is the generator: defining a subject type should produce a usable UI + a default menu + a list/form view with **no code**. That is the single highest-leverage gap — it is the difference between "configurable" and "plug and play."

### Steal B — field types carry meaning, not just storage
Frappe's `fieldtype` encodes semantics: `Link` (FK to another DocType), `Table` (embedded child rows), `Dynamic Link`, `Currency`, `Check`, plus `fetch_from` (auto-pull a value from a linked doc) and `depends_on` (conditional visibility). This is a richer event-schema vocabulary than a bare JSON-schema object. **Worth copying:** model `relationship_kind` as a first-class field type (the `Link` analog) so a pack declares `borrower → loan → lender` as data, not schema.

### Steal C — `is_submittable` gives you an immutable lifecycle for free
`make_amendable()` adds `amended_from`/`amended_by`; docstatus enforces `Draft(0) → Submitted(1) → Cancelled(2)` with no editing after submit, and `check_if_latest()` throws on concurrent stale writes. **This is exactly the "record of truth" lifecycle** — a submitted event is sealed. Timeline's hash-chain handles *tamper-evidence* at the byte level, but Frappe's docstatus answers the *semantic* question ("is this record final?"). A pack should be able to declare a subject type as *submittable* and get Draft/Submitted/Cancelled for free.

### Steal D — declarative `Workflow` state machine (the closest match to your `workflow`)
A `Workflow` is pure data: `states` (each mapping to a doc_status, optional derived-field updates) and `transitions` (state → action → next_state, with an `allowed` **role** list, a `condition` via `safe_eval`, and `allow_self_approval`). `apply_workflow` enforces roles and can drive submit/cancel. **This validates the pack's `workflow` primitive almost 1:1** — and adds two things to copy: (1) transitions carry a *role* requirement (currently your workflows trigger on events, not on approved role transitions), and (2) state can *map to* the submittable lifecycle (a "submitted" state == sealed record).

### Steal E — `naming_series` for collision-safe per-tenant run numbers
A series like `SINV-.YYYY.-.#####` tokenizes date parts and a zero-padded counter kept in a `Series` table incremented **atomically**, with sane reclamation on delete. **Timeline's `naming_template` is the direct analog** — this is a reference implementation for "Case #«tenant»-«year»-«seq»" numbering with collision safety.

### Steal F — hooks.py = the extension contract that makes an ecosystem possible
A single `hooks.py` per app registers `doc_events` (on_update/on_submit/on_cancel, even on `"*"`), `override_doctype_class`, `permission_query_conditions`, `has_permission`, `scheduler_events`, migrations. **Limit:** Timeline is a *data-bundle* platform, so packs don't add Python hooks. But the *ecosystem lesson* transfers: define a single, narrow extension surface (e.g. a pack can register events on `"*"` subject writes, or a workflow action) so third parties extend without forking. Frappe runs third-party code in `RestrictedPython` sandboxes (`safe_exec`) — worth copying if packs ever ship logic (migrate `event_transition_rule` conditions from config to a *sat-any-sandboxed-expression* language).

### Steal G — modular directory = versionable pack
Each ERPNext module is a folder (`accounts/`, `hr/`, `crm/`) owning its doctypes/reports/pages; a `migrate` pipeline diffs each `.json` against the DB and applies schema changes (`frappe.model.sync.sync_all`), with a `migration_hash` to detect drift. **Adopt this:** treat a pack as a versioned directory of JSON, and give pack versions a migration path (`v1 → v2` upgrades schema/events on installed tenants) keyed off a pack hash. This is the "how do packs evolve safely" question — Frappe has the canonical answer.

**Bottom line:** ERPNext is the closest structural match and the highest-signal source. The top three steals: (1) *generate UI from the schema* (the missing plug-and-play half), (2) a *submittable/sealed* lifecycle per record type, (3) a *migration pipeline for evolving pack schema*.

---

## 2. triggerdotdev/trigger.dev — durable side effects for pack workflows

Your pack workflows have side effects ("when rent is paid → create receipt reference; when loan disbursed → notify", plus the webhook/connector layer). Trigger.dev is the reference for making those side effects **durable and correct** without managing your own queue infra.

### Steal A — durable (checkpoint/resume) execution, not naive retry
Trigger.dev v3 snapshots a task's whole process at each pause point (`waitForEvent`) and restores rather than replays — so a job that made external side effects doesn't replay them on resume. **Reality check for a self-hosted record platform:** CRIU checkpoints are Cloud-only; self-hosted uses a store-state machine. The lesson that survives self-hosting: **model each side effect as its own idempotent unit and persist its state**, so a retry can't double-create a receipt. Timeline already hash-chains events; make outbound workflow actions idempotent the same way.

### Steal B — retry policy as a first-class declared per-task option
Exponential backoff with jitter is config per task (`maxAttempts`, `factor`, `minTimeoutInMs`, `randomize`), with `catchError` able to inspect the error+payload and *conditionally skip retrying* or *retry at a date*. **Copy:** give each workflow action a declared retry policy (and a "permanently invalid → abort, no retry" path), and bake jittered backoff at the action level, not the app.

### Steal C — idempotency keys + debounce on side-effect *triggers*, not raw calls
Triggering with an idempotency key returns the same run instead of duplicating; the known trap (from their own issue tracker) is that a side-effecting call made *inside* a run gets **no** protection. **Lesson:** make every outbound side effect its own idempotently-triggered unit and design external calls to be idempotent at their API level. Debounce is the tool for "recompute the ledger after a burst of edits settles."

### Steal D — run history as an auditable primitive
Every task run carries full tracing (attempts, retries, idempotency hits, state) that is queryable. **In a tamper-evident platform this is a goldmine:** the workflow side-effect history *is itself* an append-only record. Persist workflow run state as events on the subject, so the "ledger of what the system did" is as verifiable as the "ledger of what happened."

### Steal E — event-driven triggers into external systems
Webhook HTTP endpoints with signature verification map to events; a task can `waitForEvent` (pause for an external ping). **This is your connector layer done right:** "when rent is paid (DB write) → emit event → verified webhook → durable receipt task." Timeline's email/file/Kafka/CDC connectors are the seed; the missing piece is *durable orchestration* over them.

**Bottom line:** steal durability, per-action retry, idempotency discipline, and "run history is a record." Adopt Temporal-style state-machine durability only if you outgrow the simple queue; start with idempotent-triggered actions persisted as events.

---

## 3. getlago/lago — a clean architecture reference, and the billing/metering model for paying packs

### Steal A — decouple measurement from pricing (for paying packs)
Lago separates `BillableMetric` (the measurement: `SUM`/`COUNT`/etc per stable string code) from `Charge` (how that measurement is priced: tiers, packages, per currency) from `Plan`. **One metric, any number of price functions — re-instrument-free.** If packs are ever monetized, this is the model: define a pack's *record type* (measurement) independently of any *price* attached to it, so one pack can be free/enterprise/per-tenant without re-instrumenting the engine.

### Steal B — wallet semantics: top-up is liability, not revenue
Lago splits `paid_credits` (liability, recognized as revenue on consumption) from `granted_credits` (contra-revenue), with an "ongoing" (provisional) balance vs an "invoiced" (settled) balance. **If you meter pack usage against credits** (e.g. per-record or per-pack), copy this: a credit purchase is not revenue until used; provisional vs settled balances so live meter never blocks billing.

### Steal C — the ingestion pipeline is a layered, separable pipeline
`ingest → dedupe → enrich → aggregate → price`, with measurement (aggregation), pricing (charge model), and invoicing as separate stages so you can change prices without touching the meter. Idempotency is a **data-model decision**: dedupe on a deterministic `transaction_id`, ingest-everything-then-filter (unknown records skipped silently, not dropped), and use last-write-wins replacement for corrections. **This is the audit-then-reconcile contract:** lose nothing, skip silently, correct by replacement — exactly the discipline your record events need if they ever flow into analytics/billing.

### Steal D — hexagonal pragmatism and async worker topology
Thin controllers → domain `services` → models, with explicit ports for the volatile parts (payment providers, event stores) and idempotency as a first-class service. A separate *clock* process only *enqueues* recurring jobs; dedicated worker pools per concern (billing, payments, webhooks, PDFs) scale independently. **For Timeline:** keep each external dependency behind a seam; run the pack workflow side effects and any reporting/PDF as separate async pools, and keep a single scheduler that only enqueues.

### Steal E — self-host + a per-tenant upgrade path for scale
Lago stores events per-tenant-switchable on a fast OLAP store (ClickHouse) while the core stays on Postgres, with a backfill task to migrate a single tenant. **Copy the multi-tenant upgrade path:** the engine runs on Postgres; a high-volume tenant can move its event/analytics store to something faster without a global migration.

**Bottom line:** the billing/metering model for monetizable packs (Steals A–C), plus the architecture hygiene (D) and the per-tenant scale path (E). The wallet semantics (B) are directly relevant to any "pay per pack / per record" future.

---

## 4. relaticle/relaticle — the modern closest analog to your subject-type + pipeline design

### Steal A — one enum of subject types, shared uniform traits (registry, not fork)
Relaticle's subject types are a single `CrmEntity` enum mapped to model classes, all sharing the same traits (ULID ids, soft delete, team scope, creator, custom fields, `LogsActivity` timeline). Adding a record type = "add one enum case + model," not a fork. **For Timeline:** a subject type is already data, which is stronger — but the lesson is *uniformity*: every subject (regardless of pack) should expose the same operations (timeline, documents, relationships, retention) so no pack needs bespoke plumbing.

### Steal B — attributes as EAV custom fields (schema changes need NO migrations)
Typed attributes live in a polymorphic `custom_field_values` table keyed `(entity_type, entity_id, custom_field_id)` unique, with **one typed column per family** (`string_value`, `integer_value`, `date_value`, `json_value`, …). Even "native" fields are seeded custom-field rows. **This is the single biggest data-model insight for a data-bundle pack platform:** a pack adds fields by *seeding attribute rows*, keeping the physical schema stable while the logical shape of a subject varies per pack. Timeline's `subject_type.schema` is a JSON schema today; the EAV pattern is the alternative that makes per-tenant field variation cheap and migration-free. (Trade-off: JSON-schema is simpler to validate; EAV is cheaper to vary and to index. Choose per pack.)

### Steal C — the pipeline/board is just a SELECT field (states as data)
The kanban `STAGE` is a SELECT custom field whose *options* are the columns (reorderable, recolorable, renaming without code). Card move writes position AND state in one transaction. **For your packs: a domain's "state machine" is a field whose options are the states** — money-lending statuses, employment-verification stages — defined as data, not schema. This is the bridge between Timeline's `workflow` and a board UI.

### Steal D — timeline is a merged, ordered diff (your event timeline)
Every subject uses `LogsActivity` (log-all-dirty) into a polymorphic Activity model; rows sharing a `batch_uuid` are merged by a `TimelineBuilder` into one entry whose diff combines native + custom-field changes into an ordered list. **This validates the hash-chained event timeline** and suggests one refinement: an event should record a *batched before→after diff* (all fields changed in one save) as the immutable payload, not a loose set of independent writes.

### Steal E — one write path (the shared Actions layer)
All behavior funnels through `app/Actions/<Domain>/` `final readonly` classes with a single `execute()` doing authorization + ownership, shared by the web UI, REST API, and MCP tools; a custom PHPStan rule fails any write that bypasses the Actions layer. **Copy this as a hard architectural rule:** subject/event writes go through one CreateEvent path, shared by API, web, and any agent/MCP surface, with ownership checks *inside* that path.

### Steal F — agent/schema-discovery as the differentiator
An MCP server + REST API are first-class; a `GetCrmSchemaTool`/`ListCustomFieldsTool` **exposes the subject-type schema (fields + options) as a discoverable resource** so an agent can introspect before acting; a driven rule: "a field reachable in the form must be settable from chat." **This is the sharp edge for the record platform:** make the pack *contract* introspectable (this pack's subject types, events, states, fields) so a pack is not just installable by humans but **addressable by agents** — the thing ERPNext/HubSpot-class systems break on. Combined with fixes to the claim, the programmatic surface is a credible wedge.

**Bottom line:** EAV custom fields (B), states-as-a-field (C), a shared single write path (E), and **agent-addressable pack schema** (F). Relaticle is the closest to Timeline's "subject + timeline" shape, so its data-model and write-path rules are the most directly transferable.

---

## 5. makeplane/plane — the go-to-market + editioning playbook

### Steal A — strict tenant boundary via base-model + derived context
A 4-level hierarchy (`Workspace → Project → Cycle/Module → Issue`) with `WorkspaceBaseModel`/`ProjectBaseModel` mixins baking the tenant FK into every query chain; API views re-derive context from the URL path. **Copy:** put the tenant FK in a base model/mixin so *no query can forget the boundary* — the structural guarantee behind Timeline's RLS.

### Steal B — per-tenant human-readable sequence IDs under an advisory lock
Issues get `sequence_id` (like `PAG-42`) generated under `pg_advisory_xact_lock` keyed to the project, while UUIDs stay the real PK. **This is the reference implementation for Timeline's `naming_template`:** stable, scoped, human-facing ids (loan numbers, tenancy refs) under a Postgres advisory lock to prevent counter races — exactly what Frappe's `Series` does too.

### Steal C — states and views are configurable data, not schema
`State` is its own model (workspace-seeded defaults) and each issue holds an FK to it, so every project redefines its lifecycle without code; properties/priorities are enums, labels/assignees are through-tables. The whole product is "workspace is a configurable container; domain behavior is data." **Same conclusion as Frappe and Relaticle:** for pack states, make the lifecycle a tenant-defined entity (folder into your `workflow`/state model) rather than a set of enum columns.

### Steal D — realtime only where it pays
Only collaborative pages use CRDT realtime (Yjs/Hocuspocus via one `live` server + Redis fan-out); everything else is plain REST with async workers. **Adopt the restraint:** don't bolt websockets everywhere. Realtime only for the collaborative-authoring surface (a record's shared doc), backed by an event bus; keep lists/state plain request/response.

### Steal E — open-core with AGPL/protective licence; perfile editioning
AGPL-3.0 protects against closed-source SaaS forking; free Community Edition is the funnel (unlimited, self-host in <10 min) while SSO/RBAC/audit-logs/enterprise are a paid *editioning layer over the same codebase* (explicit `core` vs `ce` folders; upgrade = config/licence change, not re-platform). **For Timeline's packs:** define the paid/enterprise surface as *extension points within the same codebase* (per-pack or per-tenant gating) rather than separate products. Licensing will need care given Timeline is Apache-2.0 — a protective licence is a deliberate strategy, not a default.

### Steal F — self-hosting is a first-class product (regulated-vertical wedge)
Ships `setup.sh`, Docker, Helm, external Postgres/Redis/MinIO via env vars, a "God mode" admin app for instance admins; data-residency customers buy vendor-managed self-host. **Air-gap + BYO-storage are day-1 assumptions** — this is the wedge into regulated verticals (fintech lending, health, gov) and reinforces the DPPA/data-residency story already in Timeline's remediation plan.

### Steal G — community mechanics as a metrics pipeline
Public repo on day one, GitHub Discussions + forum, labeled beginner issues, `CODEOWNERS`, ship fast with release notes as content marketing; open-source engagement feeds both contributors and enterprise credibility/traction. **For the society/pack play:** treat the pack registry + community as the go-to-market, not a side quest.

**Bottom line:** the playbook — strict tenancy (A), per-tenant ids (B), states-as-data (C), realtime restraint (D), protective open-core + file-level editioning (E), self-host as a product (F), community as GTM (G).

---

## Cross-cutting synthesis — the six rules for the record platform

1. **Pack = data, and the UI must be generated from it.** Three projects converge here (Frappe's reflexive generator, Relaticle's field-registry UI, Plane's states-as-data). The #1 gap is generating list/form/board from `subject_type`+`event_schema`. Close it and packs become genuinely plug-and-play.
2. **Make the record lifecycle explicit: Draft → Submitted(sealed) → Cancelled.** Frappe's `docstatus` + Timeline's hash chain are complementary (semantic finality + byte-level tamper-evidence). Add a submittable/sealed concept per subject type.
3. **States and relationships as data, not schema.** Frappe `Workflow` states, Relaticle SELECT-field stages, Plane `State` — all say the same thing. Keep `workflow` and make `relationship_kind` a first-class link field type.
4. **Side effects are durable, idempotent, and themselves recorded.** Trigger.dev's durability + Lago's idempotency-as-data-model + run-history-as-record. Every workflow action gets a declared retry policy, an idempotency key, and its run history persisted as events on the subject.
5. **Strict tenant boundary, per-tenant human IDs, single write path.** Plane's base-model tenancy, Plane+Frappe advisory-lock numbering, Relaticle's Actions layer. Nail tenancy and the one-write-path early; they're hard to retrofit.
6. **Expose the pack contract to agents; self-host as a first-class product; protective open-core with file-level editioning.** Relaticle's schema-discovery surface, Plane's self-host + editioning, and the licensing strategy. The differentiator is programmatic + verifiable + self-hostable, not the crypto.

## What to do with this (in order)

1. **Schema → UI generation** for a subject type (from `packs/tenancy`), i.e. Frappe Steal A. The single biggest plug-and-play win.
2. **Verified programmatic/second surface**: expose a subject type's schema (fields/states/events) as machine-readable so a pack is agent-addressable (Relaticle F), gated behind the integrity/verification fixes already in the remediation plan.
3. **Lifecycle discipline**: add Draft/Submitted(sealed)/Cancelled semantics per subject type (Frappe C/D).
4. **Durable, idempotent, recorded workflow actions + their run history as events** (Trigger.dev A–D, Lago C). Persist side-effect history verifiably.
5. **EAV custom fields** as the cheap "per-tenant field variation" store where a pack needs it (Relaticle B).
6. **Per-pack migration path** keyed off a pack hash (Frappe G) so packs can evolve v1 → v2 on installed tenants.
7. **Pack registry + verified marketplace + licensing** (Plane E/G, Frappe F) as the ecosystem/GTM layer.

---

## Strategy-level insights from the companion review (OSS-POSITIONING-REFERENCES.md)

The companion review is pitched at **positioning / adoption / licensing**, a different lens from this document's implementation level. The following insights from it are **not** developed here and are worth keeping side-by-side:

### 1. Timeline's current hook runner is a live example of the durability problem (Trigger.dev)
Not a future risk — a present defect. The post-create hook runner at `apps/api/app/infrastructure/services/post_create_hooks.py` (referenced in the review as the runner around `create_event.py:228`) iterates hooks with **no guard, isolation, or error collection**; `WorkflowTriggerHook`, `WebhookDispatchHook`, and `EventStreamBroadcastHook` each swallow their own exception and log. The fix the review recommends is a **transactional outbox with durable retry**, not better `try/except` in three places. This is the concrete first implementation of Trigger.dev Steals A–C.

### 2. Direct vs Embedded adoption model (Lago)
Lago distinguishes **Direct** (monetise your own product) from **Embedded** (a platform offers billing to its customers). For Timeline: **Direct** = an institution keeps its own verifiable records; **Embedded** = a regulator/donor/apex body offers verifiable record-keeping to every entity it supervises. The latter is the far larger lever in Uganda and *changes who the adopter is* — one supervising body instead of hundreds of small institutions. This should be evaluated before the sales motion is set.

### 3. Licensing split — permissive spec/verifier, copyleft server (Lago's model, generalised)
Four of five reviewed projects chose copyleft (GPL/AGPL); Timeline is Apache-2.0 (with Trigger.dev). The recommendation: **permissive (Apache-2.0/MIT) for the specification, the offline verifier, and any SDKs** (they must be embeddable everywhere; a verifier nobody can embed verifies nothing), and **AGPL for the server** (anyone hosting hosted verifiable records contributes back). Decide early; relicensing later needs every contributor's agreement. This is strategic and separate from the implementation list above.

### 4. Category-creation, not substitution (Plane)
Plane substituted into an existing, understood category by naming incumbents (Jira/Linear/Monday). **Timeline has no incumbent to name — the category doesn't exist in buyers' heads — so category creation is slower and harder, and the explainer matters more than the feature list.** Whoever explains the problem best tends to own the solution space.

### 5. The test suite is trust collateral (Relaticle)
Relaticle leads with **2,000+ automated tests** as a headline; Timeline is at ~**8.4% coverage**, with TSA anchoring, epoch sealing, chain repair, erasure and retention untested. For a self-hosted trust substrate, coverage is the cheapest proxy for "I can verify this" — nobody adopts a substrate they cannot verify. Engineering, but strategic in effect.

### 6. Agent-written records make provenance MORE valuable (Relaticle)
As records come to be written by agents rather than people, an agent-written record carrying a verifiable chain and a named actor is worth more, not less. The review flags **Timeline's missing actor column** as squarely in the way of that provenance story — a concrete finding this deep-dive's Steal F (agent-addressable schema) does not cover. Combine: expose packs to agents (Steal F) *and* record the acting entity on every event.

### 7. The layering frame
The companion review frames the product stack as **specification → verifier → core engine → compliance kit → packs**, with every reviewed project separating engine from domain content. Useful shared vocabulary for deciding what is permissive (=spec/verifier, embeddable) vs copyleft (=engine/server).

## Sources
- frappe/frappe: `frappe/model/document.py`, `frappe/model/workflow.py`, `frappe/model/naming.py`, `frappe/permissions.py`, `frappe/modules/utils.py`, `frappe/migrate.py`, `frappe/utils/safe_exec.py`, `hooks.py`, `frappe/utils/pdf` + `print_format_generator`.
- triggerdotdev/trigger.dev: durable execution docs (CRIU checkpoint/resume, waits), task/trigger/idempotency/retry/catchError/debounce docs, self-host (Docker/Helm) and Cloud-only feature list.
- getlago/lago: `docs/architecture.md`, `docs/monitoring.md`, `app/services/billable_metrics/aggregation_factory.rb`, `app/services/events/stores/`, `events-processor` (Kafka topics `events_raw`→`events_enriched`→`events_enriched_expanded`→`events_charged_in_advance`), wallet/plan/charge docs.
- relaticle/relaticle: `app/Enums/CrmEntity.php`, `custom_field_values` table, `app/Actions/<Domain>/`, `LogsActivity` + `TimelineBuilder`, `OpportunitiesBoard`, MCP tools (`GetCrmSchemaTool`/`ListCustomFieldsTool`), `tests/Arch/ArchTest.php`.
- makeplane/plane: `apps/api/.../models/` (WorkspaceBaseModel/ProjectBaseModel), `issue.py` (`pg_advisory_xact_lock`, `sequence_id`), `State` model + `workspace_seed_task.py`, `apps/live` (Hocuspocus/Yjs), worker/webhook (`model_activity.delay`, `webhook_task.py`), `setup.sh`/Helm, editioning (`core` vs `ce`).
