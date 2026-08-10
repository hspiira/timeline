"""Page sections — one function per visual section.

Each function returns a self-contained HTML string fragment.
Add a new section here; compose it in ``root.py``.  No section knows about
any other; dependency direction is always: root → sections → components.
"""

from __future__ import annotations

from ._components import (
    btn,
    card_with_header,
    chip,
    delivery_card,
    icon,
    industry_card,
    kpi_row,
    phase_row,
    pillar_card,
    section_header,
)

# ---------------------------------------------------------------------------
# Section-specific CSS (injected via page_shell extra_head)
# ---------------------------------------------------------------------------

SECTIONS_CSS = """
<style>
  /* ── Hero ──────────────────────────────────────────────────── */
  .hero {
    padding: 120px 0 80px;
    position: relative; overflow: hidden;
  }
  .hero-grid {
    position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(59,130,246,.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(59,130,246,.035) 1px, transparent 1px);
    background-size: 56px 56px;
    mask-image: radial-gradient(ellipse 70% 60% at 50% 40%, black, transparent);
    pointer-events: none;
  }
  .hero-inner {
    position: relative;
    display: flex; flex-direction: column; gap: 24px;
    max-width: 760px;
  }
  .hero h1 em {
    font-style: normal; color: var(--blue);
  }
  .hero-sub {
    font-size: 17px; color: var(--muted); max-width: 540px; line-height: 1.75;
  }
  .hero-actions {
    display: flex; flex-wrap: wrap; gap: 10px; margin-top: 4px;
  }

  /* Hash chain visualization */
  .chain-viz {
    margin-top: 32px;
    display: flex; align-items: stretch; gap: 0;
    border: 1px solid var(--border-hi); border-radius: var(--radius);
    overflow-x: auto; background: var(--surface);
  }
  .chain-block {
    display: flex; flex-direction: column; gap: 4px;
    padding: 14px 16px; border-right: 1px solid var(--border);
    min-width: 148px; flex-shrink: 0;
  }
  .chain-block:last-child { border-right: none; }
  .chain-block-lbl {
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .1em; color: var(--muted-dim);
  }
  .chain-block-type { font-size: 12px; font-weight: 600; color: var(--text); }
  .chain-block-hash {
    font-family: var(--font-mono); font-size: 9px;
    color: var(--blue); margin-top: 5px;
  }
  .chain-block.genesis .chain-block-hash { color: var(--green); }
  .chain-block.anchored .chain-block-hash { color: var(--amber); }
  .chain-tsa {
    display: flex; align-items: center; gap: 6px; padding: 14px 16px;
    font-size: 10px; font-weight: 600; color: var(--amber); white-space: nowrap;
    border-left: 1px solid rgba(245,158,11,.2);
    background: rgba(245,158,11,.04); flex-shrink: 0;
  }
  .chain-tsa svg { width: 12px; height: 12px; }

  /* ── Problem ────────────────────────────────────────────────── */
  .problem-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;
  }
  .problem-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 22px;
    transition: border-color .15s;
  }
  .problem-card:hover { border-color: var(--border-hi); }
  .problem-card-ico svg { width: 18px; height: 18px; color: var(--muted); margin-bottom: 12px; }
  .problem-card h3 { font-size: 14px; margin-bottom: 6px; }
  .problem-card p  { font-size: 13px; color: var(--muted); line-height: 1.65; }

  /* ── Pillars ────────────────────────────────────────────────── */
  .pillars-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
  }
  @media (max-width: 760px) { .pillars-grid { grid-template-columns: 1fr; } }

  .pillar-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 28px 24px;
    position: relative; overflow: hidden;
    transition: border-color .15s, transform .2s;
  }
  .pillar-card:hover { border-color: var(--border-hi); transform: translateY(-2px); }
  .pillar-accent {
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
  }
  .pillar-accent-blue  { background: linear-gradient(90deg, var(--green), var(--blue)); }
  .pillar-accent-indigo { background: linear-gradient(90deg, var(--blue), #818cf8); }
  .pillar-accent-amber { background: linear-gradient(90deg, #818cf8, var(--amber)); }
  .pillar-num {
    font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted-dim); margin-bottom: 16px; font-family: var(--font-mono);
  }
  .pillar-ico { width: 22px; height: 22px; color: var(--blue); margin-bottom: 14px; }
  .pillar-card h3 { margin-bottom: 10px; }
  .pillar-card p  { font-size: 13px; color: var(--muted); line-height: 1.7; }
  .pillar-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 18px; }

  /* ── How it works ───────────────────────────────────────────── */
  .steps-row {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px;
    background: var(--border);
    border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden;
  }
  @media (max-width: 860px) { .steps-row { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 480px) { .steps-row { grid-template-columns: 1fr; } }
  .step-cell {
    padding: 28px 22px; background: var(--surface);
  }
  .step-num {
    font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    color: var(--blue); font-family: var(--font-mono); margin-bottom: 16px;
  }
  .step-ico { width: 20px; height: 20px; color: var(--muted); margin-bottom: 12px; }
  .step-cell h3 { font-size: 14px; margin-bottom: 6px; }
  .step-cell p  { font-size: 13px; color: var(--muted); line-height: 1.65; }

  /* ── Tech row ───────────────────────────────────────────────── */
  .tech-row {
    display: flex; align-items: center; flex-wrap: wrap; gap: 10px;
    border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
    padding: 24px 0;
  }
  .tech-row-label {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .1em; color: var(--muted-dim);
  }
  .tech-badge {
    font-size: 11px; font-family: var(--font-mono); color: var(--muted);
    background: var(--surface); border: 1px solid var(--border);
    padding: 4px 9px; border-radius: var(--radius-sm);
  }

  /* ── Industries ─────────────────────────────────────────────── */
  .industries-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;
  }
  @media (max-width: 760px) { .industries-grid { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 480px) { .industries-grid { grid-template-columns: 1fr; } }

  .industry-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px;
    transition: border-color .15s;
  }
  .industry-card:hover { border-color: var(--border-hi); }
  .ind-ico { width: 18px; height: 18px; color: var(--muted); margin-bottom: 10px; }
  .industry-card h3 { font-size: 14px; margin-bottom: 4px; }
  .industry-subjects {
    font-size: 10px; font-family: var(--font-mono); color: var(--muted-dim); margin-bottom: 10px;
  }
  .industry-events { display: flex; flex-direction: column; gap: 4px; }
  .event-chip {
    font-size: 10px; font-family: var(--font-mono); color: var(--muted);
    background: var(--surface-2); border: 1px solid var(--border);
    padding: 2px 7px; border-radius: var(--radius-sm); width: fit-content;
  }

  /* ── Delivery models ─────────────────────────────────────────── */
  .delivery-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
  }
  @media (max-width: 760px) { .delivery-grid { grid-template-columns: 1fr; } }

  .delivery-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 28px 24px;
    display: flex; flex-direction: column;
    transition: border-color .15s, transform .2s;
  }
  .delivery-card:hover { transform: translateY(-2px); }
  .delivery-featured { border-color: rgba(59,130,246,.35); }
  .delivery-price {
    font-size: 28px; font-weight: 800; letter-spacing: -.03em; color: #f9fafb;
    margin: 16px 0 3px;
  }
  .delivery-price-note { font-size: 11px; color: var(--muted-dim); margin-bottom: 22px; }
  .delivery-features {
    list-style: none; display: flex; flex-direction: column; gap: 9px;
    margin-bottom: 24px; flex: 1;
  }
  .delivery-features li { font-size: 13px; color: var(--muted); display: flex; align-items: flex-start; gap: 7px; }
  .feat-check { width: 13px; height: 13px; color: var(--green); flex-shrink: 0; margin-top: 2px; }

  /* ── Roadmap ─────────────────────────────────────────────────── */
  .phases { display: flex; flex-direction: column; position: relative; }
  .phases::before {
    content: ""; position: absolute; left: 19px; top: 10px; bottom: 10px; width: 1px;
    background: linear-gradient(to bottom, var(--blue), #6366f1, var(--border));
  }
  .phase-row {
    display: flex; gap: 28px; padding: 24px 0;
    border-bottom: 1px solid var(--border);
  }
  .phase-row:last-child { border-bottom: none; }
  .phase-dot {
    width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    background: var(--surface); border: 1px solid var(--border); position: relative; z-index: 1;
  }
  .phase-ico { width: 18px; height: 18px; }
  .chip-green + .phase-ico, .phase-row .chip-green ~ * .phase-ico { color: var(--green); }
  .phase-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; flex-wrap: wrap; }
  .phase-num  { font-size: 11px; font-weight: 600; color: var(--muted-dim); font-family: var(--font-mono); }
  .phase-content h3 { margin-bottom: 6px; }
  .phase-content p  { font-size: 13px; color: var(--muted); line-height: 1.7; max-width: 600px; }
  .phase-items { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
  .phase-item {
    font-size: 10px; font-family: var(--font-mono); color: var(--muted);
    background: var(--surface-2); border: 1px solid var(--border);
    padding: 2px 7px; border-radius: var(--radius-sm);
  }
  .phase-item-done   { color: var(--green); border-color: rgba(34,197,94,.2); background: rgba(34,197,94,.05); }
  .phase-item-active { color: var(--blue);  border-color: rgba(59,130,246,.25); background: rgba(59,130,246,.06); }

  /* ── Developer panel ─────────────────────────────────────────── */
  .dev-shell {
    display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2.2fr); gap: 24px;
  }
  @media (max-width: 780px) { .dev-shell { grid-template-columns: 1fr; } }

  .dev-right { display: flex; flex-direction: column; gap: 14px; }

  .foot-note { margin-top: 16px; font-size: 12px; color: var(--muted-dim); }
  .foot-note a { color: var(--muted); text-decoration: none; }
  .foot-note a:hover { text-decoration: underline; }

  /* ── CTA ──────────────────────────────────────────────────────── */
  .cta-section {
    text-align: center;
    background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(59,130,246,.07) 0%, transparent 70%);
  }
  .cta-section h2 { margin-bottom: 12px; }
  .cta-section p  { font-size: 16px; color: var(--muted); max-width: 480px; margin: 0 auto 28px; }
  .cta-actions { display: flex; justify-content: center; flex-wrap: wrap; gap: 10px; }
  .cta-note { font-size: 12px; color: var(--muted-dim); margin-top: 14px; }
</style>
"""


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

