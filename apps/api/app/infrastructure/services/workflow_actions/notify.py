"""notify workflow action handler."""

from __future__ import annotations

from typing import Any

from app.infrastructure.persistence.models.workflow import Workflow
from app.infrastructure.services.workflow_actions import ActionContext
from app.shared.telemetry.logging import get_logger

logger = get_logger(__name__)


class NotifyHandler:
    """Handler for action type notify."""

    async def execute(
        self,
        action: dict[str, Any],
        triggered_by: Any,
        workflow: Workflow,
        execution_log: list[dict[str, Any]],
        ctx: ActionContext,
    ) -> tuple[int, int]:
        action_type = action.get("type", "notify")
        params = action.get("params", {})
        role_code = params.get("role")
        template_key = params.get("template")
        data = params.get("data")
        if not role_code or not template_key:
            execution_log.append(
                {
                    "action": action_type,
                    "status": "failed",
                    "error": "notify requires params.role and params.template",
                }
            )
            return (0, 1)
        if not ctx.recipient_resolver or not ctx.template_renderer or not ctx.notification_service:
            execution_log.append(
                {
                    "action": action_type,
                    "status": "skipped",
                    "reason": "notify not configured (missing resolver/templates/notification)",
                }
            )
            return (0, 0)
        try:
            emails = await ctx.recipient_resolver.get_emails_for_role(
                ctx.tenant_id, role_code
            )
            if not emails:
                logger.warning(
                    "notify action skipped: no recipients for role %r (tenant_id=%s)",
                    role_code,
                    ctx.tenant_id,
                )
                execution_log.append(
                    {
                        "action": action_type,
                        "status": "skipped",
                        "reason": f"no recipients found for role '{role_code}'",
                    }
                )
                return (0, 0)
            payload = getattr(triggered_by, "payload", None) or {}
            subject, body = ctx.template_renderer.render(
                template_key, triggered_by, payload, data
            )
            await ctx.notification_service.send(emails, subject, body)
            execution_log.append(
                {
                    "action": action_type,
                    "status": "success",
                    "recipients_count": len(emails),
                }
            )
            return (1, 0)
        except KeyError as e:
            execution_log.append(
                {"action": action_type, "status": "failed", "error": str(e)}
            )
            return (0, 1)
        except Exception as e:
            execution_log.append(
                {"action": action_type, "status": "failed", "error": str(e)}
            )
            return (0, 1)
