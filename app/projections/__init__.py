"""Projection handlers: import all modules so handlers register at startup."""

from app.projections import audit

__all__ = ["audit"]
