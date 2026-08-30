# Reference projects for Timeline's open-source positioning

**Reviewed:** 2026-08-29. Each project's README fetched directly; quotations are from those READMEs and from Frappe's own documentation. Licences as stated by each project on that date.

**Purpose:** Timeline is being repositioned from a single-vertical product into an open-source verifiable-records substrate with plug-and-play vertical packs. These five projects were selected as models. This records what each one actually teaches.

> **Companion:** for the source-grounded, implementation-level "what to steal" extraction of the same five projects, see `research/PACK-PLATFORM-INSIGHTS.md`.

---

## The structural fact that makes this viable

Every concept a vertical pack needs is **already a runtime-configurable table with a CRUD endpoint** in Timeline: `subject_type`, `event_schema`, `event_transition_rule`, `document_category`, `document_requirement`, `naming_template`, `relationship_kind`.

So a "money lending pack" is a **data bundle, not a code plugin**. No code review, no version skew, and a domain expert rather than a programmer can author one. That is a stronger position than any plugin API, and it already exists.

---

## 1. frappe/erpnext — the closest structural match

**Licence:** GPL-3.0

The architecture is exactly the pattern Timeline is reaching for. Frappe Framework is the substrate, described in the README as "a full-stack web application framework written in Python and JavaScript" providing "a robust foundation for building web applications, including a database abstraction layer, user authentication, and a REST API." ERPNext is modules built on top of it.

**The idea worth taking is the DocType.** From Frappe's documentation:

> "A DocType is the core building block of any application based on the Frappe Framework. It describes the **Model** and the **View** of your data."

> "A DocType not only stores fields, but also other information about how your data behaves in the system. We call this **Meta**."

Three properties matter:

1. **Metadata is stored as data.** Behaviour can be changed at runtime without deployment.
2. **It is reflexive.** A DocType is itself a DocType. The system describes itself in its own terms.
3. **It generates the interface.** Creating one produces a database table, a list view at `/app/[doctype-name]`, a form view, and ORM access, with no code written.

**Where Timeline stops short.** Timeline has property 1. Defining an `event_schema` or a `document_requirement` changes behaviour at runtime. But it does **not** have property 3: defining a schema generates no UI. A pack author still needs a developer to make the pack usable.

That gap is the difference between "configurable" and "plug and play". Closing it is what would make packs real.

**Note on licence divergence:** ERPNext is GPL-3.0. Timeline is Apache-2.0. See the licensing section below.

---

## 2. triggerdotdev/trigger.dev — solves a defect already found in Timeline

**Licence:** Apache-2.0, the same as Timeline

The README states the platform provides:

> "Durability, retries & queues: Build rock solid agents and AI applications using our durable tasks, retries, queues and idempotency."

Plus checkpointing that makes tasks inherently durable, automatic retries on uncaught errors, no execution timeouts, concurrency and queue management, and **atomic versioning to deploy new versions without affecting running tasks**.

**Why this is directly relevant.** Timeline's post-create hook runner at `create_event.py:228` is:

```python
for hook in self._post_create_hooks:
    await hook.after_event(context)
```

No guard, no isolation, no error collection. Consequently all three hooks swallow their own exceptions and log: `WorkflowTriggerHook` (line 42), `WebhookDispatchHook` (lines 84 and 90), `EventStreamBroadcastHook` (line 138). Three subsystems diverge silently on failure, and the runner's structure leaves each hook no safer option.

Trigger.dev is the pattern that replaces it. The fix is a transactional outbox with durable retry, not better `try`/`except` in three places.

**The subtler idea: atomic versioning.** When a vertical pack changes, adding a required document or altering a transition rule, what happens to in-flight flows? Timeline has no answer. Trigger.dev's approach, where running work continues on the version it started with, is the model. **Pack versioning must be designed before packs ship**, not retrofitted.

Its positioning against serverless timeouts also mirrors Timeline's own platform problem exactly.

---

## 3. getlago/lago — the closest architectural cousin

**Licence:** AGPLv3 for the platform, **MIT for the Agent SDKs and MCP server**

An event-driven pipeline: usage events → metering → pricing and credits → entitlements → invoices → payments → revenue. Architectural features include idempotent event ingestion with deduplication by `transaction_id`, atomic batch processing, asynchronous workers for events, billing, payments and webhooks, Prometheus metrics, and independently scalable stateful services.

**Two ideas to take.**

**Idempotency by client-supplied key.** Timeline has a chain-fork retry loop, which handles concurrent appends. That is a different guarantee from idempotent ingestion, which handles a client retrying a request it is unsure completed. Timeline has an `external_id` column on `event`; whether it is used for deduplication is unverified and worth checking. For field devices on unreliable connections this is not optional.

**Direct versus Embedded.** Lago describes two operating models: Lago Direct for monetising your own product, Lago Embedded for platforms offering billing to their customers. The parallel for Timeline is significant:

- **Direct:** an institution keeps its own verifiable records
- **Embedded:** a regulator, donor or apex body offers verifiable record-keeping to every entity it supervises

