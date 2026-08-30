# HR / People Plan

**Date:** 2026-08-29
**FX basis:** 1 USD = 3,771.89 UGX (Wise mid-market, retrieved 29 Aug 2026; Wise shows a 30-day band of 3,710.59 to 3,766.80). **Not the Bank of Uganda official rate.** Verify before contractual use.

**Rating: 3/10 on organisational and execution viability.**

## Executive summary

1. **The first hire is nobody.** The founder must personally complete 30 to 50 buyer conversations before any commercial headcount.
2. Hiring a salesperson now converts an unvalidated product into a burning payroll and moves the learning out of the founder's head. That is the single most likely failure mode.
3. Ugandan salary data for senior software roles is **thin, stale and internally contradictory by a factor of 5 to 10.** Treat the tables below as a floor plus a warning, not a benchmark.
4. **The Employment (Amendment) Act, 2025 was assented on 29 April 2026 and commencement is not yet gazetted.** It introduces statutory severance of one month per year worked.
5. **Fully-loaded statutory cost multiplier: approximately 1.11x gross** today, approximately **1.19x** once severance is provisioned, approximately **1.30x to 1.45x** all-in including market-standard non-statutory items (inference).
6. **The employer-cost to employee-take-home wedge at UGX 5m gross is approximately 1.66:1.**
7. Vertical nomination: **NGO and donor-funded programme compliance.** Runner-up: coffee and cocoa export traceability under EUDR.
8. The deciding factor is hireable domain credibility. Kampala has a deep, affordable pool of donor-grant compliance and internal-audit professionals. It has no pool of people who can get a pre-revenue vendor through a BoU-supervised bank's vendor onboarding.
9. **A co-founder is required, not an employee.** Profile: Ugandan, 35 to 50, commercial, with an existing institutional rolodex.
10. The rating is low because of what has not been done, not because of what cannot be done.

> **Note from the COO:** this report's vertical nomination is **superseded**. HR flagged the donor-funding risk itself and instructed verification; the CFO independently verified an approximately 66% cut to Uganda's USAID programme, EUR 2bn in EU cuts and GIZ suspensions in Oct 2025. The nomination does not survive that. **Everything else in this report stands and is adopted.** See `COO-DECISION.md`.

---

## 1. The capability gap

### The blunt answer

**The first hire should be nobody.** Not a salesperson, not a domain expert.

### The argument

A salesperson sells a known thing at a known price to a known buyer. This company has none of those three. Hiring a B2B enterprise salesperson into a zero-customer, zero-pricing, zero-reference-account situation produces a predictable sequence: three months learning the product, three months of unsuccessful cold outreach into institutions that will not buy audit-critical software from an unreferenced vendor, and departure at month seven or eight.

The second-order damage is worse. **In a founder-led company the customer discovery loop is the product roadmap.** Outsourcing it at the pre-validation stage permanently severs the founder from the buyer, and a deep-infrastructure engineer who has never spoken to a buyer will then build against a salesperson's paraphrase of a market he has never touched.

There is also a hard local constraint. A B2B enterprise salesperson in Kampala capable of opening doors at supervised financial institutions is among the scarcest and most expensive commercial profiles in the country, and such a person has a functioning career. They do not join a pre-revenue solo-founder company for equity. **You will not be able to hire the good version of this person, and the version you can afford cannot open the doors.**

### Priority order with trigger events

| # | Role | Trigger: hire when X is true | Notes |
|---|------|------------------------------|-------|
| 0 | **None. Founder does discovery.** | Immediate | 30 to 50 recorded buyer conversations in one vertical. Target: 5 written problem statements in the buyer's own words, 3 verbal price reactions |
| 1 | **Commercial co-founder, domain-credible, equity not salary** | Founder has completed 25+ discovery conversations, has identified a single vertical, and can articulate the buyer's problem without using the words "hash chain", "Merkle" or "event sourcing" | Trigger is deliberately after discovery: you cannot recruit a credible commercial co-founder with nothing to show, and you should not want one who joins without evidence |
| 2 | **Design-partner implementation lead / domain expert** (first salaried hire) | Two signed pilots exist with named institutional sponsors | A former grants-compliance manager or internal auditor, not a salesperson. Their job is to make two pilots succeed and translate audit language into product requirements |
| 3 | **B2B enterprise salesperson** | One reference customer is live and referenceable by name, and a repeatable price point has been accepted twice | Before this, they have nothing to sell |
| 4 | **Second backend engineer** | The founder is the bottleneck on paying-customer commitments for two consecutive months | Engineering capacity is not the constraint |
| 5 | **Finance / admin officer** (outsourced first) | Payroll exceeds two employees, or a customer requires audited accounts in vendor onboarding | NSSF, PAYE and LST obligations apply from employee one, but can be bought as a service |
| 6 | **DevOps / SRE** | A contract contains an uptime or data-residency commitment the founder cannot personally honour | Currently a luxury |
| 7 | **Customer success / implementation** | Three or more live customers | Merges with role 2 until then |
| 8 | **Frontend engineer** | Only when a customer has refused to buy for a UI reason, twice | 47 routes already exist. The least defensible hire in the company today |

**Applied cryptography specialist: never hire one.** The primitives (hash chains, Merkle proofs, RFC 3161) are standardised and implemented. What is needed is a one-off external security review before the first institutional sale, purchased as a service.

---

## 2. Compensation benchmarks

### Data quality warning, read before the tables

No credible, methodologically transparent, recent Ugandan technology salary survey was located. This is the most important finding in this section.