def hero(app_name: str) -> str:
    """Full-width hero with tagline and hash chain visualization."""
    return f"""
<section class="hero" id="hero" aria-labelledby="hero-heading">
  <div class="hero-grid" aria-hidden="true"></div>
  <div class="container">
    <div class="hero-inner">

      <div class="eyebrow">
        <span class="live-dot" aria-hidden="true"></span>
        {app_name} · Private beta
      </div>

      <h1 id="hero-heading">
        The infrastructure layer<br>that makes history <em>provable</em>
      </h1>

      <p class="hero-sub">
        Compliance-grade event sourcing for regulated industries.
        Immutable, cryptographically chained, and externally timestamped —
        so the past stays exactly as it happened.
      </p>

      <div class="hero-actions">
        {btn("Request early access", "#cta", icon_name="arrow-right", variant="blue")}
        {btn("Open API docs", "/docs", icon_name="book-open-text", variant="ghost")}
        {btn("Health check", "/api/v1/health", icon_name="activity", variant="ghost")}
      </div>

      <!-- Hash chain visualization -->
      <div class="chain-viz fade-up" role="img" aria-label="Example hash chain showing four linked events">
        <div class="chain-block genesis">
          <span class="chain-block-lbl">Event #1 — genesis</span>
          <span class="chain-block-type">LoanApplicationCreated</span>
          <span class="chain-block-hash">prev: null</span>
          <span class="chain-block-hash">hash: 3a7f…b21c</span>
        </div>
        <div class="chain-block">
          <span class="chain-block-lbl">Event #2</span>
          <span class="chain-block-type">DocumentsSubmitted</span>
          <span class="chain-block-hash">prev: 3a7f…b21c</span>
          <span class="chain-block-hash">hash: e91d…04af</span>
        </div>
        <div class="chain-block">
          <span class="chain-block-lbl">Event #3</span>
          <span class="chain-block-type">UnderwritingApproved</span>
          <span class="chain-block-hash">prev: e91d…04af</span>
          <span class="chain-block-hash">hash: 77c2…f938</span>
        </div>
        <div class="chain-block anchored">
          <span class="chain-block-lbl">Event #4</span>
          <span class="chain-block-type">LoanDisbursed</span>
          <span class="chain-block-hash">prev: 77c2…f938</span>
          <span class="chain-block-hash">hash: b84a…19d7</span>
        </div>
        <div class="chain-tsa">
          {icon("lock", "")}
          RFC 3161 · 2025-03-12T14:22:08Z
        </div>
      </div>

    </div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Problem
# ---------------------------------------------------------------------------

def problem() -> str:
    """The problem section — four pain point cards."""
    cards = [
        ("archive",    "Regulators ask for history you cannot reconstruct",
         "A regulator asks for the exact state of an account on March 14th, two years ago, "
         "with proof it was not altered. Your database stores today's state. Game over."),
        ("code-2",     "Engineering builds it. Then rebuilds it. Then again.",
         "15–20% of engineering capacity in compliance-heavy companies goes to audit infrastructure — "
         "work that never ships a feature, never differentiates the product, and never quite does the job."),
        ("eye-off",    "The audit log is the first thing that gets silently fixed",
         "Support edits a record. A migration runs. A developer corrects a data entry. "
         "Conventional audit tables have no cryptographic mechanism to detect this."),
        ("network",    "Events live in five different systems and belong to none",
         "The loan event is in Salesforce, the KYC check is in a third-party API, "
         "the payment is in core banking, and the policy change is in a spreadsheet. "
         "Nobody has the full picture."),
    ]
    cards_html = "".join(
        f"""<div class="problem-card fade-up">
              <div class="problem-card-ico">{icon(ico)}</div>
              <h3>{title}</h3>
              <p>{body}</p>
            </div>"""
        for ico, title, body in cards
    )
    return f"""
