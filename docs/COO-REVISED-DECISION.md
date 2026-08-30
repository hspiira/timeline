# COO REVISED DECISION — Best industry to start in, Ugandan market

**Date:** 2026-08-29
**Author:** COO (re-appointed per `APPOINTMENTS.md`)
**Inputs (independent, parallel):** `CFO-REVISED.md`, `CTO-REVISED.md`, `HR-REVISED.md`, plus the prior-team base at `COO-DECISION.md`, `CFO-FINANCIAL-ASSESSMENT.md`, `CTO-TECHNICAL-AUDIT.md`, `HR-PEOPLE-PLAN.md`, `REMEDIATION-PLAN.md`.
**Instruction:** challenge the prior conclusion on evidence. May confirm, overturn, or refine.

---

## The decision

**Enter Uganda through UMRA Tier 4: money lenders and non-deposit-taking microfinance institutions — CONFIRMED as the best industry to start in — but the finding is now narrower and harsher than the prior pick, and it is governed by a sharper discovery question.**

Three executives, working independently on separate evidence, all nominated the same vertical; each also independently produced the same objection. That convergence under independence is the strongest evidence available in this exercise. I confirm the vertical. I **refine** the strategy: target the high-ticket, litigating/inspected minority, not the ~2,132 mass; scope the product as the "loan file of record + court-ready record pack + receipts" tier first; and run a sharper 90-day gate than the prior team did.

---

## How the three executives scored (summary)

| Dimension | Verdict | Key evidence |
|-----------|---------|--------------|
| **Finance (CFO)** | Money lenders best fit; corrected prior "killed on price" | ~2,132 licensed (Verified); statutory stack UGX 500k/yr licence + UGX 200k/yr dues (Verified); artefact prices UGX 100k–250k/yr (USD 27–67); but median loan UGX 30k–150k ≤8 days means mass market may not litigate |
| **Technical (CTO)** | Money lenders best fit; rules out EUDR as structurally impossible | File-of-record is 2–3 weeks; loan accounting +4–6 weeks; banks 20+ wks; EUDR impossible (no offline); re-platform 1–2 wks to AWS af-south-1 or Raxio Namanve |
| **People (HR)** | Money lenders best fit for staffing + co-founder | Deep cheap ex-UMRA pool; Employment (Amendment) Act 2025 now **in force** (commencement 5 Jun 2026); risk = fragile UMRA anchor |

---

## The 12-vertical scorecard (COO synthesis, weighted equally finance × technical × org)

Weighting note: for a pre-revenue solo founder, **cost-to-serve vs first-revenue** dominates. Score: 1–5 per dimension.

| # | Vertical | Fin | Tech | Org | Total /15 | Disposition |
|---|----------|-----|------|-----|-----------|-------------|
| 1 | **Money lenders / NDTMFIs (UMRA)** | 3 | 4 | 5 | **12** | **START HERE** |
| 2 | NGO / donor compliance | 1 | 4 | 4 | 9 | Rejected — donor funding collapsed |
| 3 | Coffee / EUDR | 1 | 1 | 2 | 4 | Rejected — no offline, state-funded |
| 4 | Clinical / health-research | 2 | 2 | 2 | 6 | Rejected — thin market, high build |
| 5 | Tier 1–3 banks (BoU) | 2 | 1 | 2 | 5 | Rejected — can't pass vendor onboarding |
| 6 | SACCOs | 2 | 4 | 3 | 9 | Runner-up-ish, small public register |
| 7 | Insurance (IRA) | 2 | 3 | 3 | 8 | Defer |
| 8 | Land (NLIS) | 1 | 2 | 1 | 4 | Rejected — state monopoly |
| 9 | Public procurement (PPDA) | 1 | 3 | 2 | 6 | Rejected — slow, politicised |
| 10 | Legal / judiciary | 2 | 3 | 2 | 7 | Defer |
| 11 | Education (NCHE) | 1 | 3 | 2 | 6 | Rejected |
| 12 | SME / manufacturing | 1 | 3 | 2 | 6 | Rejected — lowest WTP |