| Source | Type | Assessment |
|--------|------|------------|
| Paylab.com Uganda | Self-reported, cleaned of outliers | Best of a weak field. **Sample size and collection date not disclosed.** Ranges appear to represent roughly the middle 80% of respondents |
| Glassdoor Kampala | Self-reported | **Unusable.** Senior Software Engineer in Kampala rests on **3 submissions** as of July 2026 |
| worldsalaries, salaryexplorer, digitalregenesys, nucamp, basketadvisory, maxishr, ugandajobs.online | Aggregator / SEO content | Figures appear modelled, not surveyed, and are mutually inconsistent. **Disregard entirely** |
| UBOS National Labour Force Survey 2021 | Primary, government | Real but far too coarse for professional technology roles, and approximately 5 years old |
| BrighterMonday Uganda salary guide | Sought | **NOT FOUND** with role-level ICT data |
| NCHE / NITA-U salary data | Sought | **NOT FOUND** in accessible form |

**The contradiction, stated plainly.** Glassdoor implies a Kampala senior software engineer earns roughly UGX 673,000 to 882,000/month. Paylab implies a backend developer spans UGX 1.61m to 6.22m/month. Aggregators imply approximately UGX 2.47m/month. These differ by up to an order of magnitude. **No figure here should be used as a negotiating anchor without validating against three live job postings or three candidate conversations in the month you hire.**

### National context anchor (primary source)

UBOS National Labour Force Survey 2021: approximately **50% of Ugandans in paid employment earn UGX 200,000 or less per month** (data year 2021). At the FX rate above, approximately USD 53/month. Every technology figure below sits in the extreme upper tail of the Ugandan wage distribution, with retention and internal-equity implications.

### Technology roles

**Source: Paylab.com Uganda, Information Technology. Gross monthly UGX including bonuses. Sample size and date not disclosed. Accessed 29 Aug 2026.** Category average UGX 3,408,800/month; spread UGX 1,492,500 to 5,791,955 (stated as 80% of workers).

| Role | Gross monthly UGX | USD/month |
|------|-------------------|-----------|
| Backend Developer | 1,612,014 to 6,221,506 | 427 to 1,650 |
| Frontend Developer | 1,477,928 to 5,047,758 | 392 to 1,338 |
| Python Programmer | 1,556,842 to 5,328,225 | 413 to 1,413 |
| Java Programmer | 1,622,630 to 6,427,163 | 430 to 1,704 |
| DevOps Engineer | 1,985,933 to 7,271,434 | 527 to 1,928 |
| Systems Administrator | 1,353,591 to 4,026,186 | 359 to 1,068 |
| Database Administrator | 1,588,729 to 4,953,991 | 421 to 1,313 |
| Lead Developer | 2,793,341 to 8,786,944 | 741 to 2,330 |
| Solution Architect | 2,504,678 to 8,863,303 | 664 to 2,350 |
| IT Architect | 2,365,835 to 9,607,969 | 627 to 2,547 |
| IT Project Manager | 2,041,043 to 6,470,123 | 541 to 1,715 |

### Seniority bands

**NO VERIFIED SOURCE for the seniority split.** Paylab publishes only a single range per title and no located Ugandan survey publishes junior/mid/senior bands for software roles. Junior is placed at roughly the sourced lower bound, senior at roughly the upper bound, with an upward adjustment at the senior end reflecting the global remote market.

| Role | Junior (0-2y) | Mid (3-5y) | Senior (6y+) | Senior USD/mo |
|------|---------------|------------|--------------|---------------|
| Backend engineer | 1.5m to 2.5m | 2.5m to 4.5m | 4.5m to 8.0m | 1,193 to 2,121 |
| Frontend engineer | 1.4m to 2.2m | 2.2m to 3.8m | 3.8m to 6.5m | 1,008 to 1,723 |
| DevOps / SRE | 1.9m to 2.8m | 2.8m to 5.0m | 5.0m to 8.5m | 1,326 to 2,254 |

**Critical caveat.** An engineer capable of maintaining this system is not priced by the Kampala local market. They are priced by the global remote market. Treat UGX 8m/month as the ceiling of what a **local employer** typically pays, and simultaneously as roughly half of what that person can earn on a foreign remote contract.

### Commercial, compliance and finance roles

**Source: Paylab.com Uganda, Banking. Accessed 29 Aug 2026.** Category average UGX 2,594,030/month; spread UGX 1,056,081 to 4,525,923.

| Role | Gross monthly UGX | USD/month |
|------|-------------------|-----------|
| Internal Auditor | 1,757,644 to 4,532,003 | 466 to 1,202 |
| Compliance Specialist | 1,705,837 to 5,033,603 | 452 to 1,335 |
| Risk Specialist | 1,593,266 to 4,235,177 | 422 to 1,123 |
| Relationship Manager | 1,634,271 to 4,068,355 | 433 to 1,079 |
| Financial Analyst | 1,707,315 to 4,097,520 | 453 to 1,086 |

**Paylab Commerce category average is UGX 2,113,770/month with no role-level breakdown.** Ugandan sales compensation could not be sourced at role level.

| Role | Position | Working assumption |
|------|----------|--------------------|
| **B2B enterprise salesperson, financial institutions** | **NO VERIFIED SOURCE** | **Estimate:** base UGX 5m to 9m/month (USD 1,326 to 2,386) plus commission at 30-50% of OTE. Reasoning: competes with bank relationship-manager and telco enterprise key-account roles, sits above the Banking ceiling of UGX 4.53m because it carries quota risk and a network. **Verify against live postings** |
| **Customer success / implementation consultant** | No direct source. Nearest: IT Project Manager, Internal Auditor | **Estimate:** UGX 3m to 6m/month (USD 795 to 1,591) |
| **Compliance / audit domain expert** | Sourced: Compliance Specialist, Internal Auditor ranges | Use the sourced range. For a genuinely senior person (ACCA or CPA(U), 10y+, ex-Big 4 Kampala or ex-donor compliance director), **estimate** UGX 6m to 10m/month, above the Paylab ceiling. **Not verified** |
| **Finance / admin officer** | Nearest: Financial Analyst | Junior bookkeeping **estimate** UGX 800,000 to 1.8m/month. Qualified: use sourced Financial Analyst range |

