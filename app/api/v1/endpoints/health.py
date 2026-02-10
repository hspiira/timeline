"""Health check endpoint. No dependencies; used for liveness probes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def health_check() -> dict[str, str]:
    """Return simple ok status for liveness."""
    return {"status": "ok"}
