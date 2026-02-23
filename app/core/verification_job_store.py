"""In-memory store for chain verification background jobs.

Single place for job state; no shared mutable dict on app.state.
Jobs are keyed by job_id; optional TTL can be added later.
"""

from __future__ import annotations

from typing import Any

from app.shared.utils.datetime import utc_now


class VerificationJobStore:
    """In-memory store for verification job status and results."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def set(self, job_id: str, tenant_id: str) -> None:
        """Register a new job as pending."""
        self._jobs[job_id] = {
            "tenant_id": tenant_id,
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": utc_now(),
        }

    def get(self, job_id: str) -> dict[str, Any] | None:
        """Return job payload or None if not found."""
        return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        status: str,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """Update job status and optional result/error."""
        job = self._jobs.get(job_id)
        if not job:
            return
        job["status"] = status
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