### Does equity work as compensation in Uganda?

**Sourced position.** Accion's guide to employee stock options in emerging markets states that in sub-Saharan Africa ESOPs remain uncommon, arrangements are often limited to founders and top executives, and there is frequently a lack of understanding of how options work. TechCabal (June 2025) describes the practice as still maturing, with regulatory and tax treatment across African jurisdictions still evolving.

**No Uganda-specific or Kenya-specific survey measuring employee preference between cash and equity was located. That data does not appear to exist in accessible form.**

**Assessment (inference):**

- **Equity does not function as compensation for rank-and-file Ugandan hires.** For an employee whose alternative is a UGX 4m salary at a bank or telco, an option grant in a pre-revenue company with no local secondary market, no precedent of local startup exits producing employee liquidity, and unclear tax treatment on exercise, is not perceived as compensation. It is perceived as a discount request, and it will cost you the candidate.
- **Equity works for exactly one category:** a co-founder with independent financial means who understands the instrument and is buying upside rather than accepting a discount.
- **Practical guidance:** pay cash at market for employees. Reserve 10-15% for an option pool meaningful only post-Series-A. To close a co-founder, use founder shares with a 4-year vest and 1-year cliff, not options. **No verified source on Ugandan tax treatment of share option exercise. Verify with URA or a Kampala tax practice before granting anything.**

---

## 3. Talent availability

### Graduate output: a documented gap

**No published Ugandan graduate-output numbers by discipline were obtained.** Three documents were identified and failed to retrieve:

- NCHE, *State of Higher Education and Training in Uganda 2020/21* (unche.or.ug). PDF exceeded fetch size limit. **Almost certainly contains enrolment and graduate figures by discipline cluster. Download manually.**
- NCHE, *State of Higher Education Report 2019 to 2022*. Not retrieved.
- NITA-U, *ICT Skills and Training Needs Assessment Final Report* (empowerconsult.co.ug). Not machine-readable. **Likely the single most relevant document. Read it directly.**

**NO VERIFIED SOURCE for annual Ugandan CS/software graduate numbers.**

**Practical implication regardless of the number:** graduate volume is not the constraint. Uganda produces enough entry-level developers that junior hiring is easy and cheap. The constraints are at the senior end and on the commercial side, where volume is irrelevant.

### The rare skills

| Skill | Availability in Kampala | Assessment |
|-------|------------------------|------------|
| **Applied cryptography** | Effectively zero as a hireable local pool | Do not attempt to hire it. Buy an external audit instead |
| **Event-sourcing architecture** | Very thin. Rare even in large markets | The founder already has it. Genuinely defensible by scarcity, and also why a second backend engineer will take 4 to 6 months to become productive on this codebase |
| **Enterprise B2B compliance sales** | Thin, expensive, concentrated in incumbent employers (banks, telcos, enterprise resellers, Big 4) | **The binding constraint.** No amount of engineering budget substitutes |
| **Donor-grant compliance and internal audit** | **Deep and affordable.** Large concentration of INGO country offices, programme implementers and Big 4 advisory practices | Priced in the sourced Banking range, UGX 1.7m to 5.0m/month |

### Poaching risk: real and severe

Crossover advertises remote software engineering roles targeted at Kampala. Reporting located in search indicates Kampala-targeted remote roles advertised at up to USD 200,000/year, mid-level remote frontend at approximately USD 3,000/month, and Kampala Python developers at roughly USD 700 to 1,000/month locally rising to USD 1,800 to 3,000 with ML/AI specialisation. **The live Crossover listings page returned no readable content, and the secondary sources are low-quality SEO content. Treat the specific numbers as unverified. Treat the direction as certain.**

**The arithmetic:** the top of the sourced local senior band is approximately UGX 8m to 9.6m/month (USD 2,100 to 2,550). A competent Ugandan senior engineer on a foreign remote contract can plausibly earn USD 3,000 to 6,000+/month tax-advantaged as a contractor. **You cannot win a salary contest against a USD-denominated remote employer and should not try.** Retention levers are equity meaningfulness (weak), problem interest, and the founder's technical reputation. **Assume any senior engineer you hire is continuously recruitable and plan for 18 to 24 month tenure.**

### Is domain expertise hireable?

| Domain | Hireable? | From where |
|--------|-----------|------------|
| **Donor grant audit and programme compliance** | **Yes, readily** | INGO country offices, donor-funded implementers, Big 4 Kampala advisory, internal audit functions. Deepest and most affordable |
| **Banking supervision** | **Marginally** | BoU alumni and bank compliance heads exist but are few, senior, well-paid and risk-averse. Accessible as advisors or non-executive directors, not hires |
| **Export compliance / certification** | **Yes, moderately** | UCDA alumni, exporter QA and certification managers, sustainability-scheme auditors |
| **Land records, judiciary, healthcare regulation** | Sparse, mostly public-sector | Not a viable staffing base for a startup |

---

## 4. Employment law and cost of employment

**Status stamp: as of 29 August 2026.** Re-verify before relying on any of this contractually.

### The Employment (Amendment) Act, 2025