<section class="section-alt" id="problem" aria-labelledby="problem-heading">
  <div class="container">
    <div class="section-header fade-up">
      <p style="font-size:clamp(20px,3vw,32px);font-weight:700;letter-spacing:-.02em;
                color:#f9fafb;max-width:680px;line-height:1.3;" id="problem-heading">
        Every audit log tells you what exists now. None of them prove what happened then
        — or that nobody changed it in between.
      </p>
    </div>
    <div class="problem-grid" role="list">{cards_html}</div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Solution pillars
# ---------------------------------------------------------------------------

def pillars() -> str:
    """Three solution pillar cards."""
    p1 = pillar_card(
        "01", "shield-check",
        "Cryptographic proof that history did not change",
        "Every event is SHA-256 chained to the previous. One altered record breaks every hash that "
        "follows. The chain tip is anchored via RFC 3161 — the same timestamping standard used in "
        "financial markets and legal proceedings — so proof exists entirely outside your database.",
        ["SHA-256 chain", "RFC 3161 TSA", "VerificationService"],
        accent="blue",
    )
    p2 = pillar_card(
        "02", "plug-zap",
        "Ingest events from any source without changing anything",
        "The Connector framework maps any source — Kafka, PostgreSQL CDC, REST, inbound email, "
        "file watchers — to the same immutable ledger. Your existing systems stay untouched. "
        "Timeline watches what already happens and records it with idempotency guarantees.",
        ["Kafka", "CDC / Debezium", "REST", "Email", "external_id"],
        accent="indigo",
    )
    p3 = pillar_card(
        "03", "layers",
        "Query state at any point in time, live or historical",
        "Projections replay the event stream through reducer functions to answer 'what is current "
        "state?' and 'what was state on date X?' — without storing historical snapshots. "
        "Webhooks push on every write. SSE streams live to any UI. Redis pub/sub scales across workers.",
        ["Projections", "Webhooks", "SSE", "Redis pub/sub", "time-travel"],
        accent="amber",
    )
    return f"""
<section id="solution" aria-labelledby="solution-heading">
  <div class="container">
    {section_header("The solution", "One platform. Three properties nothing else has together.",
                    "Each layer builds on the previous. Together they create a system categorically "
                    "different from an audit log.", centered=True)}
    <div class="pillars-grid">{p1}{p2}{p3}</div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# How it works
# ---------------------------------------------------------------------------

def how_it_works() -> str:
    """Four-step how-it-works strip."""
    steps = [
        ("01", "clipboard-list",  "Define your schema",
         "Register subject types (loan, policy, patient) and event types with optional JSON Schema "
         "payload validation. Your industry semantics; Timeline's engine."),
        ("02", "plug-zap",        "Connect your sources",
         "Write events via REST, or attach a connector to your Kafka topic or PostgreSQL database. "
         "Every source produces the same hash-chained ledger entry with idempotency and provenance."),
        ("03", "lock",            "Verify and timestamp",
         "The chain is anchored automatically via RFC 3161 TSA on a configurable schedule. "
         "Run chain verification at any time. The proof lives outside Timeline's own infrastructure."),
        ("04", "bar-chart-2",     "Query, project, stream",
         "Define projections as pure reducer functions. Query current or as-of state. "
         "Subscribe via SSE for live updates. Receive webhooks when specific events occur."),
    ]
    cells = "".join(
        f"""<div class="step-cell fade-up">
              <div class="step-num">Step {num}</div>
              <div>{icon(ico, "step-ico")}</div>
              <h3>{title}</h3>
              <p>{body}</p>
            </div>"""
        for num, ico, title, body in steps
    )
    return f"""
