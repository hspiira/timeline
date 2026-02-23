"""Search API: full-text search across subjects, events, documents."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_search_service, get_tenant_id, require_permission
from app.application.use_cases.search import SearchService
from app.schemas.search import SearchResponse, SearchResultItemResponse

router = APIRouter()


@router.get("", response_model=SearchResponse)
async def search(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    search_svc: Annotated[SearchService, Depends(get_search_service)],
    _: Annotated[object, Depends(require_permission("subject", "read"))] = None,
    q: str = Query(..., min_length=1, max_length=500),
    scope: Literal["all", "subjects", "events", "documents"] = Query(
        "all", description="Search scope"
    ),
    limit: int = Query(50, ge=1, le=100),
):
    """Full-text search within tenant (subjects, events, documents metadata)."""
    items = await search_svc.search(tenant_id=tenant_id, q=q, scope=scope, limit=limit)
    return SearchResponse(
        results=[
            SearchResultItemResponse(
                resource_type=i.resource_type,
                id=i.id,
                tenant_id=i.tenant_id,
                snippet=i.snippet,
                subject_id=i.subject_id,
                display_title=i.display_title,
            )
            for i in items
        ]
    )
