# CTO REVISED — Ugandan market technical feasibility (re-run)

**Date:** 2026-08-29 | **Author:** CTO (re-appointed per `APPOINTMENTS.md`)
**Mandate:** Per-vertical build cost, deploy/runtime reality, and whether the platform can actually run for each vertical in Uganda.

## 1. Re-platform is required, cheap, and fast — do it once

Vercel **cannot host this product.** Vercel's own limits (verified, docs updated 2026-08-24) cap function duration (300s default, 800s max, 1800s extended max) — there is **no unbounded execution** for the `while True` epoch-seal / chain-anchor / TSA-batch / projection loops. Vercel also has **no African region** (single `iad1` US default), so no in-country data-residency option exists at all.

**Where data should sit (DPPA s.19):** cross-border storage is legally permitted if the recipient country has protection "at least equivalent" to the Act, or the data subject consents. The PDPO (decision, 18 Jul 2025) requires no advance approval but demands documented legal-basis records, and has **not yet** published its "adequate countries" list. Conservative, zero-friction posture for Ugandan citizen data: in-country.

| Option | Location | Verdict |
|--------|----------|---------|
| **AWS `af-south-1` (Cape Town, 3 AZs, live since 2020)** | South Africa | **Preferred managed path.** RDS Postgres + ECS/Fargate/EC2 workers. Acceptable under s.19 with consent/adequate-protection record; not local |
| **Raxio Data Centre, Namanve (Kampala)** | **Uganda** | **Only truly in-Uganda option.** Tier III carrier-neutral DC (opened 2021, hosts Uganda IXP); Roke Cloud "ABQ Cloud". Self-managed VMs → run full stack on always-on compute |
| Hetzner | No African region (DE/FI/US/SG) | **Disqualified** |
| Wingu Africa | Djibouti/Ethiopia/Tz/Tz/Somalia | **Not Uganda** |

**Cost/timeline:** **US$300–1,500/mo, ~1–2 weeks** of senior time (Docker → ECS/EC2, RDS, worker migration). This is the cheapest, most certain work in the whole plan.

## 2. Per-vertical build cost (weeks, one senior engineer)

| Vertical | Weeks | Notes |
|---|---|---|
| Money-lender "loan file of record + court pack + receipts" | **2–3** | Pure fit for existing tamper-evidence; no offline needed |
| + Loan accounting (balance/interest/aging/statement) | **+4–6** | Financial projection layer + money type |
| Clinical / health-research | 8–14 | 21 CFR Part 11 / ALCOA+ / GAMP-5 IQ·OQ·PQ validation, vendor-qualified docs, e-signature |
| EUDR / coffee | **Structurally impossible now** | Requires offline GPS (±5 m); no offline mode exists |
| Tier 1–3 banks | 20+ | Temenos T24 core-banking integration (~9-mo, 90+ integration programs), ISO 27001/SOC2, vendor onboarding |

## 3. Money-lender ruling — direct

A **"loan file of record + court-ready record pack + receipts" does NOT require native Decimal/Numeric columns.** Ledger-engineering practice (independent sources, unanimous) treats balances, statements, aging and interest as **projections** over an append-only event stream; the house standard is a typed money value in integer minor units with double-entry/idempotency/currency invariants. Decimal columns are a storage convenience, not the hard requirement.

**The actual hidden cost:** the platform has *neither* a money type *nor* a financial projection engine — money sits in untyped JSONB and the existing projection engine is built for chain identity, not financial aggregation. Computing the **UMRA-capped 2.8%/month (≈33.6%/yr) interest** (Legal Notice No. 21/2024) means building a money value type, interest accrual, aging and audit-grade statements. **That is 4–6 weeks of real, measurable engineering — not multi-month, but a genuine build.** Do not sell it as "free."

## 4. Single best vertical and biggest objection

**Best: Money lenders** — the tamper-evident "loan file of record / court pack / receipts" tier. Near green-field (UMRA submission is report/batch, not live core-banking integration), low regulatory weight vs banks/clinical, no offline need, and it plays directly to the platform's differentiator (irrefutable, timestamped records).

**Biggest technical objection:** choosing this vertical **catalyses the financial-projection build**. A platform that can store a loan but cannot compute a balance aims at exactly the feature that undoes its credibility in front of a borrower, lender or court. Scope discipline (stay in the file-of-record lane first) is mandatory.

## 5. Structurally impossible near-term

**EUDR/coffee is incompatible on the current platform.** The no-offline-mode constraint is decisive; every verified tool in the space (MAAIF ToR, SYMOS, TerraTrac) is offline-first because rural terrain lacks connectivity. Field geolocation also needs integration with incumbents (MAAIF registry, National Data Warehouse 1.8M+ farmers). **Drop as a near-term option.**

## 6. Gaps not closed

- `reg.cisumra.com` technical submission format (API vs batch/schema) — mechanism exists, page would not load; interface unverified.
- **UGPASS Timestamping Service**: NITA-U confirms a timestamping service + first PKI licence (2022) in Uganda, but RFC 3161 conformance is **NOT VERIFIED**; assume EU/US TSA reliance is viable only via s.19 consent/adequate-protection until tested.
- PDPO "adequate countries" list — explicitly not yet published.
- Exact USD pricing for target AWS/Raxio configurations. NO VERIFIED SOURCE.

---

**Bottom line:** Re-platform to always-on compute (AWS `af-south-1`, or Raxio Namanve for true in-Uganda residency) in 1–2 weeks. Enter **money lenders** on the file-of-record tier first, budget honestly (4–6 weeks) for the financial-projection add-on. Defer banks and clinical until revenue justifies the compliance lift. Drop EUDR field collection.