<section class="section-alt" id="how" aria-labelledby="how-heading">
  <div class="container">
    {section_header("How it works", "From zero to provable history in four steps",
                    centered=True)}
    <div class="steps-row" role="list">{cells}</div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Tech row
# ---------------------------------------------------------------------------

def tech_row() -> str:
    """Horizontal strip of technology badges."""
    techs = [
        "Python 3.12", "FastAPI", "PostgreSQL (RLS)", "SQLAlchemy async",
        "Redis", "RFC 3161 TSA", "SHA-256", "HMAC-SHA256",
    ]
    badges = "".join(f'<span class="tech-badge">{t}</span>' for t in techs)
    return f"""
<div class="container">
  <div class="tech-row fade-up" aria-label="Technology stack">
    <span class="tech-row-label">Built on</span>
    {badges}
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# Industries
# ---------------------------------------------------------------------------

def industries() -> str:
    """Six industry cards."""
    cards = [
        industry_card("landmark",     "Lending & Fintech",
                      "loan · account · borrower",
                      ["LoanApplicationCreated", "UnderwritingApproved", "LoanDisbursed",
                       "PaymentReceived", "DefaultDeclared"]),
        industry_card("shield",       "Insurance",
                      "policy · claim · client",
                      ["PolicyIssued", "ClaimFiled", "ClaimAssessed",
                       "SettlementPaid", "PolicyRenewed"]),
        industry_card("heart-pulse",  "Healthcare",
                      "patient · episode · consent",
                      ["PatientAdmitted", "ProcedurePerformed",
                       "MedicationAdministered", "DischargeCompleted"]),
        industry_card("scale",        "Legal & Professional",
                      "matter · filing · client",
                      ["MatterOpened", "FilingSubmitted",
                       "HearingScheduled", "JudgmentDelivered"]),
        industry_card("package",      "Procurement & Supply Chain",
                      "supplier · contract · PO",
                      ["SupplierApproved", "ContractSigned",
                       "OrderPlaced", "DeliveryReceived"]),
        industry_card("users-round",  "HR & Payroll",
                      "employee · role · review",
                      ["EmployeeOnboarded", "RoleChanged",
                       "SalaryAdjusted", "TerminationInitiated"]),
    ]
    return f"""
