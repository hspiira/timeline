# COO Decision and Synthesis

**Date:** 2026-08-29
**Inputs:** `CFO-FINANCIAL-ASSESSMENT.md`, `CTO-TECHNICAL-AUDIT.md`, `HR-PEOPLE-PLAN.md`
**Subject:** Timeline (`timeline/`, `timeline-ui/`), a multi-tenant tamper-evident event-sourcing and case-file platform.

---

## Rating: 3 out of 10

| Assessor | Dimension | Rating |
|----------|-----------|--------|
| CFO | Financial merit | **3/10** |
| HR | Organisational and execution viability | **3/10** |
| CTO | Business idea, technical merit and defensibility | **3/10** |
| CTO | Codebase production readiness | **4/10** |

Three executives, working independently on separate evidence bases, arrived at the same number. They disagreed sharply on which industry to enter, which indicates independent reasoning rather than a committee effect, and they still converged on the score.

**This rates the business, not the engineering.** The gap between those two things is the entire finding.

---

## The constraint that comes before everything

**Do not put the integrity claim in writing to anyone until it is true, or narrow the claim to what `app/core/epoch_sealing_job.py:127-141` actually delivers.**

The CTO audit established that the guarantee the product rests on is not true as currently shipped:

- Anchoring flags default `False` (`app/core/config.py:99,105,107`)
- The background loops producing every integrity guarantee cannot run on the declared deploy target
- The public verification page requires login (`apps/web/src/routes/verify/$subjectId.tsx:34`)
- Documents carry no tamper-evidence at all
- The tenant-level anchor commits only to whichever subject wrote last

The scenario to avoid is a customer relying on this claim in court, with opposing counsel being the person who discovers anchoring was off. The CTO framed it as a **fraud-exposure risk, not a code risk**, and that framing is adopted.

The COMPLIANCE-profile epoch sealing path is genuinely sound. Sell that. Not the marketing version.

---

## Immediate action: one diagnostic

Two facts in the codebase cannot both be false (see `CTO-TECHNICAL-AUDIT.md`, P0-1):

> Either RLS is live and all integrity anchoring is silently dead, or the anchoring works and the app role bypasses RLS, meaning tenant isolation has no database layer at all.

```sql
SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user;
```

Read-only, so it does not violate the build freeze. **Run it first.** Everything else in the integrity backlog depends on knowing which world you are in.

---

## The vertical: money lenders and non-deposit-taking MFIs (UMRA)

Each executive nominated something different. Resolution:

| Exec | Nomination | Disposition |
|------|-----------|-------------|
| HR | NGO and donor compliance | **Superseded.** HR flagged the funding risk and instructed verification. The CFO independently verified approximately USD 307m and 66% of Uganda's USAID programme cut, EUR 2bn in EU cuts, GIZ suspensions Oct 2025. HR asked the right question and the answer came back against its own pick |
| CFO | Clinical and health-research records | **Not chosen.** The NDA 20-year retention mandate is real and primary-sourced. But the institution count, the load-bearing sizing input, is the CFO's own unsourced estimate of 10 to 15. HR independently rated healthcare records-compliance talent "thin". The CTO rated it high engineering effort (e-signatures, CSV/GAMP5 validation). A small unverified market that is hard to staff and hard to build for is not a first market |
| CTO | Money lenders / non-deposit MFIs (UMRA) | **Adopted** |

### Why

It is the only nomination where the technology converts into money the buyer already counts, and the reasoning rests on statute the CTO extracted verbatim from UMRA's own published PDF rather than from recall:

> Tier 4 Act **s.87(3)** specifies the exact record fields a money lender must keep. That is an event schema defined by statute.
>
> **s.88(1)**: where a money lender applies to court to recover money lent, they *shall produce* those s.87 records.
>
> **ETA 2011 s.8** puts the burden of proving the authenticity of the electronic records system on the party adducing it. **s.7** defines integrity as "complete and has not been altered."
>
> A hash chain with a TSA anchor is direct evidence of exactly that, at the exact moment the lender is trying to get their money back.

**s.75(2)** gives the retention module a statutory seven-year number. **s.8(2)(l)** names a Credit Reference Bureau reporting mechanism, a defined rather than guessed integration target.

**Infrastructure fit:** a money lender works from a fixed office with a laptop and a router, not a farm. The total absence of an offline mode is survivable here and disqualifying almost everywhere else.

**Talent fit:** HR independently rated ex-UMRA and MFI operations talent **"excellent and cheap"**, rejecting that vertical only on ability to pay, not on staffability. That convergence is what makes this pick executable.

### The objection to take most seriously

The CFO killed Tier 4 microfinance on price, having read **UGX 840,000/year (approximately USD 223)** off SaccoRa's own pricing page for an entire core banking system with unlimited members.

**COO judgment, flagged as judgment rather than verified finding:** that kill may not transfer cleanly. The CFO priced *SACCO management software*, sold to *SACCOs*, out of an *operations budget*. The CTO's wedge is a different artefact (a court-ready loan record pack), sold to a different segment (approximately 1,050 licensed money lenders versus 46 SACCOs on the same UMRA list), against a different budget line (loan recovery and litigation).

But the CFO's discipline stands, and it becomes discovery question number one:

> **When you go to court to recover a defaulted loan, what does the documentation problem cost you, and what have you paid to fix it?**

If the honest answer is "nothing, our paperwork is fine", the vertical dies and the CFO was right.

**Caveat on the counts:** the UMRA list is dated March 2022, and the figures are the CTO's own extraction from row numbering. Verify with UMRA before planning on them.

