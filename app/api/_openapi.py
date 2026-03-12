"""Centralised OpenAPI documentation registry.

Every route's ``summary``, ``description``, ``responses``, ``tags``, and
``openapi_extra`` (request body examples, extensions) lives here.  Route
files stay thin — a single ``**doc("projections.create")`` call is all they
need.

Usage
-----
In any endpoint module::

    from app.api._openapi import doc

    @router.post("/projections", status_code=201, **doc("projections.create"))
    async def create_projection(...):
        ...

The function body and docstring stay *in the route file*.  Only decorator
metadata belongs here.

Adding a new endpoint
---------------------
1. Add a ``RouteDoc`` entry to ``DOCS`` keyed as ``"<router>.<operation>"``.
2. Add ``**doc("<router>.<operation>")`` to the route decorator.
3. Remove the now-redundant inline ``summary=`` / ``responses=`` kwargs.

Splitting this file
-------------------
If this file exceeds ~400 lines, convert ``app/api/_openapi.py`` into a
package::

    app/api/_openapi/
        __init__.py      ← re-exports DOCS and doc()
        _common.py       ← shared response snippets
        projections.py   ← projection entries
        events.py        ← event entries
        ...

``__init__.py`` simply merges the sub-dicts::

    from .projections import PROJECTION_DOCS
    from .events      import EVENT_DOCS
    DOCS = {**PROJECTION_DOCS, **EVENT_DOCS, ...}

No changes to any route file are needed when you split.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─── RouteDoc dataclass ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class RouteDoc:
    """Metadata for one API endpoint.

    All fields map directly to FastAPI route decorator kwargs.
    ``openapi_extra`` can carry anything the framework does not expose natively
    (e.g. multiple request-body examples, ``x-*`` vendor extensions).
    """

    summary: str
    description: str = ""
    responses: dict[int, dict[str, Any]] = field(default_factory=dict)
    tags: list[str] | None = None
    deprecated: bool = False
    openapi_extra: dict[str, Any] | None = None


# ─── Shared response snippets ─────────────────────────────────────────────────
# Define once, reference by unpacking into responses={} below.
# Keep descriptions short — they appear in Swagger/Redoc as tooltips.

_401 = {
    401: {
        "description": "Missing or invalid bearer token.",
        "content": {"application/json": {"example": {"detail": "Not authenticated"}}},
    }
}
_403 = {
    403: {
        "description": "Token lacks the required scope for this tenant.",
        "content": {"application/json": {"example": {"detail": "Insufficient permissions"}}},
    }
}
_404 = {
    404: {
        "description": "Resource not found.",
        "content": {"application/json": {"example": {"detail": "Not found"}}},
    }
}
_409 = {
    409: {
        "description": "Conflict — resource with that identity already exists.",
        "content": {"application/json": {"example": {"detail": "Already exists"}}},
    }
}
_422 = {
    422: {
        "description": "Request body or query parameter failed schema validation.",
    }
}
_429 = {
    429: {
        "description": "Rate limit exceeded.",
        "content": {"application/json": {"example": {"detail": "Rate limit exceeded"}}},
    }
}

# Convenience bundles
_STD     = {**_401, **_403, **_422}           # auth + validation only
_STD_429 = {**_STD, **_429}                   # auth + validation + rate-limit
_STD_404 = {**_STD, **_404}                   # auth + validation + not-found


# ─── Tag descriptions (rendered in Swagger UI sidebar) ────────────────────────
# Register via app.openapi_tags in main.py (see comment at bottom of file).

TAGS_METADATA = [
    {
        "name": "Events",
        "description": (
            "Core event ingestion and querying. "
            "Every write is SHA-256 hash-chained to the previous event for the subject."
        ),
    },
    {
        "name": "Chain Verification",
        "description": (
            "Cryptographic integrity checks. "
            "Inline for small tenants; background job for large ones."
        ),
    },
    {
        "name": "Projections",
        "description": (
            "Read-model projections built by continuously reducing the event stream. "
            "Register a named handler, then query its derived state per subject."
        ),
    },
    {
        "name": "Subjects",
        "description": "Subject registry — entities whose events Timeline tracks.",
    },
    {
        "name": "Connectors",
        "description": "Managed ingestion connectors (email, webhooks, custom adapters).",
    },
    {
        "name": "Tenants",
        "description": "Tenant provisioning and configuration.",
    },
    {
        "name": "Auth",
        "description": "Authentication and token management.",
    },
    {
        "name": "Health",
        "description": "Service liveness and readiness probes.",
    },
]


# ─── DOCS registry ────────────────────────────────────────────────────────────

DOCS: dict[str, RouteDoc] = {

    # ══════════════════════════════════════════════════════════════════════════
    # PROJECTIONS  (template — fully documented)
    # ══════════════════════════════════════════════════════════════════════════

    "projections.create": RouteDoc(
        summary="Create a projection definition",
        description="""
