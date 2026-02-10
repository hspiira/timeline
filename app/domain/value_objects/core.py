"""Domain value objects for the Timeline application.

Value objects are immutable types that represent domain concepts with
self-validation. They have no identity, only value.
"""

import re
from dataclasses import dataclass
from typing import ClassVar

# Shared slug pattern: lowercase alphanumeric with optional hyphens (e.g. acme-corp).
_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass(frozen=True)
class TenantCode:
    """Value object for tenant code (SRP: tenant code validation).

    Tenant codes must be 3-15 characters, lowercase alphanumeric with
    optional hyphens (e.g. 'acme', 'acme-corp'). Immutable once activated.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate format and length.

        Raises:
            ValueError: If empty, length out of range, or invalid format.
        """
        if not self.value:
            raise ValueError("Tenant code must be a non-empty string")
        if len(self.value) < 3 or len(self.value) > 15:
            raise ValueError("Tenant code must be 3-15 characters")
        if not _SLUG_RE.match(self.value):
            raise ValueError(
                "Tenant code must be lowercase alphanumeric with optional hyphens "
                "(e.g., 'acme', 'acme-corp', 'abc123')"
            )


@dataclass(frozen=True)
class SubjectType:
    """Value object for subject type (SRP).

    Subject types are lowercase alphanumeric with optional hyphens,
    max 150 characters (e.g. 'client', 'policy').
    """

    value: str

    def __post_init__(self) -> None:
        """Validate non-empty, length, and format.

        Raises:
            ValueError: If empty, too long, or invalid format.
        """
        if not self.value:
            raise ValueError("Subject type must be a non-empty string")
        if len(self.value) > 150:
            raise ValueError("Subject type must not exceed 150 characters")
        if not _SLUG_RE.match(self.value):
            raise ValueError(
                "Subject type must be lowercase alphanumeric with optional hyphens "
                "(e.g., 'client', 'policy', 'supplier')"
            )


@dataclass(frozen=True)
class EventType:
    """Value object for event type with domain validation (SRP).

    Event types are free-form strings; VALID_TYPES documents standard
    types. Custom types are allowed for extensibility.
    """

    value: str

    # Standard event types (reference only - custom types are allowed)
    VALID_TYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "created",
            "updated",
            "deleted",
            "status_changed",
            "metadata_updated",
            "relationship_added",
            "relationship_removed",
        }
    )

    def __post_init__(self) -> None:
        """Validate non-empty. Custom types are allowed.

        Raises:
            ValueError: If event type is empty.
        """
        if not self.value:
            raise ValueError("Event type must be a non-empty string")


@dataclass(frozen=True)
class Hash:
    """Value object for cryptographic hash (SRP).

    Must be a SHA-256 (64 hex chars) or SHA-512 (128 hex chars) string.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate length and hex characters.

        Raises:
            ValueError: If empty, wrong length, or non-hex.
        """
        # Normalize to lowercase for consistent comparisons
        object.__setattr__(self, "value", self.value.lower())
        if not self.value:
            raise ValueError("Hash must be a non-empty string")
        if len(self.value) not in (64, 128):
            raise ValueError(
                "Hash must be a valid SHA-256 (64 chars) or SHA-512 (128 chars) hex string"
            )
        if not all(c in "0123456789abcdef" for c in self.value):
            raise ValueError("Hash must contain only hexadecimal characters")


@dataclass(frozen=True)
class EventChain:
    """Value object representing the chain relationship (SRP).

    Links current event hash to previous event hash. Enforces that
    current_hash does not equal previous_hash (no self-reference).
    """

    current_hash: Hash
    previous_hash: Hash | None

    def __post_init__(self) -> None:
        """Enforce chain invariants at construction time.

        Raises:
            ValueError: If current_hash equals previous_hash.
        """
        if self.previous_hash is not None:
            if self.current_hash.value == self.previous_hash.value:
                raise ValueError(
                    "current_hash cannot reference itself (current_hash == previous_hash)"
                )

    def is_genesis_event(self) -> bool:
        """Return whether this is the first event in the chain.

        Returns:
            True if there is no previous hash (genesis event).
        """
        return self.previous_hash is None
