"""Shared HTML page shell, design tokens, and asset imports.

Single source of truth for colours, typography, spacing, and CDN links.
All pages import ``page_shell()``; none duplicate CSS variables or font tags.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# CDN assets — one place to bump versions
# ---------------------------------------------------------------------------

FONTS_TAG = (
    '<link rel="preconnect" href="https://fonts.googleapis.com" />'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800'
    "&family=JetBrains+Mono:wght@400;500&display=swap\" rel=\"stylesheet\" />"
)

LUCIDE_TAG = '<script src="https://unpkg.com/lucide@latest" defer></script>'

# ---------------------------------------------------------------------------
# Design tokens + base CSS
# Single string — no f-string, so CSS braces stay literal.
# ---------------------------------------------------------------------------

BASE_CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    /* Palette — dark neutral base, blue accent, amber highlight */
    --bg:         #050505;
    --bg-2:       #080808;
    --surface:    #0d0d0d;
    --surface-2:  #111111;
    --border:     #181818;
    --border-hi:  #262626;
    --blue:       #3b82f6;
    --blue-lo:    rgba(59,130,246,0.08);
    --blue-mid:   rgba(59,130,246,0.18);
    --amber:      #f59e0b;
    --amber-lo:   rgba(245,158,11,0.08);
    --green:      #22c55e;
    --green-lo:   rgba(34,197,94,0.08);
    --text:       #e5e7eb;
    --muted:      #9ca3af;
    --muted-dim:  #6b7280;

    /* Shape — very subtle rounding; keeps the geometric feel */
    --radius:     3px;
    --radius-sm:  2px;

    /* Typography */
    --font-sans:  "Inter", system-ui, -apple-system, sans-serif;
    --font-mono:  "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas,
                  "Liberation Mono", monospace;
  }

  html { scroll-behavior: smooth; }

  body {
    font-family: var(--font-sans);
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    overflow-x: hidden;
  }

  /* ── Accessibility ─────────────────────────────────────────────── */
  .skip-link {
    position: absolute; top: -100px; left: 16px; z-index: 200;
    padding: 10px 16px; background: var(--blue); color: #fff;
    font-size: 14px; font-weight: 600; text-decoration: none;
    border-radius: var(--radius); transition: top .2s ease;
  }
  .skip-link:focus { top: 16px; outline: 2px solid var(--blue); outline-offset: 2px; }

  a:focus-visible, button:focus-visible {
    outline: 2px solid var(--blue); outline-offset: 2px;
  }

  /* ── Layout helpers ────────────────────────────────────────────── */
  .container { max-width: 1100px; margin: 0 auto; padding: 0 24px; }

  section { padding: 88px 0; }

  .section-alt { background: var(--bg-2); }

  /* ── Typography scale ──────────────────────────────────────────── */
  h1 {
    font-size: clamp(36px, 6vw, 70px);
    font-weight: 800; letter-spacing: -.04em; line-height: 1.05; color: #f9fafb;
  }
  h2 {
    font-size: clamp(24px, 4vw, 40px);
    font-weight: 700; letter-spacing: -.03em; line-height: 1.1; color: #f9fafb;
  }
  h3 { font-size: 16px; font-weight: 600; color: #f9fafb; }

  code {
    font-family: var(--font-mono); font-size: .88em;
    background: var(--surface-2); border: 1px solid var(--border-hi);
    padding: 1px 5px; border-radius: var(--radius-sm); color: var(--muted);
  }

  /* ── Chip / tag ────────────────────────────────────────────────── */
  .chip {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted-dim); border: 1px solid var(--border-hi);
    padding: 3px 8px; border-radius: var(--radius-sm); background: var(--surface);
  }
  .chip-blue {
    color: var(--blue); border-color: rgba(59,130,246,.25);
    background: var(--blue-lo);
  }
  .chip-amber {
    color: var(--amber); border-color: rgba(245,158,11,.25);
    background: var(--amber-lo);
  }
  .chip-green {
    color: var(--green); border-color: rgba(34,197,94,.25);
    background: var(--green-lo);
  }

  /* ── Buttons ───────────────────────────────────────────────────── */
  .btn {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 9px 18px; border: 1px solid var(--border-hi);
    background: transparent; color: var(--text); font-family: var(--font-sans);
    font-size: 14px; font-weight: 500; text-decoration: none; cursor: pointer;
    border-radius: var(--radius); transition: background .12s, border-color .12s, color .12s;
    white-space: nowrap;
  }
  .btn svg { width: 15px; height: 15px; flex-shrink: 0; }

  .btn-primary {
    background: #f9fafb; color: #020617; border-color: #f9fafb;
  }
  .btn-primary:hover { background: #e5e7eb; border-color: #e5e7eb; }

  .btn-blue {
    background: var(--blue); color: #fff; border-color: var(--blue);
  }
  .btn-blue:hover { background: #60a5fa; border-color: #60a5fa; }

  .btn-ghost {
    background: transparent; color: var(--muted); border-color: var(--border-hi);
  }
  .btn-ghost:hover {
    background: rgba(148,163,184,.07); color: var(--text); border-color: var(--border-hi);
  }

  /* ── Cards ─────────────────────────────────────────────────────── */
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px 22px;
  }
  .card + .card { margin-top: 12px; }

  .card-header {
    display: flex; align-items: center; justify-content: space-between;
    gap: 10px; margin-bottom: 10px;
  }
  .card-label {
    display: flex; align-items: center; gap: 6px;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .1em; color: var(--muted-dim);
  }
  .card-label svg { width: 14px; height: 14px; color: var(--muted); }

  .card p { font-size: 13px; color: var(--muted); line-height: 1.65; margin-top: 4px; }

  /* ── Code box ──────────────────────────────────────────────────── */
  .code-box {
    font-family: var(--font-mono); font-size: 12px;
    background: #020617; border: 1px solid var(--border-hi);
    border-radius: var(--radius-sm); padding: 8px 12px;
    color: var(--text); display: flex; align-items: center;
    justify-content: space-between; gap: 8px; overflow-x: auto;
    margin-top: 8px; white-space: nowrap;
  }
  .code-muted { color: var(--muted-dim); }
  .code-label {
    font-size: 10px; text-transform: uppercase; letter-spacing: .1em;
    color: var(--muted-dim); margin: 10px 0 3px;
  }

  /* ── KPI row ───────────────────────────────────────────────────── */
  .kpi-row { display: flex; gap: 10px; }
  .kpi {
    flex: 1; border: 1px solid var(--border); border-radius: var(--radius);
    padding: 10px 12px;
  }
  .kpi-label { font-size: 10px; color: var(--muted-dim); margin-bottom: 3px; }
  .kpi-value { font-size: 13px; color: var(--text); }

  /* ── Section header ────────────────────────────────────────────── */
  .section-header { margin-bottom: 52px; }
  .section-header h2 { margin: 12px 0 10px; }
  .section-header p  { font-size: 15px; color: var(--muted); max-width: 500px; }
  .section-header.centered { text-align: center; }
  .section-header.centered p { margin: 0 auto; }

  /* ── Fade-up scroll animation ──────────────────────────────────── */
  .fade-up {
    opacity: 0; transform: translateY(24px);
    transition: opacity .55s ease, transform .55s ease;
  }
  .fade-up.visible { opacity: 1; transform: translateY(0); }

  /* ── Eyebrow / live dot ────────────────────────────────────────── */
  .eyebrow {
    display: inline-flex; align-items: center; gap: 7px;
    font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted-dim);
  }
  .live-dot {
    width: 7px; height: 7px; border-radius: 50%; background: var(--green);
    animation: blink 2.2s ease-in-out infinite;
  }
  @keyframes blink {
    0%,100% { opacity:1; } 50% { opacity:.3; }
  }

  /* ── Nav ───────────────────────────────────────────────────────── */
  nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(16px); background: rgba(5,5,5,.85);
  }
  .nav-inner {
    display: flex; align-items: center; justify-content: space-between;
    height: 56px;
  }
  .nav-logo {
    font-size: 16px; font-weight: 700; color: #f9fafb;
    text-decoration: none; display: flex; align-items: center; gap: 8px;
    letter-spacing: -.02em;
  }
  .nav-logo-mark {
    width: 26px; height: 26px; border-radius: var(--radius);
    background: var(--blue); display: flex; align-items: center;
    justify-content: center; font-size: 13px; font-weight: 800; color: #fff;
  }
  .nav-links { display: flex; align-items: center; gap: 24px; list-style: none; }
  .nav-links a {
    font-size: 13px; font-weight: 500; color: var(--muted);
    text-decoration: none; transition: color .15s;
  }
  .nav-links a:hover { color: var(--text); }

  /* ── Footer ────────────────────────────────────────────────────── */
  footer {
    border-top: 1px solid var(--border); padding: 32px 0;
    text-align: center;
  }
  footer .f-logo { font-size: 14px; font-weight: 700; color: #f9fafb; margin-bottom: 6px; }
  footer p  { font-size: 12px; color: var(--muted-dim); margin-top: 6px; }
  footer a  { color: var(--muted); text-decoration: none; }
  footer a:hover { color: var(--text); }

  @media (max-width: 640px) {
    .nav-links { display: none; }
    section { padding: 64px 0; }
  }
"""