**Confirmed: assented by the President on 29 April 2026. Commencement not gazetted**, meaning assented but not yet in force. Await the official commencement notice.

Sources: MMAKS Advocates legal alert (May 2026), corroborated by KTA Advocates, Engoru Mutebi Advocates and Afriwise. **These are law-firm alerts, strong secondary authority, not the gazetted primary text.**

| Area | Change | Section |
|------|--------|---------|
| **Severance allowance** | Standardised at **one month's salary per year worked**, replacing the prior discretionary approach. Grounds expanded to redundancy, physical incapacity, and termination by a labour officer for wage non-payment | ss. 86, 88 |
| **Casual workers** | Maximum **six months** continuous employment. Layoff-and-rehire does not reset the clock | s. 34A |
| **Probation** | Payment in lieu of notice extended from seven days to **one month**. **Automatic confirmation** if the employer keeps paying after probation expires without formal extension | s. 66 |
| **Pre-dismissal hearing** | Mandatory. Employee gets **five working days** to prepare a defence. Non-compliance triggers automatic liability of **four weeks' net pay regardless of the merits** | s. 65 |
| **Unfair dismissal remedy** | Basic compensatory order raised from four to **eight weeks' wages** | ss. 76, 77 |
| **New dismissal grounds** | Abscondment (30+ consecutive days), forged documents, conduct adversely affecting the business | s. 64A |
| **Statutory definitions** | Unfair dismissal and wrongful dismissal defined | ss. 65A, 65B |
| **Harassment** | Policy must be displayed conspicuously. Employer/agent intimidation criminalised | ss. 6, 6A |
| **Childcare / breastfeeding** | Employer must provide time, space or facility, children aged 3 to 36 months | s. 56A |
| **Dispute resolution** | New three-month threshold. Only the complainant may refer to the Industrial Court if the labour officer has not resolved. Arbitration removed as an individual dispute mechanism | s. 92(7) |
| **Migrant workers** | Minister may gazette job categories closed to non-citizens; employment in those without an exemption certificate is a criminal offence | Part IXA |

**Maternity and paternity leave were not reported as amended.** Could not be confirmed either way.

**Action item:** severance at one month per year worked is a material new balance-sheet item. It is contingent, not payable on every exit, but for a startup that may need to shed staff it is exactly the scenario in which it bites.

### Base Employment Act, Cap 226 (Act 6 of 2006)

| Item | Provision | Section | Source quality |
|------|-----------|---------|----------------|
| Definition of employee | "any person who has entered into a contract of service or an apprenticeship contract" | s. 2 | Quoting the Act |
| Contract of service | "any contract, whether oral or in writing, whether express or implied, where a person agrees in return for remuneration, to work for an employer" | s. 2 | Quoting the Act |
| Hours of work | Section exists, **exact hours not verified** | s. 53 | Section number only |
| **Annual leave** | **21 days** paid plus public holidays | s. 54 | Secondary. **Not verified against primary text.** Current gazetted public holiday count not verified |
| Sick pay | Section exists, **entitlement not verified** | s. 55 | Section number only |
| **Maternity leave** | **60 working days** fully paid, at least four weeks after childbirth or miscarriage | s. 56 | Secondary. **Not verified against primary text** |
| **Paternity leave** | **4 working days** paid per year | s. 57 | Secondary. **Not verified against primary text** |
| Probationary contracts | Section exists, maximum length **not verified**. See s. 66 amendment | s. 67 | Section number only |

**Notice periods, s. 58(3)(a), minimum:**

| Service | Minimum notice |
|---------|----------------|
| 6 months to 1 year | 2 weeks |
| 12 months to 5 years | 1 month |
| 5 to 10 years | 2 months |
| 10 years or more | 3 months |

Contracts may provide longer. **Not verified against primary text; the official Employment Act PDF at bills.parliament.ug is a scanned image and could not be text-extracted.**

**Note:** the Court of Appeal has reaffirmed that an employer may terminate without giving a reason by issuing notice or payment in lieu. **The 2026 amendment's mandatory pre-dismissal hearing at s. 65 materially narrows this. Take Ugandan employment counsel before any termination once the amendment commences.**

### NSSF

| Item | Rate | Source |
|------|------|--------|
| **Employee contribution** | **5%** of gross monthly wage | NSSF Uganda, nssfug.org |
| **Employer contribution** | **10%** of gross monthly wage | NSSF Uganda, nssfug.org |
| **Total** | **15%** | |
| **Who must register** | **Every employer, irrespective of the number of employees.** The prior five-employee threshold was removed | NSSF (Amendment) Act 2022, ULII and nssfug.org |
| Remittance deadline | 15th of the following month | Secondary. **Not verified against NSSF primary** |

**This applies from employee number one. There is no small-employer exemption.**

### PAYE (URA), resident individuals, monthly

**Source: ura.go.ug/en/domestic-taxes/paye-rates/, accessed 29 Aug 2026. The URA page does not state an effective date.**

| Monthly chargeable income (UGX) | Tax |
|--------------------------------|-----|
| 0 to 235,000 | Nil |
| 235,000 to 335,000 | (Income - 235,000) x 10% |
| 335,000 to 410,000 | (Income - 335,000) x 20% + 10,000 |
| 410,000 to 10,000,000 | (Income - 410,000) x 30% + 25,000 |
| Above 10,000,000 | [(Income - 410,000) x 30% + 25,000] + [(Income - 10,000,000) x 10%] |

Annual exemption threshold: UGX 2,820,000.

**Unresolved:** whether employee NSSF contributions are deductible in computing chargeable income for Ugandan PAYE. The arithmetic below treats them as **not deductible**. **Verify with URA or a Kampala tax adviser. This materially changes take-home.**