### The engineering bill

The system has **no financial primitives at all.** No `Numeric`, `Decimal`, `currency` or `amount` column exists in any persistence model. Money would live in untyped JSONB payloads. It can record a repayment; it cannot compute a balance, apply interest, age a portfolio, or produce a statement.

---

## Directives

| # | Directive | Rationale |
|---|-----------|-----------|
| 1 | **Build freeze, 90 days. Zero features.** | The CFO's gate 5: any engineering hour spent now is itself a fail signal, because the risk is demand and no amount of code reduces it. **This overrides the CTO's 10 to 14 week engineering estimate**, which stays on the shelf until the gates clear |
| 2 | **30 conversations with licensed money lenders**, at least 15 with a budget holder | One question above all: what happens when you go to court under s.88(1) |
| 3 | **No hires.** Founder runs discovery personally | The discovery loop is the roadmap in a founder-led company. Outsourcing it now permanently severs the person making architecture decisions from the buyer |
| 4 | **Run the RLS diagnostic** | See above. Read-only, exempt from the freeze |
| 5 | **Register with the PDPO** (DPPA 2019 s.29(2)) | Days and a nominal fee. Cannot sell to a regulated buyer without it. Section numbers are secondary-sourced; confirm against the Gazette before anything contractual |
| 6 | **Narrow or fix the integrity claim** before any pitch, deck, demo script or contract | See the constraint above |
| 7 | **When the freeze lifts, delete ~11,000 to 12,000 lines** (~25% of the codebase) | Per `CTO-TECHNICAL-AUDIT.md` P5. None of it would be noticed by a first paying customer |
| 8 | **Re-platform once, not twice** | Vercel cannot run the product (P0-6), and DPPA s.19 pushes toward Ugandan hosting. Do both in one move |

### Numbers to plan against when hiring eventually begins

- **1.66:1** employer-cost to employee-take-home wedge
- **1.11x** for cash-flow modelling, **1.20x** for provisioning, **1.35x** for affordability decisions
- Employment (Amendment) Act 2025 assented 29 Apr 2026, commencement not yet gazetted, introducing severance at one month per year worked

---

## The 90-day gate

No further capital after day 90 unless all five hold:

| # | Gate | Threshold |
|---|------|-----------|
| 1 | Conversations | 30 completed, at least 15 with a budget holder, all in one vertical |
| 2 | Existing spend | At least 3 buyers state in writing what they currently pay for an adjacent system, with the figure |
| 3 | **Cash, not intent** | At least 1 signed paid pilot at USD 2,000+ annualised. **An LOI is worth nothing** |
| 4 | Mandate is live | At least 1 written instance of an auditor, monitor, court or regulator asking that buyer for tamper-evident or independently verifiable records |
| 5 | Engineering freeze | Zero new features shipped |

Fail gate 1 or 3: **stop.** Fail gate 4: the integrity layer is a hobby; pivot to plain case management and compete on price, or stop.

---

## Risk register

| Risk | Source | Note |
|------|--------|------|
| **Founder hires an engineer instead of doing sales** | HR | Called "the modal outcome for a solo technical founder with a large finished product and no customers". Discovery is uncomfortable and produces no artefact for weeks; engineering is comfortable and the founder is excellent at it. Under uncertainty people revert to competence |
| **Integrity claim goes in writing before it is true** | CTO | Fraud-exposure, not code |
| **Ugandan price ceiling is real and universal** | CFO | Verified adjacent WTP is USD 111-223/yr. If the true ceiling is USD 300/yr, no Uganda vertical clears the cost of selling to it |
| **Platform incompatibility eats the runway** | CTO | 3 to 4 weeks minimum, non-negotiable |
| **Single point of failure** | HR | No bus factor, no code review, nobody else who can answer a security questionnaire honestly. Every institutional vendor due diligence will surface this |
| **Commission-only salesperson** | HR | Produces nothing in four months; founder draws the wrong lesson |
| **State builds it free** | CFO | Verified in three of four researched verticals. A mandate is only a WTP signal when the state has not funded the tooling |

---

## Why 3, and what moves it

**Not lower.** The asset is real and the wedge is sharp. Tenant isolation is genuinely good work, with no cross-tenant leak found across 39 tables under FORCE RLS plus a second application-layer check on 158 call sites. The epoch sealing design is correct. The s.88(1) plus ETA ss.7-8 argument is the kind of thing most competitors never find. Total capital at risk to reach a decision is under USD 30,000, inside a single angel cheque.

**Not higher.** On the one dimension determining survival, the information content of this business is nil. Zero interviews, zero pilots, no tested price. On defensibility: every primitive is 25-year-old commodity, `rfc3161ng` is a pip install, and the crypto is not what the buyer pays for, since no Ugandan regulator requires it. The moat is not even in the part that was hard to build. What is defensible is the document-compliance engine plus statutory workflow knowledge, defended by relationships rather than technology.

**The rating is low because of what has not been done, not because of what cannot be done.**

| Milestone | Re-rates to |
|-----------|-------------|
| 30 conversations in one vertical, 3 written problem statements | **5** |
| 1 signed paid pilot at USD 2,000+ annualised (LOI does not count) | **6** |
| Credible commercial co-founder joins | **7** |

All three are reachable in four months. None costs a shilling of hiring spend.

> **The single highest-value action available is not a code change.** It is ten conversations with licensed money lenders about what happens when they go to court to recover a defaulted loan. If s.88(1) hurts them, there is a company here. If it does not, that is discovered for the price of ten conversations instead of another six months.
