"""Naming template dependencies (composition root)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import get_db, get_db_transactional
from app.infrastructure.persistence.repositories import NamingTemplateRepository


async def get_naming_template_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NamingTemplateRepository:
    """Naming template repository for read operations."""
    return NamingTemplateRepository(db)


async def get_naming_template_repo_for_write(
    db: Annotated[AsyncSession, Depends(get_db_transactional)],
) -> NamingTemplateRepository:
    """Naming template repository for create/update/delete."""
    return NamingTemplateRepository(db)
