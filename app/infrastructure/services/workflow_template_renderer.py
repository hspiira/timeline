"""Workflow notification templates: template key → subject/body (Jinja)."""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, Template

# In-repo template definitions: key → (subject_template, body_template)
# Context: event (trigger event), payload (event.payload), data (action params.data)
_DEFAULT_TEMPLATES: dict[str, tuple[str, str]] = {
    "high_value_claim": (
        "High-value claim {{ payload.get('claim_ref', '') }} requires review",
        "A claim was submitted with amount {{ payload.get('amount', 'N/A') }}.\n"
        "Subject ID: {{ event.subject_id if event else 'N/A' }}\n"
        "{% if data %}\nThreshold: {{ data.get('threshold', 'N/A') }}\n{% endif %}",
    ),
    "workflow_notification": (
        "Workflow: {{ payload.get('title', 'Notification') }}",
        "Event type: {{ event.event_type if event else 'N/A' }}\nPayload: {{ payload }}",
    ),
}


class WorkflowTemplateRenderer:
    """Renders subject and body for workflow notify action from a template key."""

    def __init__(
        self,
        templates: dict[str, tuple[str, str]] | None = None,
    ) -> None:
        """Initialize with optional template dict; falls back to _DEFAULT_TEMPLATES."""
        self._templates = templates or _DEFAULT_TEMPLATES
        self._env = Environment(autoescape=False)
        self._compiled: dict[str, tuple[Template, Template]] = {}
        for key, (sub_str, body_str) in self._templates.items():
            self._compiled[key] = (
                self._env.from_string(sub_str),
                self._env.from_string(body_str),
            )

    def render(
        self,
        template_key: str,
        event: Any,
        payload: dict[str, Any],
        data: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Render subject and body for the template key. Raises KeyError if key unknown."""
        if template_key not in self._compiled:
            raise KeyError(f"Unknown workflow template: {template_key}")
        ctx = {
            "event": event,
            "payload": payload,
            "data": data or {},
        }
        subject_tpl, body_tpl = self._compiled[template_key]
        subject = subject_tpl.render(**ctx)
        body = body_tpl.render(**ctx)
        return subject, body
