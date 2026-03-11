"""Post-create hook implementations: workflow, webhook, SSE broadcast."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from app.application.interfaces.post_create_hooks import (
    IPostCreateHook,
    PostCreateContext,
)

if TYPE_CHECKING:
    from app.application.interfaces.event_stream import IEventStreamBroadcaster
    from app.application.interfaces.services import IWorkflowEngine
    from app.application.interfaces.webhook import IWebhookDispatcher

logger = logging.getLogger(__name__)


class WorkflowTriggerHook:
    """Runs workflow engine triggers after an event is created."""

    def __init__(
        self,
        get_workflow_engine: Callable[[], "IWorkflowEngine | None"],
    ) -> None:
        self._get_workflow_engine = get_workflow_engine

    async def after_event(self, context: PostCreateContext) -> None:
        """Run workflow triggers when trigger_workflows is True."""
        if not context.trigger_workflows:
            return
        engine = self._get_workflow_engine()
        if not engine:
            return
        try:
            await engine.process_event_triggers(context.entity, context.tenant_id)
        except (
            AssertionError,
            AttributeError,
            IndexError,
            KeyError,
            NameError,
            TypeError,
        ):
            raise
        except Exception:
            logger.exception(
                "Workflow trigger failed for event %s (type: %s)",
                context.entity.id,
                context.entity.event_type.value,
            )


class WebhookDispatchHook:
    """Spawns fire-and-forget webhook dispatch and tracks task in app-level set."""

    def __init__(
        self,
        dispatcher: "IWebhookDispatcher | None",
        pending_tasks: set[asyncio.Task[None]] | None,
    ) -> None:
        self._dispatcher = dispatcher
        self._pending_tasks = pending_tasks or set()

    async def after_event(self, context: PostCreateContext) -> None:
        """Schedule webhook dispatch; add task to pending set for lifecycle tracking."""
        if not self._dispatcher:
            return
        task = asyncio.create_task(
            self._dispatcher.dispatch(
                context.tenant_id,
                context.entity,
                context.subject_type,
            )
        )
        self._pending_tasks.add(task)

        def _on_done(t: asyncio.Task[None]) -> None:
            self._pending_tasks.discard(t)
            try:
                exc = t.exception()
            except Exception:
                logger.exception(
                    "Webhook dispatch task failed (error retrieving exception)",
                )
                return
            if exc is not None:
                logger.exception(
                    "Webhook dispatch task failed for event %s",
                    context.entity.id,
                    exc_info=exc,
                )

        task.add_done_callback(_on_done)


def _event_result_to_sse_payload(r: Any) -> dict:
    """Build JSON-serializable payload for SSE (event_time as ISO string)."""
    return {
        "id": r.id,
        "tenant_id": r.tenant_id,
        "subject_id": r.subject_id,
        "event_type": r.event_type,
        "schema_version": r.schema_version,
        "event_time": r.event_time.isoformat(),
        "payload": r.payload,
        "previous_hash": r.previous_hash,
        "hash": r.hash,
        "workflow_instance_id": r.workflow_instance_id,
        "correlation_id": r.correlation_id,
        "external_id": r.external_id,
        "source": r.source,
    }


class EventStreamBroadcastHook:
    """Publishes event payload to SSE (and other) subscribers."""

    def __init__(
        self,
        broadcaster: "IEventStreamBroadcaster | None",
    ) -> None:
        self._broadcaster = broadcaster

    async def after_event(self, context: PostCreateContext) -> None:
        """Publish event to stream broadcaster for SSE subscribers."""
        if not self._broadcaster:
            return
        payload = _event_result_to_sse_payload(context.event_result)
        await self._broadcaster.publish(
            context.tenant_id,
            payload,
            context.event_result.subject_id,
        )