<section id="industries" aria-labelledby="industries-heading">
  <div class="container">
    {section_header("Industries", "Same engine. Every regulated vertical.",
                    "The subject model is universal. Event type semantics are yours to define.",
                    centered=True)}
    <div class="industries-grid">{" ".join(cards)}</div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Delivery models
# ---------------------------------------------------------------------------

def delivery() -> str:
    """Three delivery model / pricing cards."""
    cloud = delivery_card(
        "Timeline Cloud",
        "Managed SaaS",
        "Fully managed. No infrastructure to operate. Timeline handles uptime, "
        "TSA anchoring, backups, and scaling. Start writing events in under an hour.",
        "From $299<span style='font-size:16px;font-weight:500;color:var(--muted-dim)'>/mo</span>",
        "Up to 500 K events/mo · 10 K subjects · 1 connector",
        [
            "Multi-tenant, fully isolated",
            "Automatic TSA anchoring",
            "Webhook delivery + retry",
            "SSE real-time streaming",
            "99.9% uptime SLA (Growth+)",
            "Growth: up to 10 M events/mo",
            "Scale: up to 100 M events/mo",
        ],
        "Start free trial",
        "#cta",
        featured=False,
    )
    hosted = delivery_card(
        "Timeline Self-Hosted",
        "Your Infrastructure",
        "Deploy on your own Kubernetes or Docker environment. Complete data sovereignty. "
        "Ideal for regulated institutions and data residency requirements.",
        "From $18K<span style='font-size:16px;font-weight:500;color:var(--muted-dim)'>/yr</span>",
        "License by tenant count and event volume",
        [
            "Helm chart + Docker Compose",
            "Offline license key — air-gap ready",
            "All Cloud features included",
            "PostgreSQL + Redis on your servers",
            "Your own TSA endpoint or ours",
            "Email support; dedicated add-on",
        ],
        "Contact sales",
        "#cta",
        featured=True,
    )
    oem = delivery_card(
        "Timeline Embedded",
        "OEM / White-Label",
        "Embed the Timeline engine inside your own product. White-labeled under "
        "your brand. For software vendors who want to offer compliance audit as a "
        "native feature.",
        "Custom",
        "Annual OEM license · volume-based",
        [
            "Full source license",
            "White-label theming",
            "Multi-brand tenant isolation",
            "Vendor SDK — Python + TypeScript",
            "Dedicated integration support",
            "SLA and support contract included",
        ],
        "Talk to us",
        "#cta",
        featured=False,
    )
    return f"""
<section class="section-alt" id="delivery" aria-labelledby="delivery-heading">
  <div class="container">
    {section_header("How to access Timeline",
                    "Three ways to deploy. One engine.",
                    "From self-serve cloud to air-gapped enterprise — "
                    "Timeline meets you where your compliance requirements actually are.",
                    centered=True)}
    <div class="delivery-grid">{cloud}{hosted}{oem}</div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------

def roadmap() -> str:
    """Phase-by-phase roadmap timeline."""
    phases_html = "".join([
        phase_row(
            "1", "Phases 1–4", "done",
            "Core ledger + gateway hardening",
            "SHA-256 hash chain, RFC 3161 TSA anchoring, multi-tenant RLS, event schema registry, "
            "transition validation, idempotency keys, multi-source connector framework, enrichment "
            "pipeline, per-tenant rate limiting, HMAC-SHA256 webhooks, SSE streaming.",
            ["Hash chain", "TSA anchoring", "Connectors", "Webhooks",
             "SSE streaming", "Rate limiting", "RBAC + auth", "Workflow engine"],
            [], [],
        ),
        phase_row(
            "5", "Phase 5 · Current", "active",
            "Projection engine + Redis pub/sub",
            "Named projections as pure reducer functions, watermark-based multi-worker "
            "advancement with SKIP LOCKED, point-in-time state replay, Redis pub/sub for "
            "multi-worker SSE, and analytics query endpoints.",
            ["event_seq ordering", "get_events_since_seq"],
            ["Projection tables + engine", "ProjectionRegistry", "Redis publisher", "Analytics API"],
            [],
        ),
        phase_row(
            "6", "Phase 6 · Year 1", "planned",
            "Cloud launch + developer experience",
            "Stripe billing, event metering, quota enforcement, tenant onboarding wizard, "
            "API key management, TypeScript SDK, public API documentation, Docker Compose dev "
            "stack, customer admin dashboard, SAML SSO, and status page.",
            [],
            [],
            ["Stripe billing", "TypeScript SDK", "Onboarding wizard",
             "Admin dashboard", "SAML SSO", "API docs"],
        ),
        phase_row(
            "7", "Phase 7 · Year 2", "planned",
            "Self-hosted + compliance certification",
            "Helm chart for Kubernetes, offline license key validation, SOC 2 Type I, "
            "GDPR Data Processing Agreement, Python SDK, Redis projection cache, and "
            "read replica support.",
            [],
            [],
            ["Helm chart", "Offline license", "SOC 2 Type I", "DPA template", "Python SDK"],
        ),
        phase_row(
            "8", "Phase 8 · Year 2–3", "planned",
            "Connector marketplace + industry packs",
            "Concrete PostgreSQL CDC and Kafka connector implementations, managed connector "
            "configuration UI, AWS SQS and HTTP webhook receiver connectors, industry starter "
            "packs, and multi-region deployment.",
            [],
            [],
            ["PostgreSQL CDC", "Kafka connector", "Connector UI", "Industry packs", "Multi-region"],
        ),
        phase_row(
            "9", "Phase 9 · Year 4–5", "planned",
            "OEM + partner ecosystem",
            "White-label OEM license, vendor SDK, public partner API, projection marketplace "
            "for partner-published reducer libraries, optional GraphQL query layer, and "
            "governance features for regulated tenants.",
            [],
            [],
            ["OEM license", "Partner API", "Projection marketplace", "GraphQL (opt.)", "Governance"],
        ),
    ])
    return f"""
