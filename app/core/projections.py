"""Projection handler registry and @projection decorator (Phase 5)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.application.dtos.event import EventResult


@dataclass
class ProjectionRegistration:
    """Registered projection handler: name, version, subject_type, handler."""

    name: str
    version: int
    subject_type: str | None
    handler: Callable[..., Awaitable[dict[str, Any]]]


class ProjectionRegistry:
    """Singleton registry of all @projection-decorated handlers."""

    _handlers: dict[tuple[str, int], ProjectionRegistration] = {}

    def register(
        self,
        name: str,
        version: int,
        subject_type: str | None,
        fn: Callable[..., Awaitable[dict[str, Any]]],
    ) -> None:
        """Register a projection handler."""
        self._handlers[(name, version)] = ProjectionRegistration(
            name=name,
            version=version,
            subject_type=subject_type,
            handler=fn,
        )

    def get(self, name: str, version: int) -> ProjectionRegistration | None:
        """Return registration for (name, version), or None."""
        return self._handlers.get((name, version))

    def all(self) -> list[ProjectionRegistration]:
        """Return all registered handlers."""
        return list(self._handlers.values())


_registry = ProjectionRegistry()


def projection(
    name: str,
    *,
    version: int = 1,
    subject_type: str | None = None,
) -> Callable[[Callable[..., Awaitable[dict[str, Any]]]], Callable[..., Awaitable[dict[str, Any]]]]:
    """Decorator to register a projection handler.

    Args:
        name: Projection name (must match definition row).
        version: Projection version (must match definition row).
        subject_type: Optional subject type filter; None = all subject types.

    Returns:
        Decorator that registers the function and returns it unchanged.
    """

    def decorator(
        fn: Callable[..., Awaitable[dict[str, Any]]],
    ) -> Callable[..., Awaitable[dict[str, Any]]]:
        _registry.register(name, version, subject_type, fn)
        return fn

    return decorator


def get_registry() -> ProjectionRegistry:
    """Return the global projection registry."""
    return _registry
