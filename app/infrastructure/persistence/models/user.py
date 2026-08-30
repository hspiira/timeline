"""User ORM model: a person's membership of one organisation (tenant-scoped).

The credential lives on :class:`~app.infrastructure.persistence.models.identity.Identity`,
not here. This row says "this person belongs to this organisation, under this
handle". One person in three organisations has three of these rows and one
identity, so there is a single place to change a password or disable them.
"""

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.identity import Identity
from app.infrastructure.persistence.models.mixins import MultiTenantModel


class User(MultiTenantModel, Base):
    """Membership row. Table: app_user. Unique (tenant_id, username) and (tenant_id, identity_id)."""

    __tablename__ = "app_user"

    identity_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("identity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False)

    # Whether this person may use THIS organisation. Deactivating here has no
    # effect on their access to any other organisation, and does not touch their
    # identity — that is deliberate, so one customer cannot lock a person out of
    # another customer's workspace. Compare ``Identity.is_active``.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    # Eager-loaded: callers almost always need the email, and lazy loading on an
    # async session raises rather than silently querying.
    identity: Mapped[Identity] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_tenant_username"),
        UniqueConstraint("tenant_id", "identity_id", name="uq_tenant_identity"),
    )

    @property
    def email(self) -> str:
        """The person's email, from their identity."""
        return self.identity.email
