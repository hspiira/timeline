# Executive Appointments — Mandates, Scope, and Instructions

**Issued by:** COO (acting)
**Date:** 2026-08-29
**Purpose:** Fresh, independent re-assessment of which *industry* a multi-tenant, tamper-evident, event-sourcing and case-file platform (`timeline/`, `timeline-ui/`) should enter first **in the Ugandan market**. This run is explicitly instructed to **challenge the prior conclusion** (money lenders / non-deposit MFIs under UMRA) and may confirm, overturn, or refine it — but only on evidence.

## Operating rules (apply to every officer)

1. **Evidence over belief.** Every claim carries a source. No fabricated figures. Where something cannot be verified, write **"NO VERIFIED SOURCE"** and say what would verify it — do not invent a number.
2. **Date-stamp everything** "(as of 29 Aug 2026)" and re-check regulator registers, budgets, FX and pricing that move.
3. **Maturity tagging.** Allowed tags: `[Verified primary]`, `[Verified secondary]`, `[Estimate + reasoning]`, `[Inference]`, `[NO VERIFIED SOURCE]`. A recommendation resting on `[NO VERIFIED SOURCE]` must be flagged as such.
4. **The two questions every officer must answer** for the shortlisted verticals:
   - (a) Does the technology convert into money the buyer already counts?
   - (b) Is the demand signal real today, not hypothetical?
5. **Constraint awareness.** Everyone must weigh the three structural constraints in `CTO-TECHNICAL-AUDIT.md`: the platform cannot run on Vercel (re-platform needed), the integrity claim is not true as shipped, and there are no financial primitives (money lives in untyped JSONB). These are inputs, not excuses.
6. **Deliverables.** Each officer returns a short memo (≤ ~800 words body) that scores their dimension for every candidate vertical against a named list of "candidate verticals", and explicitly states their single best pick and their single biggest objection to it.

## The candidate verticals to score (do not restrict yourselves to a smaller set, but do not silently add infinity)

1. Money lenders / non-deposit MFIs (UMRA / Tier 4)
2. NGOs and donor-funded programme compliance
3. Coffee / cocoa export & EUDR traceability
4. Clinical / health-research records (NDA / UNCST)
5. Tier 1-3 supervised financial institutions (BoU)
6. SACCOs (deposit-taking)
7. Insurance (IRA)
8. Land records (MLHUD / NLIS)
9. Public procurement (PPDA)
10. Legal / judiciary case files
11. Education / university records (NCHE)
12. Manufacturer / SGB asset and compliance records (a deliberately open category for SME formality)

---

## CFO — Appointment

**Role:** Finance & commercial viability. Owns market sizing, willingness-to-pay (WTP), cost-to-serve, and financing.

**Mandate:**
- For each candidate vertical, establish: verified price anchors (open vendor pricing pages), realistic ACV range, market size (countable buyers), and total addressable cost-to-serve (sales cycle, certification, delivery).
- Relentlessly test the single most important question: **will the buyer actually pay, and have they paid for anything adjacent before?** A "regulatory mandate" is only a WTP signal when the state has NOT built the tooling for free.
- Own the burn/runway model and the 90-day go/no-go gate.
- Explicitly separate the *price ceiling problem* that killed Tier 4 microfinance for the prior CFO from the *revenue-per-deal* possibility of a litigation-pack wedge — and give a defensible ruling.
- **Reframe request:** do not assume the integrity layer is the unit of sale. Evaluate both (i) selling the integrity/records layer to an incumbent system, and (ii) selling a complete bounded product (e.g. loan file of record with court-ready pack) that happens to be built on the engine.

**Deliverable:** `CFO-REVISED.md` — vertical WTP table + market sizes + financing reality + a ruling on the Tier 4 price-ceiling question.

**KPI:** A financial recommendation with at least 5 `[Verified primary]` or `[Verified secondary]` price points that were opened, not guessed.

---

## CTO — Appointment

**Role:** Technical feasibility & product-build cost. Owns how expensive each vertical is to build for, and whether the platform can actually be deployed and operated in Uganda for it.

**Mandate:**
- Catalogue, per vertical: incremental build cost (weeks, one engineer), regulatory/compliance engineering, integration complexity (existing core systems, national platforms), and **infrastructure fit** (offline needs, field-vs-office, connectivity).
- Rule on the re-platform: off Vercel, toward Ugandan hosting per DPPA s.19 (Uganda's Data Protection and Privacy Act). Confirm the current best host options and cost.
- Confirm/quantify the **no financial primitives** reality (no `Numeric`/`Decimal`/`amount` column in any model) and what it costs per vertical. In particular: does the money-lender "loan file of record" require money primitives, and is that cheap or the hidden cost the prior team said it was?
- Audit the true state of the integrity claim as shipped (anchoring defaults, background loops vs serverless, verification-tier login, documents outside the chain) — verbatim anything material so the COO and CFO can price the fraud-exposure risk.
- Flag any vertical that structurally cannot run on the current or 6-weeks-of-work platform.

**Deliverable:** `CTO-REVISED.md` — per-vertical build matrix + deploy/runtime reality + the single best and single worst technical vertical.

**KPI:** A build-cost matrix where every figure is labelled estimate-vs-measure, and a definitive ruling on (a) Vercel and (b) whether any chosen vertical needs money primitives.

---

## HR — Appointment

**Role:** Organisational & execution viability. Owns whether the company can staff/credibly enter each vertical and whether the people exist to be trusted with it.

**Mandate:**
- Per vertical: is domain credibility **hireable** locally (and affordable), or a non-hireable rolodex?
- Update the Ugandan salary/loaded-cost model where the prior report left it thin, and correct the "1.66:1 wedge" and "1.11x / 1.20x / 1.35x" multipliers where better data exists.
- Verify status of the **Employment (Amendment) Act 2025** (assented 29 Apr 2026; was commencement gazetted?) and its severance/implications.
- Rule on the co-founder-most-likely-to-come-from profile for each shortlisted vertical.
- Apply the "**first hire is nobody** / founder does discovery" doctrine and check whether any vertical changes it.

**Deliverable:** `HR-REVISED.md` — talent availability matrix + loaded-cost update + the staffing verdict per vertical.

**KPI:** A talent verdict per vertical that distinguishes "can staff" from "cannot staff", each with a sourced or labelled basis.

---

## Sequence and meeting

Officers research **in parallel and independently**. Each returns their memo. The COO then synthesises, scores all twelve verticals on (finance × technical × org), and issues `COO-REVISED-DECISION.md` naming the best industry to start in, the runner-up, the rejected, and the near-term action plan.

Officers may nominate different verticals. Resolution is on evidence, not on who shouts loudest.