Register a new read-model projection over a subject's event stream.

A projection is a named reducer that Timeline evaluates continuously
against incoming events.  The engine discovers active definitions on
each worker cycle and advances their `last_event_seq` watermark by
applying new events through the registered handler, writing derived
state into the `projection_state` table.

**Idempotency:** `(tenant_id, name, version)` is a unique key.
Re-submitting the same triple returns `409 Conflict`.

**Watermark:** the engine always begins from `last_event_seq = 0`
on first creation, meaning the full subject history is replayed
before the projection is considered current.  Use
`POST /{tenant_id}/projections/{name}/{version}/rebuild` to reset
an existing projection to genesis.
        """,
        tags=["Projections"],
        responses={**_STD_429, **_409},
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "examples": {
                            "loan_balance": {
                                "summary": "Running loan balance",
                                "value": {
                                    "name": "loan_balance",
                                    "version": 1,
                                    "subject_type": "loan",
                                },
                            },
                            "claim_status": {
                                "summary": "Latest claim status (all subject types)",
                                "value": {
                                    "name": "claim_status",
                                    "version": 1,
                                    "subject_type": None,
                                },
                            },
                        }
                    }
                }
            }
        },
    ),

    "projections.list": RouteDoc(
        summary="List projection definitions",
        description="""
Return all projection definitions registered for the authenticated
tenant, including those marked `active=False`.

This endpoint is read-only and does not trigger rebuilds or cause
the projection engine to advance any watermark.
        """,
        tags=["Projections"],
        responses={**_STD},
    ),

    "projections.deactivate": RouteDoc(
        summary="Deactivate a projection",
        description="""
Set `active=False` on the projection identified by
`(tenant_id, name, version)`.

The projection engine skips deactivated definitions on subsequent
cycles:

- Existing rows in `projection_state` are preserved as-is.
- No new events are applied while the projection is inactive.
- Reactivation is not yet available via API; contact support or
  set `active=True` directly in the projection management use case.

Use this to pause or retire a projection without discarding its
historical derived state.
        """,
        tags=["Projections"],
        responses={**_STD, **_404},
    ),

    "projections.rebuild": RouteDoc(
        summary="Rebuild a projection from genesis",
        description="""
Reset the watermark (`last_event_seq`) to `0` for the projection
identified by `(tenant_id, name, version)`.

**This is an asynchronous operation.**  The call returns `202
Accepted` immediately.  On the next worker cycle the engine will:

1. Re-scan events for the relevant subjects starting from sequence 1.
2. Re-run the projection handler for each event in order.
3. Overwrite current rows in `projection_state` for this projection.

Use this when you change a projection handler's logic but keep the
same `(name, version)` and need all derived state recomputed.

To monitor progress, poll `GET /{tenant_id}/projections/{name}/{version}`
and inspect `last_event_seq`.
        """,
        tags=["Projections"],
        responses={
            **_STD,
            **_404,
            202: {"description": "Rebuild accepted; worker will process on next cycle."},
        },
    ),

    "projections.get_state": RouteDoc(
        summary="Get projection state for a subject",
        description="""
Return the derived state of a named projection for a single subject.

**Current state (default)** — omit `as_of`.  Reads the latest row
from `projection_state`.  Fast path suitable for dashboards and APIs.

**Point-in-time replay** — supply `as_of` (ISO-8601 datetime).  The
endpoint loads events for `(tenant_id, subject_id)` up to the given
timestamp, replays them through the registered handler, and returns
the reconstructed state.  This path does *not* read from or write to
`projection_state`.

A `404` is returned when either the projection definition or the
subject's state row does not exist (for the current-state path), or
when the ProjectionRegistry has no handler registered for
`(name, version)` (for the replay path).
        """,
        tags=["Projections"],
        responses={**_STD, **_404},
    ),

    "projections.list_states": RouteDoc(
        summary="List all subjects' projection state",
        description="""
Return a paginated window of current projection state rows for the
definition identified by `(tenant_id, name, version)`.

Only *current* state is returned — there is no point-in-time replay
on this endpoint.  Use the single-subject endpoint with `as_of` for
that.

This is the natural backing endpoint for projection-powered list
views, for example *"all mortgage applications with their current
processing status"* without touching the raw event stream.

