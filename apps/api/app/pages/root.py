"""Root landing page — thin orchestrator.

Composes the full page from modular building blocks:

* ``_base``       — HTML shell, design tokens, CDN links
* ``_components`` — nav + footer atoms
* ``sections``    — one function per content section

Adding a new section is a two-step process:
  1. Write the section function in ``sections.py``.
  2. Add one call here between ``<main>`` and ``</main>``.

Nothing else belongs in this file.
"""

from __future__ import annotations

from ._base import page_shell
from ._components import footer_bar, nav
from .sections import (
    HEALTH_FETCH_SCRIPT,
    SECTIONS_CSS,
    cta,
    delivery,
    developer_panel,
    hero,
    how_it_works,
    industries,
    pillars,
    problem,
    roadmap,
    tech_row,
)

_DESCRIPTION = (
    "Compliance-grade event sourcing for regulated industries. "
    "Immutable, cryptographically chained, and externally timestamped — "
    "with a simple JSON API."
)


def render_root_page(app_name: str) -> str:
    """Return the full HTML document for the root landing page."""
    body = (
        nav(app_name)
        + '<main id="main">'
        + hero(app_name)
        + problem()
        + pillars()
        + how_it_works()
        + tech_row()
        + industries()
        + delivery()
        + roadmap()
        + developer_panel(app_name)
        + cta(app_name)
        + "</main>"
        + footer_bar(app_name)
    )
    return page_shell(
        title=f"{app_name} — The infrastructure layer that makes history provable",
        body=body,
        description=_DESCRIPTION,
        extra_head=SECTIONS_CSS,
        extra_scripts=HEALTH_FETCH_SCRIPT,
    )