<section id="roadmap" aria-labelledby="roadmap-heading">
  <div class="container">
    {section_header("Roadmap", "From engine to platform to ecosystem.",
                    "Each phase is a commercial milestone, not just a technical one.")}
    <div class="phases">{phases_html}</div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Developer panel  (the original root.py content, preserved as a section)
# ---------------------------------------------------------------------------

def developer_panel(app_name: str) -> str:
    """Quickstart, health, and route reference for API consumers."""
    quickstart_body = f"""
<p>Run the API locally with Uvicorn once Postgres and Redis are available.</p>
<div class="code-box">
  <span>uv run uvicorn app.main:app <span class="code-muted">--reload</span></span>
</div>
<p style="margin-top:8px;">
  Copy <code>.env.example</code> to <code>.env</code> and configure
  <code>DATABASE_URL</code>, <code>REDIS_URL</code>, and secrets.
</p>
"""
    health_body = f"""
{kpi_row(("Liveness", '<span id="health-liveness">—</span>'),
         ("Readiness", '<span id="health-readiness">—</span>'))}
<p style="margin-top:10px;">
  Backed by <code>/api/v1/health</code> and <code>/api/v1/health/ready</code>.
</p>
"""
    routes_body = f"""
{kpi_row(("Scalar docs", "<code>/docs</code>"),
         ("Health", "<code>/api/v1/health</code>"))}
<div style="margin-top:10px;">
  {kpi_row(("Events", "<code>/api/v1/events</code>"),
           ("Subjects", "<code>/api/v1/subjects</code>"))}
</div>
<div style="margin-top:10px;">
  {kpi_row(("Webhooks", "<code>/api/v1/webhooks</code>"),
           ("SSE stream", "<code>/api/v1/events/stream</code>"))}
</div>
"""
    api_base_body = """
<p>Use the origin below as the base for all requests.</p>
<div class="code-label">Origin</div>
<div class="code-box"><span id="api-origin">—</span></div>
<div class="code-label">Example</div>
<div class="code-box">
  <span class="code-muted">GET</span>
  <span>/api/v1/events?subject_id=&lt;uuid&gt;</span>
</div>
"""
    return f"""
<section class="section-alt" id="developer" aria-labelledby="dev-heading">
  <div class="container">
    {section_header("Developer", f"Get started with the {app_name} API",
                    "Everything you need to write your first event.")}
    <div class="dev-shell">
      <div class="dev-left">
        {card_with_header("API base URL", "server", api_base_body, "Local &amp; deployed")}
        <div class="foot-note">
          {app_name} · Event API ·
          <a href="/docs">API reference</a> ·
          <a href="/api/v1/health">Health</a>
        </div>
      </div>
      <div class="dev-right">
        {card_with_header("Local quickstart", "terminal-square", quickstart_body)}
        {card_with_header("Platform health", "heart-pulse", health_body, "Live")}
        {card_with_header("Useful routes", "route", routes_body)}
      </div>
    </div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# CTA
# ---------------------------------------------------------------------------

def cta(app_name: str) -> str:
    """Final call-to-action section."""
    return f"""