### Local Service Tax

Introduced by the Local Governments (Amendment) (No. 2) Act, 2008. Payable by persons in gainful employment with monthly take-home exceeding UGX 100,000. Graduated from UGX 5,000/year at the bottom to a **maximum of UGX 100,000/year** for monthly income above UGX 1,000,000. Collected by the employer, remitted to the local government in four equal instalments.

Sources: KCCA Local Service Tax FAQs (**dated February 2017, approximately 9 years old, verify current bands**), PwC Worldwide Tax Summaries, TASLAF Advocates.

**Employee-borne, not an employer cost, but an employer administrative obligation.** For any technology hire it is the flat maximum, approximately UGX 8,333/month.

### Workers' compensation

**Workers Compensation Act, Cap 225.** All employers in Uganda are legally required to carry Workers' Compensation Insurance, covering all employees regardless of position or salary. Sources: Insurance Regulatory Authority of Uganda, CIC Uganda.

**NO VERIFIED SOURCE for the premium rate as a percentage of payroll. Estimate approximately 0.5% to 1.5% for low-hazard office work; 1.0% is used below.** Reasoning: office-based professional occupations are the lowest hazard class everywhere. **Obtain three broker quotes before budgeting.**

### Employee vs independent contractor

**Tax:** payments to independent contractors in Uganda attract a **6% withholding tax**. For **professional fees there is no threshold**; the 6% applies irrespective of transaction value, unlike other goods and services which carry a UGX 1,000,000 threshold. Source: PwC Worldwide Tax Summaries.

**Legal test:** Ugandan courts apply the **control test** and the **integration test**. The High Court has weighed control of work, place of work, integration, and the nature of the relationship, and has distinguished consultancy from employment on the basis that contractors are not entitled to annual leave, fixed working hours or sick leave, and are paid for work delivered.

**Misclassification risk (inference).** Running early hires as contractors is the default startup instinct and here it is specifically dangerous:

1. **The control and integration tests will fail on facts.** A full-time engineer working the founder's hours, on the founder's roadmap, in the founder's codebase, with no other clients, is an employee whatever the contract says.
2. **The consequence is retrospective and cumulative:** unremitted PAYE, unremitted employee and employer NSSF (15%), plus penalties and interest, back to the start. NSSF now covers every employer irrespective of size, so there is no threshold to hide behind.
3. **The 2026 amendment worsens it.** The six-month casual cap (s. 34A) and automatic confirmation on probation (s. 66) both operate against employers using flexible labels to avoid permanence, and the new severance attaches to reclassified service.
4. **Reputationally it is fatal to the pitch.** You intend to sell tamper-evident compliance software to audited institutions. A vendor with a URA misclassification finding cannot survive vendor due diligence. **This is a sales risk, not just a tax risk.**

**Recommendation:** genuine contractors only for genuinely discrete, deliverable-based work with multiple clients (security audit, design sprint, legal, accounting). Anyone full-time goes on a proper employment contract from day one.

### Fully-loaded cost multiplier

Let **G** = contractual gross monthly salary. PAYE, employee NSSF and LST are deducted from G and are employee-borne.

**Tier 1, statutory employer cash cost**

| Component | Rate | Cost per 1.0 of G |
|-----------|------|-------------------|
| Gross salary | 1.000 | 1.0000 |
| NSSF employer | 10% of gross | 0.1000 |
| Workers' compensation | ~1.0% *(estimate)* | 0.0100 |
| Local Service Tax | employee-borne | 0.0000 |
| PAYE | employee-borne | 0.0000 |
| **Statutory floor** | | **1.1100** |

**Tier 2, plus severance provision**

| Component | Arithmetic | Cost per 1.0 of G |
|-----------|-----------|-------------------|
| Tier 1 subtotal | | 1.1100 |
| Severance accrual, 1 month per year | 1 / 12 = 0.0833 | 0.0833 |
| **Provisioned** | | **1.1933** |

Severance is contingent rather than payable on every exit, so 1.1933 is a **prudent provisioning figure, not a guaranteed cash cost.** It becomes operative only once commencement is gazetted.

**Tier 3, realistic all-in (INFERENCE, not statutory)**

**NO VERIFIED SOURCE for these components.**

| Component | Per 1.0 of G | Reasoning |
|-----------|--------------|-----------|
| Tier 2 subtotal | 1.1933 | |
| Private medical insurance | 0.03 to 0.06 | Not statutory, but table stakes for competitive technology hires. Verify with a Kampala broker |
| Equipment, connectivity, workspace | 0.04 to 0.08 | Laptop amortised, redundant internet (a real cost in Kampala), desk |
| Recruitment, amortised | 0.03 to 0.08 | Agency fees typically around one month's salary, amortised over an assumed 18 to 24 month tenure |
| Paid absence productivity cost | 0.08 to 0.10 | 21 days annual leave plus public holidays as a share of working days. Not incremental cash, but real capacity cost |
| **Realistic all-in** | **1.30 to 1.45** | |

> **Use 1.11 for cash-flow modelling. Use 1.20 for provisioning. Use 1.35 when deciding whether you can afford a hire.**

### Worked example: UGX 5,000,000 gross per month

