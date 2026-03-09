"""In-memory store for chain verification background jobs.

Single place for job state; no shared mutable dict on app.state.
Jobs are keyed by job_id. Eviction by max age (since creation) and by
grace period after terminal state (completed/failed) keeps the store bounded.
"""

from __future__ import annotations

import time
from typing import Any

from app.shared.utils.datetime import utc_now

# Sentinel: "not provided" so update() can distinguish from explicit None.
_UNSET: object = object()

# Defaults when not passed from config (e.g. tests).
DEFAULT_MAX_JOB_AGE_SECONDS = 86400  # 24 hours
DEFAULT_GRACE_PERIOD_SECONDS = 3600  # 1 hour after completed/failed

_TERMINAL_STATUSES = ("completed", "failed")


class VerificationJobStore:
    """In-memory store for verification job status and results.

    Evicts jobs older than max_age_seconds (since created_at) and jobs in
    terminal state (completed/failed) that have been finished longer than
    grace_period_seconds. Eviction runs on get(), set(), and update().
    """

    def __init__(
        self,
        max_age_seconds: int = DEFAULT_MAX_JOB_AGE_SECONDS,
        grace_period_seconds: int = DEFAULT_GRACE_PERIOD_SECONDS,
    ) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._max_age_seconds = max_age_seconds
        self._grace_period_seconds = grace_period_seconds

    def _evict_expired(self) -> None:
        """Remove jobs that exceed max age or terminal-state grace period."""
        now = utc_now()
        now_mono = time.monotonic()
        expired = []
        for k, v in self._jobs.items():
            created_at = v.get("created_at")
            if created_at is not None and (now - created_at).total_seconds() > self._max_age_seconds:
                expired.append(k)
                continue
            if v.get("status") in _TERMINAL_STATUSES:
                finished_at = v.get("_finished_at")
                if finished_at is not None and (now_mono - finished_at) > self._grace_period_seconds:
                    expired.append(k)
        for k in expired:
            del self._jobs[k]

    def set(self, job_id: str, tenant_id: str) -> None:
        """Register a new job as pending."""
        self._evict_expired()
        self._jobs[job_id] = {
            "tenant_id": tenant_id,
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": utc_now(),
        }

    def get(self, job_id: str) -> dict[str, Any] | None:
        """Return job payload or None if not found."""
        self._evict_expired()
        return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        status: str,
        result: object = _UNSET,
        error: object = _UNSET,
    ) -> None:
        """Update job status and optional result/error.

        Use _UNSET (default) to leave result/error unchanged; pass None to clear.
        """
        job = self._jobs.get(job_id)
        if not job:
            return
        job["status"] = status
        if result is not _UNSET:
            job["result"] = result
        if error is not _UNSET:
            job["error"] = error
        if status in _TERMINAL_STATUSES:
            job["_finished_at"] = time.monotonic()
        self._evict_expired()
