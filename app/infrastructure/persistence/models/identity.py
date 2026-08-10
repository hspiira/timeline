"""Identity ORM model: one row per person, global rather than tenant-scoped.

Holds the credential. A person who belongs to several organisations has one
identity here and one ``app_user`` membership per organisation, so a password
change, a deactivation, or a future passkey link happens once.

Emails are stored lower-cased; use :func:`normalise_email` before writing or
looking up, because the unique constraint is on the stored value.

No ``tenant_id`` and no RLS policy, by design: this table holds no tenant
business data, and sign-in has to read it before any organisation is known.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.mixins import CuidMixin, TimestampMixin
from app.shared.utils.email import normalise_email

__all__ = ["Identity", "normalise_email"]


class Identity(CuidMixin, TimestampMixin, Base):
    """A person. Table: identity. Unique on email across the whole system."""

    __tablename__ = "identity"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(96), nullable=False)

    # SYSTEM-WIDE kill switch: false means this person cannot sign in anywhere.
    # This is NOT how you remove someone from an organisation — that is
    # ``app_user.is_active``, which affects only that one organisation. Do not
    # expose this to tenant administrators, or one customer could lock a person
    # out of a different customer's data.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
