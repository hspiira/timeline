"""Search and dashboard analytics dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.analytics import GetDashboardStatsUseCase
from app.application.use_cases.search import SearchService
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories import (
    DocumentRepository,
    EventRepository,
    SearchRepository,
    SubjectRepository,
)

from . import document
from . import event
from . import subject


async def get_search_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchRepository:
    """Search repository for full-text search (read-only)."""
    return SearchRepository(db)


async def get_search_service(
    search_repo: Annotated[SearchRepository, Depends(get_search_repo)],
) -> SearchService:
    """Search use case (full-text across subjects, events, documents)."""
    return SearchService(search_repo)


async def get_dashboard_stats_use_case(
    subject_repo: Annotated[SubjectRepository, Depends(subject.get_subject_repo)],
    event_repo: Annotated[EventRepository, Depends(event.get_event_repo)],
    document_repo: Annotated[DocumentRepository, Depends(document.get_document_repo)],
) -> GetDashboardStatsUseCase:
    """Dashboard stats use case (counts and recent activity)."""
    return GetDashboardStatsUseCase(
        subject_repo=subject_repo,
        event_repo=event_repo,
        document_repo=document_repo,
    )