| Line | UGX/month | USD/month |
|------|-----------|-----------|
| Contractual gross (G) | 5,000,000 | 1,326 |
| Less PAYE: (5,000,000 - 410,000) x 30% + 25,000 | (1,402,000) | (372) |
| Less employee NSSF at 5% | (250,000) | (66) |
| Less Local Service Tax (100,000/yr / 12) | (8,333) | (2) |
| **Employee net take-home** | **3,339,667** | **885** |
| | | |
| Employer: gross | 5,000,000 | 1,326 |
| Employer: NSSF at 10% | 500,000 | 133 |
| Employer: workers' comp at ~1% *(estimate)* | 50,000 | 13 |
| **Employer statutory cash cost** | **5,550,000** | **1,472** |
| Plus severance accrual (G / 12) | 416,667 | 110 |
| **Employer provisioned cost** | **5,966,667** | **1,582** |
| Realistic all-in at 1.35x G | ~6,750,000 | ~1,790 |

> **The wedge: 5,550,000 / 3,339,667 = approximately 1.66.**
>
> For every UGX 1.00 the employee actually receives, you spend UGX 1.66, or UGX 2.02 at the realistic all-in figure. This is the number that should govern headcount decisions, and the one founders consistently omit.

*Assumes employee NSSF is not deductible for PAYE. See the PAYE section.*

---

## 5. Vertical assessment: the talent and credibility lens

**The deciding question:** not "who has the problem" but **in which industry can this company hire, or already access, the domain credibility to be trusted with an institution's audit-critical records.** Enterprise compliance software is bought on trust. A solo technical founder with no reference customer has zero institutional trust.

| Vertical | Hireable domain experts | Sales cycle | Buying mode | Can staff a tender? | Verdict |
|----------|------------------------|-------------|-------------|---------------------|---------|
| **NGO / donor-funded programmes** | **Deep and affordable.** Grants managers, donor compliance officers, internal auditors, Big 4 alumni. UGX 1.7m to 5.0m/mo | ~3 to 9 months *(inference)* | Mixed. Country-office discretionary budgets are relationship-driven; large programmes tender. **The relationship-driven half is reachable** | Partially, and not required for the entry motion | **Nominated (superseded, see COO note)** |
| **Coffee / cocoa export, EUDR** | **Real, smaller.** UCDA alumni, exporter QA and certification managers | ~2 to 6 months *(inference)*, compressed by deadline | **Relationship-driven, not tender.** Buyer list countable: licensed exporters, dozens not thousands | Not required | Runner-up |
| **SACCOs / microfinance (UMRA)** | **Excellent and cheap.** Ex-UMRA, MFI operations managers | Short per deal | Relationship-driven, but the scalable motion is regulator-mandated, i.e. a government tender | **No** | Rejected **on ability to pay**, not on talent |
| **Banks (BoU supervised)** | Thin at the level required, and immobile | 12 to 24 months+ | Procurement-driven with vendor due diligence, security certification, audited financials | **No** | **Rejected, hard.** A pre-revenue single-founder company cannot pass bank vendor onboarding |
| Insurance (IRA) | Moderate | 9 to 18 months *(inference)* | Procurement-driven | No | Rejected, same structural problem, smaller market |
| Land records / judiciary / PPDA | Sparse, public-sector, low mobility | 18 months+ | Public tender | **No** | Rejected |
| Healthcare / pharma (NDA) | Thin for records-compliance specifically | Long | Regulator-driven | No | Rejected |

**Note the SACCO/microfinance row.** HR rejected it on ability to pay, **not on talent availability**, which was rated "excellent and cheap". That row is what makes the COO's eventual money-lender pick staffable. See `COO-DECISION.md`.

### Why the NGO nomination was made

It is the only vertical where the required domain credibility is both **hireable** and **affordable**. A former grants-compliance manager from a large INGO country office arrives with the vocabulary, the audit scars and a personal network of programme finance directors across Kampala. In every other vertical the equivalent person either does not exist locally, will not move, or costs more than the company can raise.

Product fit with no new engineering, mapping to a donor audit:

- "Prove this expenditure record was not created after the audit was announced" maps to tamper-evident hash chain and TSA anchoring. **The killer demo**
- "Show the complete file for beneficiary X: contract, receipt, ID, signature" maps to mandatory-document compliance checking
- "Show your data-protection and retention posture" maps to retention plus export and erasure
- "Let our external auditor verify without our staff mediating" maps to the public verification page

**The risk HR flagged itself:** donor funding flows to Uganda have been volatile and the 2025 restructuring of major bilateral aid channels contracted implementer budgets significantly. **"Verify current donor programme budget levels in Uganda before committing."** The CFO did. It did not survive.

---

## 6. Verdict

### First three hires

| # | Role | Band | Trigger | If skipped |
|---|------|------|---------|------------|
| **1** | **Nobody. Founder runs discovery.** | UGX 0. Cost is founder time: 3 to 4 months at ~60% capacity | Immediate | **This is the one that kills the company.** Building further against zero demand evidence adds to a codebase that is already the largest unvalidated asset on the books. Every month of delay makes the eventual pivot more expensive and the founder's attachment to the current architecture harder to break |
| **2** | **Commercial co-founder, domain-credible** | **Equity, not salary.** 25% to 40%, 4-year vest, 1-year cliff. Cash only once funded, and then modest | 25+ conversations complete, one vertical nominated, and the founder can state the buyer's problem without using the word "Merkle" | The company has world-class engineering pointed at nothing, permanently. A salaried hire will not substitute: you cannot pay market rate, and the institutional relationships that constitute the entire value of this profile are not lent out for a salary |
| **3** | **Design-partner implementation lead** (first salaried employee) | Sourced band UGX 1.7m to 5.0m/mo gross. At UGX 4m gross: statutory employer cost ~UGX 4.44m/mo, realistic all-in ~UGX 5.4m/mo | Two signed pilots with named institutional sponsors | Pilots fail on implementation rather than product. The founder runs two institutional deployments alongside engineering, does both badly, and converts two prospective reference customers into two references that will not vouch for you. **In a trust-sold category, a failed pilot is worse than no pilot** |