<section class="cta-section" id="cta" aria-labelledby="cta-heading">
  <div class="container">
    <div class="fade-up">
      <h2 id="cta-heading">Ready to make your history provable?</h2>
      <p>
        {app_name} is in private beta. Request early access and we will
        reach out within 48 hours.
      </p>
      <div class="cta-actions">
        {btn("Request early access", "mailto:hello@timeline.dev",
             icon_name="arrow-right", variant="blue")}
        {btn("Read the vision doc", "docs/PRODUCT_VISION.md",
             icon_name="file-text", variant="ghost")}
      </div>
      <p class="cta-note">
        No credit card required during beta. Available on Cloud and Self-Hosted.
      </p>
    </div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Health-fetch script (injected per page that needs it)
# ---------------------------------------------------------------------------

HEALTH_FETCH_SCRIPT = """
<script>
(function () {
  var originEl = document.getElementById("api-origin");
  if (originEl) originEl.textContent = window.location.origin;

  function probe(url, elId, okText, failText) {
    var el = document.getElementById(elId);
    if (!el) return;
    fetch(url)
      .then(function (res) {
        return res.json().then(function (b) { return { ok: res.ok, body: b }; });
      })
      .then(function (r) {
        el.textContent = (r.body && r.body.status) ? r.body.status : (r.ok ? okText : failText);
      })
      .catch(function () { el.textContent = "error"; });
  }

  probe("/api/v1/health",       "health-liveness",  "ok",    "error");
  probe("/api/v1/health/ready", "health-readiness", "ready", "not_ready");
})();
</script>
"""
