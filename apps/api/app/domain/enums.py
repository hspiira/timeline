"""Domain enumerations for the Timeline application.

Enums represent fixed sets of domain values (e.g. tenant status).
"""

from enum import Enum


class TenantStatus(str, Enum):
    """Tenant lifecycle status.

    Determines whether a tenant can create events and accept API traffic.
    """

    ACTIVE = "Active"
    SUSPENDED = "Suspended"
    ARCHIVED = "Archived"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid status values as strings.

        Returns:
            List of enum value strings (e.g. for validation or serialization).
        """
        return [status.value for status in cls]


class IntegrityProfile(str, Enum):
    """Integrity profile for tenant-level chain guarantees.

    Controls epoch sealing cadence, TSA anchoring, Merkle usage, and repair workflow strictness.
    """

    STANDARD = "Standard"
    COMPLIANCE = "Compliance"
    LEGAL_GRADE = "Legal Grade"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid integrity profile values as strings."""
        return [profile.value for profile in cls]


class IntegrityEpochStatus(str, Enum):
    """Integrity epoch lifecycle status."""

    OPEN = "Open"
    SEALED = "Sealed"
    FAILED = "Failed"
    BROKEN = "Broken"
    REPAIRED = "Repaired"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid epoch status values as strings."""
        return [status.value for status in cls]


class ChainRepairStatus(str, Enum):
    """Chain repair workflow status."""

    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    COMPLETED = "Completed"
    FAILED = "Failed"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid chain repair status values as strings."""
        return [status.value for status in cls]


class EventIntegrityStatus(str, Enum):
    """Event integrity status (chain and anchoring)."""

    VALID = "Valid"
    CHAIN_BREAK = "Chain Break"
    REPAIRED = "Repaired"
    ERASED = "Erased"
    PENDING_ANCHOR = "Pending Anchor"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid event integrity status values as strings."""
        return [s.value for s in cls]


class TsaVerificationStatus(str, Enum):
    """TSA anchor verification outcome."""

    PENDING = "Pending"
    VERIFIED = "Verified"
    FAILED = "Failed"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid TSA verification status values as strings."""
        return [s.value for s in cls]


class TsaAnchorType(str, Enum):
    """Type of payload anchored with TSA."""

    EPOCH = "Epoch"
    BATCH = "Batch"
    EVENT = "Event"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid TSA anchor type values as strings."""
        return [s.value for s in cls]


class ChainAnchorStatus(str, Enum):
    """Chain anchor lifecycle (tenant/subject tip anchoring)."""

    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    FAILED = "Failed"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid chain anchor status values as strings."""
        return [s.value for s in cls]


class TaskStatus(str, Enum):
    """Task lifecycle status."""

    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    CANCELLED = "Cancelled"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid task status values as strings."""
        return [s.value for s in cls]