If the projection definition does not exist, an empty list is
returned (not a 404).
        """,
        tags=["Projections"],
        responses={**_STD},
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # EVENTS
    # ══════════════════════════════════════════════════════════════════════════

    "events.create": RouteDoc(
        summary="Ingest an event",
        description="""
Write a single immutable event to the ledger.

Each event is SHA-256 hash-chained to the previous event for the
same `(tenant_id, subject_id)` pair.  The chain hash is computed and
stored server-side; clients cannot supply or override it.

**Schema validation** — if an `EventSchema` is registered for
`event_type`, the `payload` is validated against it before
persistence.  Validation failure returns `422`.

**Workflows** — if a `Flow` is configured to trigger on this
`event_type`, a workflow instance is created and its
`workflow_instance_id` is returned in the response.

**Idempotency** — supply `external_id` to make the write idempotent.
Re-submitting the same `(tenant_id, external_id)` pair returns the
original event rather than creating a duplicate.
        """,
        tags=["Events"],
        responses={**_STD_429, 400: {"description": "Payload failed registered schema validation."}},
    ),

    "events.list": RouteDoc(
        summary="List events",
        description="List events for the tenant, optionally filtered to a single subject. Ordered by event sequence ascending.",
        tags=["Events"],
        responses={**_STD},
    ),

    "events.get": RouteDoc(
        summary="Get an event",
        description="Retrieve a single event by its ID (tenant-scoped).",
        tags=["Events"],
        responses={**_STD, **_404},
    ),

    "events.count": RouteDoc(
        summary="Count events",
        description="Return the total event count for the tenant. Useful for dashboard statistics.",
        tags=["Events"],
        responses={**_STD},
    ),

    "events.stream": RouteDoc(
        summary="Stream events (SSE)",
        description="""
Open a Server-Sent Events stream of new events as they are ingested.

Optionally scope the stream to a single `subject_id` via query
parameter.  Each SSE `data:` frame is a JSON-serialised event
payload.

Clients should reconnect on disconnect using standard SSE retry
logic.  Requires `event:read` permission.
        """,
        tags=["Events"],
        responses={
            **_STD,
            200: {"description": "SSE stream opened; content-type: text/event-stream."},
            503: {"description": "Event stream broadcaster not available."},
        },
    ),

    # ── Chain verification ────────────────────────────────────────────────────

    "events.verify_subject": RouteDoc(
        summary="Verify a subject's chain",
        description="""
Recompute and verify the SHA-256 hash chain for all events belonging
to `subject_id` within the tenant.

Returns per-event validity, the first failing sequence number (if
any), and an overall `is_chain_valid` flag.

For tenants with very large event volumes per subject, this call may
time out (`504`).  Use the background job endpoints instead.
        """,
        tags=["Chain Verification"],
        responses={
            **_STD,
            429: {"description": "Subject event count exceeds inline verification limit."},
            504: {"description": "Verification timed out — use background job endpoint."},
        },
    ),

    "events.verify_tenant_inline": RouteDoc(
        summary="Verify all tenant chains (inline)",
        description="""
Verify the hash chain for every subject in the tenant synchronously.

For tenants with large event volumes, this will return `400` with a
suggestion to use the async background job instead.  The threshold is
configurable via `VERIFICATION_INLINE_LIMIT`.
        """,
        tags=["Chain Verification"],
        responses={
            **_STD,
            400: {"description": "Event volume too large for inline verification — use POST /verify/tenant/all/start."},
            408: {"description": "Verification timed out — use POST /verify/tenant/all/start."},
        },
    ),

    "events.verify_tenant_start": RouteDoc(
        summary="Start background verification job",
        description="""
Enqueue a background verification job for all tenant event chains.

Returns a `job_id` immediately.  Poll
`GET /events/verify/tenant/jobs/{job_id}` for status and results.
        """,
        tags=["Chain Verification"],
        responses={
            **_STD,
            202: {"description": "Job accepted and queued."},
        },
    ),

    "events.verify_job_status": RouteDoc(
        summary="Get verification job status",
        description="""
Retrieve the status and (once complete) the full result of a
background verification job.