The second is a far larger lever, particularly in Uganda, and it changes who the adopter is from hundreds of small institutions to one supervising body.

---

## 4. makeplane/plane — the playbook, and a warning

**Licence:** AGPL-3.0

The README states: "This project is licensed under the GNU Affero General Public License v3.0," and on deployment: "Prefer full control over your data and infrastructure? Install and run Plane on your own servers." Cloud and self-host are both first-class.

**The warning is the more useful part.** Plane positions explicitly as an open-source alternative to Jira, Linear, Monday.com and ClickUp. That technique works because the category is already understood and the incumbents are named.

**Timeline cannot copy it.** There is no incumbent to name, because the category does not exist in buyers' heads. That means category creation, which is slower and harder than substitution, and it has a concrete consequence: the explainer matters more than the feature list. Whoever explains a problem best tends to own the solution space.

---

## 5. relaticle/relaticle — one sharp idea and one uncomfortable comparison

**Licence:** AGPL-3.0. Stack: Laravel 13, Filament 5, PHP 8.5, Livewire 4, PostgreSQL 17+.

Described as "The Open-Source CRM Built for People and AI-Powered Work" and "a self-hosted CRM with a production-grade MCP server", integrating AI agents with 37 CRM tools. Also 22 custom field types, five-layer authorization for multi-team isolation, and 2,000+ automated tests.

**The sharp idea: the MCP server as a first-class product surface.** This is the modern form of "we have an API". For a verifiable-records substrate the implication is strong: as more records come to be written by agents rather than people, provenance and tamper-evidence become **more** valuable, not less. An agent-written record that carries a verifiable chain and a named actor is worth considerably more than one that does not. Timeline's missing actor column, found in this audit, is squarely in the way of that.

**The uncomfortable comparison: 2,000+ tests, led with as a headline.** Timeline is at 8.4% coverage, with TSA anchoring, epoch sealing, chain repair, erasure and retention entirely untested. For a self-hosted trust product, the test suite **is** marketing collateral. Nobody adopts a substrate they cannot verify, and coverage is the cheapest available proxy for that.

---

## Cross-cutting patterns

### Licensing is a deliberate strategy

| Project | Licence |
|---|---|
| ERPNext | GPL-3.0 |
| Plane | AGPL-3.0 |
| Lago | AGPLv3 platform, **MIT SDKs and MCP server** |
| Relaticle | AGPL-3.0 |
| Trigger.dev | Apache-2.0 |
| **Timeline (current)** | **Apache-2.0** |

Four of five chose copyleft. Timeline sits at the permissive end with Trigger.dev.

The trade-off is real. Apache-2.0 maximises adoption, carries a patent grant, and is what foundations and standards bodies prefer, which suits a **specification**. AGPL prevents a cloud provider from running your software as a service without contributing back, which suits a **product**.

**The recommendation is Lago's split**, because Timeline is both:

- **Permissive (Apache-2.0 or MIT) for the specification, the offline verifier, and any SDKs.** These must be embeddable everywhere without friction. A verifier nobody can embed verifies nothing.
- **Stronger copyleft (AGPL) for the server.** So that anyone offering hosted verifiable records contributes improvements back.

This is a decision to make deliberately and early, because relicensing later requires the agreement of every contributor.

### Every project separates engine from domain content

Most explicit in Frappe/ERPNext, present in all five. This validates the layering: specification → verifier → core engine → compliance kit → packs.

### All five offer self-host plus cloud

None is self-host-only. Even setting revenue aside, a hosted option is how non-technical institutions actually adopt. A district office will not run Docker.

### The two newest lead with an agent surface

Lago ships an MCP server and Agent SDKs; Relaticle ships 37 MCP tools. For new open-source infrastructure in 2026 this is approaching table stakes rather than a differentiator.

---

## What to do with this

1. **Close the Frappe gap.** Make pack metadata drive presentation, not only validation. This is what turns "configurable" into "plug and play."
2. **Design pack versioning before shipping any pack.** Trigger.dev's atomic versioning is the model. Retrofitting this is far harder.
3. **Replace the swallow-and-log hook pattern with a transactional outbox.** Trigger.dev is the reference.
4. **Decide the licence split now.** Permissive spec and verifier, copyleft server.
5. **Add idempotent ingestion keyed on a client-supplied identifier.** Check whether `event.external_id` already serves this.
6. **Treat the test suite as trust collateral.** Relaticle leads with 2,000+ tests; Timeline is at 8.4%.
7. **Evaluate Embedded as well as Direct.** One supervising body adopting on behalf of its supervised entities beats hundreds of individual sales.

---

## Sources

All fetched 2026-08-29.

- https://github.com/frappe/erpnext
- https://docs.frappe.io/framework/user/en/basics/doctypes
- https://github.com/triggerdotdev/trigger.dev
- https://github.com/getlago/lago
- https://github.com/makeplane/plane
- https://github.com/relaticle/relaticle

**Caveat:** licences, feature claims and architecture descriptions are as each project stated them on 2026-08-29 and can change. Re-check before relying on any of them in a licensing or architectural decision.