**Money lenders wins on fit, not on glory.** It clears the triple bar (count + statutory schema + statutory cost stack) that no other vertical clears, at the lowest cost-to-enter. Its weakness is unit economics — and that weakness is the whole point of the gate.

---

## What has genuinely changed since the prior team (and what has not)

**Changed (verified this round):**
1. **Employment (Amendment) Act 2025 is now IN FORCE** (assented 29 Apr 2026; commencement gazetted **5 Jun 2026**). Prior docs said "not yet gazetted." Budget for severance (1 mo/yr), 6-month casual cap, mandatory pre-dismissal hearings, and penalties up to UGX 10–14m. **This is a live liability, plan against it.**
2. **Market count re-verified ~2x higher** (2,132 licensed vs ~1,050 carried). Same direction, bigger base.
3. **Re-platform confirmed as cheap and fast** (1–2 wks, USD 300–1,500/mo) on AWS `af-south-1` or **Raxio Data Centre, Namanve** (the only in-Uganda option, for DPPA s.19 residency).
4. **The prior CFO "killed on price" ruling is corrected** — the distinct artefact can clear its own budget line.

**Unchanged (still loading):**
1. **No Ugandan regulator mandates cryptographic tamper-evidence.** The product is sold against an evidentiary burden, not a mandate. `[Verified]` in prior audit, unchanged.
2. **The integrity claim is not true as shipped** (anchoring off by default, background loops can't run on Vercel, verification behind login, documents outside the chain). **Fraud-exposure risk. Fix or narrow before any pitch.**
3. **The 3/10 business rating** — low because of what hasn't been done (zero demand evidence), not what can't be done. All three re-runs kept 3/10.

---

## The single decision the whole company now hinges on

> **"When you go to court to recover a defaulted loan under Tier 4 Act s.88(1), what does the documentation problem cost you — and have you ever actually done it?"**

Every executive independently arrived at this. The mass of 2,132 lenders makes small, high-frequency short-term loans and recovers by pressure/mediation, not litigation. **If the honest answer is "we never go to court," the integrity wedge is a feature, not a product**, and the correct move is not a different vertical (none clears the bar better) — it is to rebundle: sell the whole loan file + accounting + regulator-reporting bundle as compliance software at a price the buyer's licence budget will bear, and treat tamper-evidence as the durable differentiator, not the headline.

## The refined go-to-market (2026, corrected from prior)

| Element | Prior plan | **Revised** |
|---------|-----------|-------------|
| Target | ~2,132 money lenders | **High-ticket minority: larger NDTMFIs + ~15 licensed digital lenders who litigate and face inspection (ACV USD 100–150/yr). Then broaden** |
| Product | Loan file of record + court pack | **Same, plus receipts (s.87(1)-(2)); explicitly a record+compliance bundle, not a "crypto" pitch** |
| Money primitives | Not built | **Budget 4–6 weeks for money type + interest (2.8%/mo cap) + statement projection — it is the credibility feature CTO flags** |
| Platform | Vercel | **AWS `af-south-1` or Raxio Namanve; re-platform in weeks 1-2 (P0-6)** |
| Hiring | First hire = nobody, founder does discovery | **Unchanged — and now stricter: the 2025 Act makes any early hire more expensive** |
| Integrity claim | Must be true before written | **Unchanged — this is still P0 severity** |

---

## The 90-day gate (sharpened for 2026)

No further capital after day 90 unless all five hold. **Gate 1 is now narrowly specified:**

| # | Gate | Threshold |
|---|------|-----------|
| 1 | **Conversations, pain-first** | 30 completed in the high-ticket minority; **at least 3 must produce a real "cost of my last court/defaulted-loan record problem" figure** (not "our paperwork is fine"). 15+ with a budget holder |
| 2 | Existing spend | ≥3 buyers state in writing what they currently pay for an adjacent system, with the figure |
| 3 | Cash, not intent | ≥1 signed paid pilot at **USD 2,000+ annualised** (LOI worthless) |
| 4 | **Mandate / inquiry is live** | ≥1 written instance of a court, regulator, CRB or auditor asking that buyer for verifiable, unaltered records |
| 5 | Engineering freeze | Zero new features shipped (re-platform + the integrity *fix* are exempt — they're not features, they're the truth of the product) |

**Fail gate 1 or 3: stop.** **Fail gate 4:** the integrity layer is a hobby — pivot to plain case management and compete on price, or stop.

---

## Directives (2026, updated)

| # | Directive | Status vs prior |
|---|-----------|-----------------|
| 1 | Build freeze + re-platform (AWS af-south-1 / Raxio Namanve) in weeks 1-2 | Renumbered; re-platform now confirmed cheap |
| 2 | 30 pain-first conversations, high-ticket minority, 3 cost-figures | **Sharpened** (was "court under s.88(1)") |
| 3 | No hires; founder runs discovery personally | Unchanged |
| 4 | Run the RLS/anchoring diagnostic (read-only) | Unchanged |
| 5 | Register with the PDPO (DPPA s.19 / s.29(2)) | Unchanged; confirm sections vs Gazette |
| 6 | Narrow or fix integrity claim before any pitch | Unchanged |
| 7 | Delete ~11-12k lines when the freeze lifts (P5) | Unchanged |
| 8 | Budget for in-force Employment (Amendment) Act 2025 (severance, hearings, penalties) | **New** |
| 9 | Budget 4–6 weeks for money type + interest/statement projection before selling loan accounting | **New** |
| 10 | Verify UMRA licence fee + Money Lenders Regs; re-pull the current register | **New** |

---

## Risk register (2026 additions in bold)

| Risk | Source | Note |
|------|--------|------|
| **The s.88(1) pain does not exist for the mass market** | CFO + CTO + HR (all three) | The load-bearing risk. Median loan UGX 30k–150k, ≤8 days, recovery by pressure not litigation. Discovery question #1 |
| **Low ACV sidecar, not a venture** | CFO | ~USD 27–67/pack; 2,000 @ ~USD 70 ≈ USD 140k ARR. Confines growth unless ticket rises or bundle expands |
| **Fragile UMRA anchor / regulator downgraded into MoF** | HR | Voluntary-opt-in risk; longer sales cycles |
| Integrity claim goes in writing before true | CTO | Fraud exposure, P0 |
| **Employment (Amendment) Act 2025 now in force** | HR | Severance + hearings + UGX 10–14m penalties; raises cost of any early hire |
| Platform incompatibility (Vercel → off) | CTO | 1–2 wks, now scoped |
| Founder hires an engineer instead of doing sales | HR | Modal failure mode, unchanged |
| Ugandan price ceiling universal (~USD 300/yr) | CFO | If true, no Uganda vertical clears cost-to-serve |

---

## Final word

The prior team picked the right vertical for the wrong single look (a price-ceiling kill). This run **confirms the vertical on stronger, corrected grounds** — a verified 2,132-lender base, a verified statutory schema and cost stack, the cheapest technical path, and the best staffing/co-founder pool — while being **harsher about the strategy**: the winning motion is the high-ticket, inspected, litigating minority served a **compliance bundle**, not a crypto pitch to the 2,132 at large.

**Rating: 3/10, defensible.** It is low because of zero demand evidence. It re-rates to 5 on 10 pain-first conversations with 3 real cost figures, and to 6 on one signed paid pilot. All reachable in four months inside a single angel cheque.

**The single highest-value action has not changed — only sharpened.** It is ten conversations with the money lenders and NDTMFIs who actually face a court or a UMRA inspection: **"what did your last recovery/record problem cost you, and who asked for the records?"** If they can't answer with a number, there is no company here and we found out for the price of ten conversations instead of two quarters.
