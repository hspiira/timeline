"""Integrity profile configuration.

Maps IntegrityProfile enums to operational parameters used by services.
"""

from dataclasses import dataclass

from app.domain.enums import IntegrityProfile

# Max seal attempts before marking epoch FAILED; used by sealing job and get_sealable_epochs filter.
EPOCH_SEAL_MAX_RETRIES = 3


@dataclass(frozen=True)
class IntegrityProfileConfig:
    """Configuration for an integrity profile."""

    seal_seconds: int
    seal_event_count: int
    tsa_enabled: bool
    merkle_enabled: bool
    repair_four_eyes_required: bool


INTEGRITY_PROFILE_CONFIG: dict[IntegrityProfile, IntegrityProfileConfig] = {
    IntegrityProfile.STANDARD: IntegrityProfileConfig(
        seal_seconds=86400,  # 24h
        seal_event_count=10_000,
        tsa_enabled=False,
        merkle_enabled=False,
        repair_four_eyes_required=False,
    ),
    IntegrityProfile.COMPLIANCE: IntegrityProfileConfig(
        seal_seconds=3600,  # 1h
        seal_event_count=1_000,
        tsa_enabled=True,
        merkle_enabled=False,
        repair_four_eyes_required=True,
    ),
    IntegrityProfile.LEGAL_GRADE: IntegrityProfileConfig(
        seal_seconds=900,  # 15m
        seal_event_count=100,
        tsa_enabled=True,
        merkle_enabled=True,
        repair_four_eyes_required=True,
    ),
}


_configured_profiles = set(INTEGRITY_PROFILE_CONFIG.keys())
_defined_profiles = set(IntegrityProfile)
if _configured_profiles != _defined_profiles:
    missing = sorted(p.name for p in _defined_profiles - _configured_profiles)
    extra = sorted(p.name for p in _configured_profiles - _defined_profiles)
    details = []
    if missing:
        details.append(f"missing={','.join(missing)}")
    if extra:
        details.append(f"extra={','.join(extra)}")
    joined = "; ".join(details) if details else "profile mapping mismatch"
    raise RuntimeError(
        "INTEGRITY_PROFILE_CONFIG must cover exactly all IntegrityProfile members; "
        f"{joined}"
    )

