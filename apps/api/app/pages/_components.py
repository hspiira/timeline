"""Reusable HTML component functions.

Every function returns a plain HTML string fragment.  No state, no side
effects — pure functions so callers can compose freely.

Lucide icons are rendered as ``<i data-lucide="...">`` tags; the Lucide JS
CDN (loaded in ``_base.py``) replaces them with SVGs at runtime.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def icon(name: str, cls: str = "") -> str:
    """Render a Lucide icon placeholder.

    Args:
        name: Lucide icon name, e.g. ``"shield-check"``.
        cls:  Extra CSS classes applied to the ``<i>`` element.
    """
    klass = f'data-lucide="{name}" aria-hidden="true"'
    if cls:
        klass += f' class="{cls}"'
    return f"<i {klass}></i>"


def chip(text: str, variant: str = "") -> str:
    """Small uppercase label chip.

    variant: ``""`` (neutral) | ``"blue"`` | ``"amber"`` | ``"green"``
    """
    cls = "chip"
    if variant:
        cls += f" chip-{variant}"
    return f'<span class="{cls}">{text}</span>'


def btn(
    label: str,
    href: str,
    *,
    icon_name: str | None = None,
    variant: str = "ghost",
) -> str:
    """Anchor styled as a button.

    variant: ``"primary"`` | ``"blue"`` | ``"ghost"``
    """
    ico = f"{icon(icon_name)} " if icon_name else ""
    return (
        f'<a href="{href}" class="btn btn-{variant}">'
        f"{ico}{label}"
        "</a>"
    )


def section_header(
    eyebrow: str,
    title: str,
    subtitle: str = "",
    *,
    centered: bool = False,
) -> str:
    """Eyebrow chip + h2 + optional paragraph."""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    cls = "section-header centered" if centered else "section-header"
    return (
        f'<div class="{cls}">'
        f"{chip(eyebrow, 'blue')}"
        f"<h2>{title}</h2>"
        f"{sub}"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Nav + Footer
# ---------------------------------------------------------------------------

def nav(app_name: str) -> str:
    """Fixed top navigation bar."""
    return f"""
<nav aria-label="Main navigation">
  <div class="container nav-inner">
    <a href="#" class="nav-logo" aria-label="{app_name} home">
      <div class="nav-logo-mark" aria-hidden="true">T</div>
      {app_name}
    </a>
    <ul class="nav-links">
      <li><a href="#solution">How it works</a></li>
      <li><a href="#industries">Industries</a></li>
      <li><a href="#delivery">Pricing</a></li>
      <li><a href="#roadmap">Roadmap</a></li>
      <li><a href="#developer">Developer</a></li>
    </ul>
    {btn("Request Access", "#cta", icon_name="arrow-right", variant="primary")}
  </div>
</nav>
"""


def footer_bar(app_name: str) -> str:
    """Site footer."""
    return f"""
<footer>
  <div class="container">
    <div class="f-logo">{app_name}</div>
    <p>The infrastructure layer that makes history provable.</p>
    <p style="margin-top:12px;">
      <a href="/docs">API reference</a> &nbsp;·&nbsp;
      <a href="docs/PLATFORM_VISION_AND_ROADMAP.md">Roadmap</a> &nbsp;·&nbsp;
      <a href="docs/PRODUCT_VISION.md">Product vision</a> &nbsp;·&nbsp;
      <a href="docs/ARCHITECTURE.md">Architecture</a>
    </p>
  </div>
</footer>
"""


# ---------------------------------------------------------------------------
# Shared card wrappers
# ---------------------------------------------------------------------------

def card_with_header(
    label: str,
    icon_name: str,
    body: str,
    tag_text: str = "",
) -> str:
    """Standard labelled card used in the dev panel."""
    tag_html = f'<span class="chip">{tag_text}</span>' if tag_text else ""
    return f"""
<div class="card">
  <div class="card-header">
    <div class="card-label">
      {icon(icon_name)}
      {label}
    </div>
    {tag_html}
  </div>
  <div class="card-body">
    {body}
  </div>