**Deliberately not in the top three:** any engineer, any DevOps or SRE, any generic salesperson, any frontend hire. Each is a plausible-sounding way to spend money without reducing the risk that is actually killing the company.

### The founder's gap assessment

**Must be learned personally, cannot be delegated:**

| Capability | Why | Time to competence |
|------------|-----|--------------------|
| **Buyer discovery** | The output is not a report, it is a rewired intuition about who has the pain and what they call it. That intuition has to live in the person making product decisions. Delegating it produces a document nobody acts on | 8 to 12 weeks concentrated |
| **Articulating the product in buyer language** | Every subsequent hire, investor conversation and partnership depends on it. "Tamper-evident event-sourcing platform" is not a sentence a grants director can act on | 4 to 8 weeks, and it emerges from discovery rather than preceding it |
| **Pricing** | A strategic position, not a task | Emerges from discovery |

**Must be hired or bought:**

| Capability | Why | Route |
|------------|-----|-------|
| **Institutional relationships and domain credibility** | Cannot be learned. Accumulated over a decade inside the sector. A founder cannot become a person a programme finance director has known for eight years | **Co-founder** |
| **Enterprise sales process mechanics** | Learnable but slow, and the founder will be bad at it during the period that matters most | Hire, after validation |
| **Ugandan payroll, tax and employment compliance** | Pure execution, well-supplied locally | Buy as a service |
| **Security certification for vendor due diligence** | Specialist, episodic | Buy as a service |

**Which is faster?** For discovery, **learning is faster**, because hiring a discovery function requires a hire the company cannot yet attract or afford. For credibility, **hiring is faster and learning is impossible.** That asymmetry is the whole of the answer, and it is why the sequence is discovery, then co-founder, then employee.

### Is a co-founder required?

**Yes, unambiguously. Not a first employee.**

Three facts compel it. The company cannot pay a market salary to anyone with the required network, and equity does not work as a discount mechanism for employees in this market. The asset being acquired is a personal rolodex, and people do not deploy their own accumulated reputation collateral on behalf of an employer they can walk away from; they deploy it when they own the outcome. And the failure mode of a salaried commercial hire in a pre-validation company is departure at month seven or eight, survivable for them and close to fatal for you.

**Profile:**

- Ugandan national, Kampala-based, approximately 35 to 50
- 10 to 15 years inside the chosen vertical, ending in a role with **budget authority or audit authority**, not a business development title
- **Comes with a named list of 30+ people who will take their call.** This is testable at interview. Ask for the list. If they cannot produce it, they are not the profile
- Commercially motivated, not technically curious. The last thing this company needs is a second person who enjoys the architecture
- Has 12 to 18 months of personal runway or tolerable part-time consulting income. If they need a salary from month one, they are the wrong person for a pre-revenue equity deal
- **Terms:** 25% to 40% equity, 4-year vest, 1-year cliff, written role split, documented decision rights over pricing and roadmap

**Where to find them:** alumni networks of Big 4 Kampala advisory practices and the finance and compliance functions of large donor-funded programme implementers. A warm-introduction search of 20 to 30 conversations, not a job posting.

### The people risk most likely to kill this company

**Primary: the founder hires an engineer instead of doing sales.**

The mechanism is specific and predictable. Discovery is uncomfortable, unstructured, status-threatening and produces no artefact for weeks. Engineering is comfortable, legible, immediately rewarding, and the founder is excellent at it. Under uncertainty, humans revert to competence. The founder will feel the commercial gap, accept intellectually that a hire is needed, and hire the person he knows how to evaluate: an engineer. Burn approximately doubles, at an all-in cost of roughly UGX 5m to 11m/month per senior engineer, demand evidence stays at exactly zero, and runway is consumed producing more unvalidated code.

**This is not hypothetical. It is the modal outcome for a solo technical founder with a large finished product and no customers, and nothing in the current situation counteracts it.**

**Secondary: the commission-only salesperson.** Founder recognises the commercial gap, cannot afford a real salesperson, hires on commission-only or a low base. That person cannot open institutional doors, because the ones who can do not work commission-only. They produce nothing in four months and depart. The founder concludes "sales doesn't work for us", which is the wrong lesson, and emerges nine months poorer and materially more demoralised.

**Tertiary: single point of failure.** One person holds 100% of the knowledge of a 43,500-line event-sourced system with cryptographic invariants. No bus factor, no code review, no second person who can honestly answer a customer's security questionnaire. **Every institutional buyer's vendor due diligence will surface this, and for audit-critical records software it is a legitimate reason to decline.** Not solved by hiring an engineer today; solved by having a customer worth de-risking for. But it belongs on the risk register.

### Rating: 3/10, defended

**What earns the 3 rather than 1 or 2:**

- The technical asset is genuine and unusually deep. Correctly implemented hash-chained append-only storage with Merkle inclusion proofs, sealed epochs and RFC 3161 anchoring is not commodity work
- Uganda cost structure gives an unusual amount of runway per unit of capital. Time to correct the mistake exists, which is not true in most markets
- The product is genuinely built. If discovery finds the right buyer, time-to-first-pilot is weeks, not quarters

**What caps it at 3:**

- **Zero demand evidence. Not weak evidence. Zero.** On the single dimension that determines survival, the information content of this business is nil. No rating above 4 is defensible regardless of engineering quality
- **The founder profile is the inverse of what the sale requires.** A structural, not incidental, mismatch
- **43,500 lines of unvalidated code is a negative on this axis.** On an execution-viability measure, finished-but-unvalidated is worse than unfinished
- **The hire that would fix this is the hire the company cannot make.** The company needs the co-founder to get the evidence and the evidence to get the co-founder. That circularity is only broken by the founder doing discovery himself, which is exactly the thing he is least likely to do
- **Talent economics run against retention at the senior end**
- **Loaded cost is higher than the founder almost certainly assumes.** A 1.66:1 wedge means affordable headcount is roughly 40% below naive expectation

