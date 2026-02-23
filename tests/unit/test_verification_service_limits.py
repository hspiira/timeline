"""VerificationService unit tests: limit and timeout behavior (DoS hardening)."""

from unittest.mock import AsyncMock

import pytest

from app.application.services.verification_service import VerificationService
from app.domain.exceptions import VerificationLimitExceededException


@pytest.fixture
def event_repo():
    """Mock event repo."""
    repo = AsyncMock()
    repo.get_by_tenant = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def hash_service():
    """Mock hash service."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_verify_tenant_chains_raises_when_event_count_exceeds_max(
    event_repo,
    hash_service,
) -> None:
    """When tenant event count exceeds max_events, VerificationLimitExceededException is raised."""
    event_repo.count_by_tenant = AsyncMock(return_value=150_000)
    svc = VerificationService(
        event_repo=event_repo,
        hash_service=hash_service,
        max_events=100_000,
        timeout_seconds=60,
    )
    with pytest.raises(VerificationLimitExceededException) as exc_info:
        await svc.verify_tenant_chains(tenant_id="t1")
    assert exc_info.value.details.get("total_events") == 150_000
    assert exc_info.value.details.get("max_events") == 100_000
    # Repo should not have been asked to fetch events (fail-fast).
    event_repo.get_by_tenant.assert_not_called()