Jobs are tenant-scoped — a tenant can only retrieve its own jobs.
Possible `status` values: `pending`, `running`, `completed`, `failed`.
        """,
        tags=["Chain Verification"],
        responses={**_STD, **_404},
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # HEALTH
    # ══════════════════════════════════════════════════════════════════════════

    "health.liveness": RouteDoc(
        summary="Liveness probe",
        description="Returns `200 OK` if the process is running. No auth required. Use for Kubernetes `livenessProbe`.",
        tags=["Health"],
    ),

    "health.readiness": RouteDoc(
        summary="Readiness probe",
        description="Returns `200 OK` when the database connection pool is healthy. Returns `503` otherwise. Use for Kubernetes `readinessProbe`.",
        tags=["Health"],
        responses={503: {"description": "Service not ready — database unavailable."}},
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # SUBJECTS  (scaffold — fill descriptions before Phase 6)
    # ══════════════════════════════════════════════════════════════════════════

    "subjects.create":  RouteDoc(summary="Create a subject",  tags=["Subjects"], responses={**_STD, **_409}),
    "subjects.list":    RouteDoc(summary="List subjects",     tags=["Subjects"], responses={**_STD}),
    "subjects.get":     RouteDoc(summary="Get a subject",     tags=["Subjects"], responses={**_STD, **_404}),
    "subjects.update":  RouteDoc(summary="Update a subject",  tags=["Subjects"], responses={**_STD, **_404}),
    "subjects.delete":  RouteDoc(summary="Delete a subject",  tags=["Subjects"], responses={**_STD, **_404}),

    # ══════════════════════════════════════════════════════════════════════════
    # CONNECTORS  (scaffold)
    # ══════════════════════════════════════════════════════════════════════════

    "connectors.create":  RouteDoc(summary="Register a connector",  tags=["Connectors"], responses={**_STD, **_409}),
    "connectors.list":    RouteDoc(summary="List connectors",        tags=["Connectors"], responses={**_STD}),
    "connectors.get":     RouteDoc(summary="Get a connector",        tags=["Connectors"], responses={**_STD, **_404}),
    "connectors.start":   RouteDoc(summary="Start a connector",      tags=["Connectors"], responses={**_STD, **_404}),
    "connectors.stop":    RouteDoc(summary="Stop a connector",       tags=["Connectors"], responses={**_STD, **_404}),
    "connectors.delete":  RouteDoc(summary="Delete a connector",     tags=["Connectors"], responses={**_STD, **_404}),

    # ══════════════════════════════════════════════════════════════════════════
    # TENANTS  (scaffold)
    # ══════════════════════════════════════════════════════════════════════════

    "tenants.create":  RouteDoc(summary="Provision a tenant",  tags=["Tenants"], responses={**_STD, **_409}),
    "tenants.get":     RouteDoc(summary="Get tenant details",  tags=["Tenants"], responses={**_STD, **_404}),
    "tenants.update":  RouteDoc(summary="Update a tenant",     tags=["Tenants"], responses={**_STD, **_404}),
    "tenants.delete":  RouteDoc(summary="Delete a tenant",     tags=["Tenants"], responses={**_STD, **_404}),

    # ══════════════════════════════════════════════════════════════════════════
    # AUTH  (scaffold)
    # ══════════════════════════════════════════════════════════════════════════

    "auth.token":   RouteDoc(summary="Issue an API token",   tags=["Auth"], responses={**_422, 401: _401[401]}),
    "auth.refresh": RouteDoc(summary="Refresh a token",      tags=["Auth"], responses={**_422, 401: _401[401]}),
    "auth.revoke":  RouteDoc(summary="Revoke a token",       tags=["Auth"], responses={**_STD}),
}


# ─── doc() helper ─────────────────────────────────────────────────────────────

def doc(route_id: str) -> dict[str, Any]:
    """Return FastAPI route decorator kwargs for the given route ID.

    Raises ``KeyError`` (with a clear message) if the ID is not registered,
    so missing entries fail at import time rather than silently producing an
    undocumented endpoint.

    Example::

        @router.post("/projections", status_code=201, **doc("projections.create"))
        async def create_projection(...):
            ...
    """
    if route_id not in DOCS:
        raise KeyError(
            f"No OpenAPI doc registered for route '{route_id}'. "
            f"Add a RouteDoc entry to app/api/_openapi.py."
        )
    d = DOCS[route_id]
    out: dict[str, Any] = {"summary": d.summary}
    if d.description:
        out["description"] = d.description.strip()
    if d.responses:
        out["responses"] = d.responses
    if d.tags:
        out["tags"] = d.tags
    if d.deprecated:
        out["deprecated"] = True
    if d.openapi_extra:
        out["openapi_extra"] = d.openapi_extra
    return out


# ─── Note for main.py ─────────────────────────────────────────────────────────
# To render tag descriptions in Swagger UI, pass TAGS_METADATA to your app:
#
#   from app.api._openapi import TAGS_METADATA
#
#   app = FastAPI(
#       title="Timeline API",
#       openapi_tags=TAGS_METADATA,
#       ...
#   )