**What moves the rating.** 25 completed buyer conversations in a single nominated vertical with three written problem statements in the buyer's own words moves this to **5**. A signed design-partner pilot with a named institutional sponsor moves it to **6**. A credible commercial co-founder joining moves it to **7**. **All three are achievable within four months and none requires a shilling of hiring spend.** The rating is low because of what has not been done, not because of what cannot be done.

---

## Sources

All accessed 29 August 2026.

**Employment law:** MMAKS Advocates legal alert on the Employment (Amendment) Act 2025 (`mmaks.co.ug`), KTA Advocates, Engoru Mutebi Advocates, Afriwise; MMAKS commentary on s.58(3) notice periods and on termination without reason (2021, 2023); Kampala Associated Advocates; `ugandalaws.com` Employment Act 2006 (s.2 definitions; ss.53-67 paywalled); Parliament of Uganda Employment Act 2006 PDF (**scanned images, not text-extractable**); ULII consolidated Employment Act (**HTTP 403, not retrieved**); CXC Global Uganda leave guide; WageIndicator / Africapay Uganda.

**Social security:** NSSF Uganda membership page; NSSF (Amendment) Act 2022 PDF; ULII NSSF (Amendment) Act 2022.

**Tax:** URA PAYE rates page (**no effective date stated**); URA PAYE overview; KCCA Local Service Tax FAQs (**February 2017**); PwC Worldwide Tax Summaries Uganda (Individual: Other taxes; Corporate: Withholding taxes); PwC Uganda on professional practitioners' tax obligations; TASLAF Advocates; ULII Local Government (Amendment) (No. 2) Act 2008.

**Employee vs contractor:** ENSafrica; Daily Monitor on a High Court PAYE direction; CXC Global Uganda.

**Workers' compensation:** Insurance Regulatory Authority of Uganda (Act text); CIC Uganda; Uganda Insurers Association *Uptake of Workers Compensation Insurance* May 2025 (**listed but not opened; recommend reading for premium rates**).

**Compensation:** Paylab.com Uganda IT, Banking and Sales categories (**sample size and date not disclosed**); Glassdoor Kampala (**n=3, rejected as unusable**); Wise and XE USD/UGX. **Opened and rejected as modelled rather than surveyed:** worldsalaries.com, salaryexplorer.com, digitalregenesys.com, nucamp.co, basketadvisory.com, maxishr.com, ugandajobs.online, employuganda.com, careerlead.ai, tboisl.com.

**Labour market and education:** UBOS National Labour Force Survey 2021 main report; Daily Monitor on NLFS earnings distribution; NCHE *State of Higher Education and Training 2020/21* (**exceeded fetch size limit, download manually**); NCHE *State of Higher Education 2019-2022* (**not retrieved**); NITA-U *ICT Skills and Training Needs Assessment* (**not machine-readable, highest-priority document for manual reading**); Makerere CoCIS BSc Computer Science; Crossover remote jobs Kampala (**no readable content, salary figures NOT verified**).

**Vertical assessment:** HQTS and PSQR on EUDR timelines; Coolset EUDR guidance (June 2026); TracexTech EUDR coffee guide; African Exponent; UMRA SACCO licensing page; UMRA licensed Tier 4 institutions **as of March 2022** (**most recent published list located; current counts NOT obtained**).

**Equity and ESOPs:** Accion guide to employee stock options in emerging markets; TechCabal *Next Wave: ESOPs and the future of employee ownership* (9 June 2025); Startup.Africa ESOP guide.

---

## Documented gaps

1. Bank of Uganda official USD/UGX rate. Wise mid-market used instead.
2. Ugandan graduate output by discipline. Three primary documents identified, none readable within tooling limits. All three downloadable manually. **Partially closed after this report:** a local copy of NCHE, *The State of Higher Education and Training in Uganda* **2019/20**, is at `docs/sources/NCHE-state-of-higher-education.txt`. Caveats: it is the 2019/20 edition, not the 2020/21 one sought; it reports **enrolment by discipline, not graduate output**; and the data is approximately 6 years old. Its finding at s.1.3.3 is that enrolment in science and technology rose from 36.7% (2018/19) to 38.1% (2019/20), with "the bigger proportion of technology enrolment ... pursuing ICT related technologies". **No ICT graduate count. The gap is narrowed, not closed.**
3. Role-level Ugandan sales compensation. Does not appear to be published.
4. Workers' compensation premium rate as a percentage of payroll. Estimated at 1.0%. Obtain broker quotes.
5. **Whether employee NSSF is deductible for Ugandan PAYE.** Assumed not deductible. Materially affects take-home arithmetic. **Verify with URA.**
6. Ugandan tax treatment of share option exercise. Not researched. Verify before any grant.
7. Gazetted primary text of the Employment (Amendment) Act 2025. Four concurring law-firm alerts relied on instead.
8. Current Ugandan public holiday count.
9. Kampala innovation hub and developer community inventory. Not researched.
10. **Current donor funding levels to Uganda post-2025 aid restructuring.** Material to the section 5 nomination. **The CFO subsequently verified this and the nomination did not survive.**
11. Current UMRA-licensed SACCO counts. Most recent published list is March 2022.
12. NSSF remittance deadline and late-payment penalty. Secondary sources only.