</div>
"""


def kpi_row(*pairs: tuple[str, str]) -> str:
    """Row of label/value KPI cells.  Each pair is (label, value_html)."""
    cells = "".join(
        f'<div class="kpi"><div class="kpi-label">{lbl}</div>'
        f'<div class="kpi-value">{val}</div></div>'
        for lbl, val in pairs
    )
    return f'<div class="kpi-row">{cells}</div>'


# ---------------------------------------------------------------------------
# Feature / pillar card
# ---------------------------------------------------------------------------

def pillar_card(
    number: str,
    icon_name: str,
    title: str,
    body: str,
    tags: list[str],
    accent: str = "blue",
) -> str:
    """Feature pillar card used in the solution section."""
    tags_html = "".join(
        f'<span class="chip" style="font-family:var(--font-mono)">{t}</span>'
        for t in tags
    )
    return f"""
<div class="pillar-card fade-up">
  <div class="pillar-accent pillar-accent-{accent}"></div>
  <div class="pillar-num">{number}</div>
  <div class="pillar-icon">{icon(icon_name, "pillar-ico")}</div>
  <h3>{title}</h3>
  <p>{body}</p>
  <div class="pillar-tags">{tags_html}</div>
</div>
"""


# ---------------------------------------------------------------------------
# Industry card
# ---------------------------------------------------------------------------

def industry_card(
    icon_name: str,
    title: str,
    subjects: str,
    events: list[str],
) -> str:
    """Compact industry card with event type chips."""
    event_chips = "".join(
        f'<span class="event-chip">{e}</span>' for e in events
    )
    return f"""
<div class="industry-card fade-up">
  <div class="industry-icon">{icon(icon_name, "ind-ico")}</div>
  <h3>{title}</h3>
  <div class="industry-subjects">{subjects}</div>
  <div class="industry-events">{event_chips}</div>
</div>
"""


# ---------------------------------------------------------------------------
# Delivery / pricing card
# ---------------------------------------------------------------------------

def delivery_card(
    badge: str,
    title: str,
    description: str,
    price: str,
    price_note: str,
    features: list[str],
    cta_label: str,
    cta_href: str,
    featured: bool = False,
) -> str:
    """Pricing / delivery model card."""
    feat_items = "".join(
        f'<li>{icon("check", "feat-check")} {f}</li>'
        for f in features
    )
    featured_cls = " delivery-featured" if featured else ""
    featured_tag = (
        '<span class="chip chip-blue" style="position:absolute;top:16px;right:16px">'
        "Most popular</span>"
        if featured
        else ""
    )
    cta_var = "blue" if featured else "ghost"
    return f"""
<div class="delivery-card fade-up{featured_cls}" style="position:relative;">
  {featured_tag}
  <div class="chip chip-blue" style="margin-bottom:14px">{badge}</div>
  <h3 style="font-size:22px;font-weight:800;letter-spacing:-.03em">{title}</h3>
  <p style="margin-top:8px;font-size:14px;color:var(--muted);line-height:1.7">{description}</p>
  <div class="delivery-price">{price}</div>
  <div class="delivery-price-note">{price_note}</div>
  <ul class="delivery-features">{feat_items}</ul>
  {btn(cta_label, cta_href, variant=cta_var)}
</div>
"""


# ---------------------------------------------------------------------------
# Roadmap phase row
# ---------------------------------------------------------------------------

def phase_row(
    number: str,
    label: str,
    status: str,
    title: str,
    body: str,
    items_done: list[str],
    items_progress: list[str],
    items_planned: list[str],
) -> str:
    """One row in the roadmap timeline."""
    status_map = {
        "done":    ("chip chip-green", icon("check-circle-2", "phase-ico"), "Complete"),
        "active":  ("chip chip-blue",  icon("circle-dot",     "phase-ico"), "In progress"),
        "planned": ("chip",            icon("circle",         "phase-ico"), "Planned"),
    }
    chip_cls, dot_ico, status_label = status_map.get(status, status_map["planned"])

    def _items(lst: list[str], cls: str) -> str:
        return "".join(f'<span class="phase-item {cls}">{t}</span>' for t in lst)

    all_items = (
        _items(items_done,     "phase-item-done")
        + _items(items_progress, "phase-item-active")
        + _items(items_planned,  "")
    )

    return f"""
<div class="phase-row">
  <div class="phase-dot">{dot_ico}</div>
  <div class="phase-content">
    <div class="phase-meta">
      <span class="phase-num">{label}</span>
      <span class="{chip_cls}">{status_label}</span>
    </div>
    <h3>{title}</h3>
    <p>{body}</p>
    <div class="phase-items">{all_items}</div>
  </div>
</div>
"""