# ---------------------------------------------------------------------------
# Lucide init — placed at the end of <body>, deferred is unreliable for
# dynamically inserted icons so we call createIcons() on DOMContentLoaded.
# ---------------------------------------------------------------------------

LUCIDE_INIT_SCRIPT = """
<script>
(function () {
  function init() {
    try {
      if (window.lucide && typeof window.lucide.createIcons === "function") {
        window.lucide.createIcons();
      }
    } catch (e) { /* non-critical */ }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
</script>
"""

SCROLL_ANIM_SCRIPT = """
<script>
(function () {
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var siblings = Array.from(entry.target.parentElement.querySelectorAll(".fade-up:not(.visible)"));
      var idx = siblings.indexOf(entry.target);
      setTimeout(function () { entry.target.classList.add("visible"); }, idx * 70);
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.1, rootMargin: "0px 0px -32px 0px" });
  document.querySelectorAll(".fade-up").forEach(function (el) { observer.observe(el); });
})();
</script>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def page_shell(
    title: str,
    body: str,
    *,
    description: str = "Compliance-grade event sourcing for regulated industries.",
    extra_head: str = "",
    extra_scripts: str = "",
) -> str:
    """Wrap *body* in the standard HTML document shell.

    Args:
        title:        Browser tab title.
        body:         HTML between ``<body>`` tags (nav + main + footer).
        description:  ``<meta name="description">`` content.
        extra_head:   Additional ``<head>`` content (page-specific styles, etc.).
        extra_scripts: Additional ``<script>`` tags inserted before ``</body>``.
    """
    return (
        "<!DOCTYPE html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="UTF-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0" />'
        f'<meta name="description" content="{description}" />'
        f"<title>{title}</title>"
        + FONTS_TAG
        + LUCIDE_TAG
        + f"<style>{BASE_CSS}</style>"
        + extra_head
        + "</head>"
        "<body>"
        '<a href="#main" class="skip-link">Skip to main content</a>'
        + body
        + LUCIDE_INIT_SCRIPT
        + SCROLL_ANIM_SCRIPT
        + extra_scripts
        + "</body></html>"
    )
