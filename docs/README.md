# Timeline: business and technical assessment

Assessment completed **29 August 2026** by a simulated executive team (CFO, CTO, HR) reporting to a COO synthesis, covering the `timeline/` backend and `timeline-ui/` frontend against the Ugandan market.

> **On paths.** These documents were written while the API and the web client were
> separate repositories. File citations have been rewritten to the merged layout
> (`timeline-ui/src` became `apps/web/src`, and so on) so they still resolve. The
> findings, dates and evidence are unchanged.

## Re-run (2026-08-29, second pass)

A fresh executive team was re-appointed (`APPOINTMENTS.md`) and explicitly instructed to **challenge the prior conclusion**. It confirms **money lenders / UMRA Tier 4** as the best vertical, corrects the prior CFO "killed on price" ruling, and sharpens the go-to-market. Read these first for the current decision:

| File | Contents |
|------|----------|
| **[COO-REVISED-DECISION.md](COO-REVISED-DECISION.md)** | **Current decision.** Confirms money lenders/UMRA; refined go-to-market (high-ticket minority); sharpened 90-day gate; directives and risk register |
| **[APPOINTMENTS.md](APPOINTMENTS.md)** | The charters/mandates given to the CFO, CTO, and HR for this re-run |
| **[CFO-REVISED.md](CFO-REVISED.md)** | Market sizing (2,132 lenders), price-ceiling correction, financing, the s.88(1) pain objection |
| **[CTO-REVISED.md](CTO-REVISED.md)** | Build-cost matrix, re-platform (AWS af-south-1 / Raxio Namanve), money-primitives ruling, EUDR impossible |
| **[HR-REVISED.md](HR-REVISED.md)** | Staffing verdicts, Employment (Amendment) Act 2025 now in force, loaded-cost update |

**Key correction to prior docs:** the Employment (Amendment) Act 2025 is now **in force** (commencement gazetted 5 Jun 2026), not "not yet gazetted."

## Original assessment documents

| File | Contents | Read it for |
|------|----------|-------------|
| **[COO-DECISION.md](COO-DECISION.md)** | (Superseded by COO-REVISED-DECISION.md) original synthesis, rating, vertical selection, directives, risk register | **Start here.** The decision and what to do next |
| **[CTO-TECHNICAL-AUDIT.md](CTO-TECHNICAL-AUDIT.md)** | Prioritised remediation backlog (P0-P5) with `file:line` evidence, integrity audit, tenant isolation, security, test coverage, scale, deletion candidates, vertical analysis | **The engineering work list.** Most actionable document here |
| **[IMPLEMENTATION-ROADMAP.md](IMPLEMENTATION-ROADMAP.md)** | The merged sequence: remediation and pack-platform work in one plan, 8 phases, 9 up-front decisions, and a 17-week minimum viable slice | **Start here for execution.** Resolves where the two plans overlap and compete |
| **[REMEDIATION-PLAN.md](REMEDIATION-PLAN.md)** | All 34 remediation items sequenced into 8 phases, with dependencies, acceptance criteria and effort estimates | **The execution plan** for everything the audit found |
| **[CFO-FINANCIAL-ASSESSMENT.md](CFO-FINANCIAL-ASSESSMENT.md)** | Verified Ugandan willingness-to-pay, market sizing, burn model, financing landscape, ARR arithmetic, 90-day gate | Pricing, runway, and whether the market can pay |
| **[HR-PEOPLE-PLAN.md](HR-PEOPLE-PLAN.md)** | Hiring sequence with triggers, sourced Ugandan salary bands, employment law, loaded cost multiplier, co-founder profile | Before making any hire or quoting any salary |

## Open-source platform & pack research (2026-08-29)

| File | Contents |
|------|----------|
| **[research/PACK-PLATFORM-INSIGHTS.md](research/PACK-PLATFORM-INSIGHTS.md)** | **Source-grounded deep dive** into frappe/erpnext, triggerdotdev/trigger.dev, getlago/lago, relaticle/relaticle, makeplane/plane — the implementation mechanisms worth stealing, mapped onto the engine's pack primitives, with the 6 cross-cutting rules and an ordered action list |
| **[OSS-POSITIONING-REFERENCES.md](OSS-POSITIONING-REFERENCES.md)** | High-level README-level review of the same five projects, licensing notes, and the positioning/strategy takeaways |
| **[TENANT-AUTH-ADVISORY.md](TENANT-AUTH-ADVISORY.md)** | Review of the current tenant-creation and password-reset flows (grounded in `auth.py`, `tenant_creation_service.py`, `password_set_token_repo.py`, `register.tsx`) and a simpler, email-free-friendly implementation plan |

The working reference pack built from this research lives in the code: `packs/tenancy/pack.json` (+ `packs/README.md`).

## Headline

**Rating: 3/10.** Three independent assessments converged on the same number. The engineering is real; the business is unvalidated. Zero customer conversations had occurred at the time of assessment.

**Selected vertical:** money lenders and non-deposit-taking microfinance institutions regulated by UMRA, on the strength of Tier 4 Act s.87 (statutory record schema), s.88(1) (records must be produced in court to recover a loan) and Electronic Transactions Act 2011 ss.7-8 (the party adducing an electronic record bears the authenticity burden).

**Immediate constraint:** do not put the integrity claim in writing until it is true, or narrow it to what COMPLIANCE-profile epoch sealing actually delivers.

## `sources/`

Extracted text of primary PDFs used in this assessment: UCDA coffee report, USDA FAS coffee annual, Insurance Act 2017 and its 2020 regulations, NSSF (Amendment) Act 2021, UNCST ethics committees, NCHE higher education 2019/20.

**Provenance:** these were written into the `timeline/` repo root on 2026-08-28 by a rate-limited earlier run of this assessment, which fetched PDFs while its working directory was inside that repo. They were untracked and not gitignored. They have been moved here; both git repos are clean and unmodified.

## Evidence conventions used throughout

- Code claims carry `path/to/file.py:LINE`. Claims without a citation are labelled inference or estimate.
- Unverifiable claims are marked **"NO VERIFIED SOURCE"** with the reasoning, rather than being filled in with a plausible number.
- Time-sensitive claims are stamped "as of [date]". Uganda regulations, licence registers, donor budgets, cloud pricing and FX rates all move.
- Each document ends with an explicit list of gaps that could not be closed. **Those lists are part of the finding, not an appendix to skip.**

## Known stale or unverified inputs

Carried forward deliberately so they are not mistaken for settled facts:

- UMRA licensed-institution counts are from a **March 2022** list, self-extracted from row numbering. Verify with UMRA.
- DPPA 2019 and ETA 2011 section numbers are secondary-sourced; NITA-U returned HTTP 404 and ULII returned HTTP 403. Confirm against the Gazette before contractual use.
- The Employment (Amendment) Act 2025 rests on four concurring law-firm alerts, not the gazetted text.
- Ugandan salary data is thin and internally contradictory by up to an order of magnitude. Validate against live postings in the month you hire.
- No Bank of Uganda official FX rate was obtained; mid-market rates were used.
