"""Application configuration (settings and environment).

Single source of truth for all configuration. Uses pydantic-settings
with .env support. Required fields (e.g. DATABASE_URL, SECRET_KEY) are
validated at load time.
"""

from functools import lru_cache
from typing import Literal

from pathlib import Path
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Directory holding pyproject.toml: this file is app/core/config.py, so three
# parents up. Used to resolve files that belong to the project rather than to
# whatever directory a command happened to be run from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# The repository root, two levels above apps/api. One .env lives there and both
# the API and the web client read it, because a deployment is a single process
# with a single environment: two files in development would put back the
# development/production split this layout exists to remove.
_REPO_ROOT = _PROJECT_ROOT.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment and .env.

    All settings are optional with defaults except those validated in
    validate_required_and_storage (database_url, secret_key, encryption_salt,
    and storage backend when applicable).
    """

    # App
    app_name: str = "timeline"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database: PostgreSQL only (SQLAlchemy + Alembic)
    database_url: str = ""
    database_echo: bool = False
    # Optional pool/driver overrides (None = use defaults in database.py)
    db_pool_size: int | None = None
    db_max_overflow: int | None = None
    db_query_cache_size: int | None = None
    db_command_timeout: int | None = None
    db_disable_jit: bool = True

    # Security
    secret_key: SecretStr = SecretStr("")
    algorithm: str = "HS256"
    # Short-lived: the client renews quietly against /auth/refresh, so a short
    # window costs users nothing and limits how long a leaked token is useful.
    access_token_expire_minutes: int = 30
    # How long someone can stay signed in without re-entering their password.
    refresh_token_expire_days: int = 14
    # Refresh token cookie. httpOnly so page scripts cannot read it. Leave
    # refresh_cookie_secure true in production; set false only for plain-http local dev.
    refresh_cookie_name: str = "timeline_refresh"
    refresh_cookie_secure: bool = True
    refresh_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    refresh_cookie_domain: str | None = None
    encryption_salt: SecretStr = SecretStr("")
    # Credential storage (email/OAuth): use a separate secret so JWT key rotation does not break stored credentials.
    credential_encryption_secret: SecretStr | None = None
    # Optional KDF salt for envelope encryption: set ENCRYPTION_KDF_SALT (base64) or
    # ENCRYPTION_KDF_SALT_PATH (file path); if unset, a default path under storage_root is used.
    encryption_kdf_salt: str = ""
    encryption_kdf_salt_path: str = ""

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"

    # Storage
    storage_backend: str = "local"
    storage_root: str = "./storage"  # Dev-friendly default; set STORAGE_ROOT for production (e.g. /var/timeline/storage)
    storage_base_url: str | None = None
    s3_bucket: str | None = None
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: SecretStr | None = None
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    allowed_mime_types: str = "*/*"
    # Document retention: soft-delete documents older than this (days). None = disabled.
    default_document_retention_days: int | None = None

    # Tenant
    tenant_header_name: str = "X-Tenant-ID"

    # OAuth audit PII retention (GDPR): days to keep ip_address/user_agent before purge.
    # Run purge_oauth_audit_pii (e.g. via cron) to anonymize after this period.
    oauth_audit_pii_retention_days: int = 90

    # Email webhook: if set, POST /email-accounts/{id}/webhook must send
    # X-Webhook-Signature-256: sha256=<hex(hmac_sha256(secret, body))>.
    email_webhook_secret: SecretStr | None = None

    # Tenant creation: optional shared secret for POST /api/v1/tenants.
    # When set, the endpoint requires X-Create-Tenant-Secret header to match.
    # In production, this should be set; when unset, tenant creation can be
    # disabled at the route level.
    create_tenant_secret: SecretStr | None = None
    # Base URL for set-password link (C2 flow). E.g. https://app.example.com or
    # http://localhost:3000. Link returned as {set_password_base_url}/set-password?token=...
    # When empty, set_password_url is not included in tenant create response.
    set_password_base_url: str = ""

    # Chain anchoring (RFC 3161). Opt-in; job runs only when enabled.
    chain_anchor_enabled: bool = False
    chain_anchor_interval_seconds: int = 300  # 5 minutes
    chain_anchor_tsa_url: str = "https://freetsa.org/tsr"
    chain_anchor_tsa_cert_path: str | None = None  # path to TSA root cert for prod verification
    chain_anchor_tsa_timeout_seconds: int = 10
    # Integrity epoch sealing: seal due epochs and open next; TSA for COMPLIANCE/LEGAL_GRADE.
    epoch_sealing_enabled: bool = False
    # TSA batch anchoring (COMPLIANCE profile): background job drains queue and anchors batches.
    tsa_batch_enabled: bool = False
    tsa_batch_interval_seconds: int = 60
    tsa_batch_max_events: int = 500

    # Request / middleware
    request_timeout_seconds: int = 60
    request_id_header: str = "X-Request-ID"
    correlation_id_header: str = "X-Correlation-ID"

    # Verification: tenant-wide chain verification (fail-fast over limit; use background job for large tenants).
    verification_max_events: int = 100_000
    verification_timeout_seconds: int = 55
    # In-memory job store: evict jobs older than this (seconds since creation). Stops unbounded growth.
    verification_job_max_age_seconds: int = 86400  # 24 hours
    # After a job reaches terminal state (completed/failed), keep it for this long (seconds) then evict.
    verification_job_grace_period_seconds: int = 3600  # 1 hour

    # RLS readiness: when True, GET /api/v1/health/ready runs RLS checks.
    rls_readiness_check: bool = False
    # App role for RLS check (default: user from DATABASE_URL). Set RLS_CHECK_APP_ROLE to override.
    rls_check_app_role: str | None = None
    # When True, readiness also requires at least one tenant_isolation policy to exist.
    rls_check_policies: bool = False

    # Redis Cache
    redis_enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: SecretStr | None = None
    redis_max_connections: int = 10
    cache_ttl_permissions: int = 300
    cache_ttl_schemas: int = 600
    cache_ttl_tenants: int = 900

    # Connectors (platform event ingestion)
    connector_email_enabled: bool = False
    connector_email_tenant_id: str | None = None
    connector_email_poll_interval_seconds: float = 60.0

    # Event rate limits (per-tenant, per minute)
    rate_limit_events_per_minute_per_tenant: int = 10_000
    rate_limit_bulk_events_per_minute_per_tenant: int = 50_000

    # Projection engine (Phase 5)
    projection_engine_enabled: bool = False
    projection_engine_interval_seconds: int = 5
    projection_engine_batch_size: int = 1000

    # OpenTelemetry
    telemetry_enabled: bool = True
    telemetry_exporter: str = "console"
    telemetry_otlp_endpoint: str | None = None
    telemetry_jaeger_endpoint: str | None = None
    telemetry_sample_rate: float = 1.0
    telemetry_environment: str = "development"

    model_config = SettingsConfigDict(
        # Anchored to the project directory rather than the process working
        # directory. A relative ".env" resolves against wherever the command was
        # run from, so the API picked up a different file (or none) depending on
        # whether you started it from the project root or a parent. That becomes a
        # silent failure once this package sits under apps/api in a monorepo.
        # Shared file first, app-local second: later entries win, so a private
        # apps/api/.env can still override the shared one without editing it.
        env_file=(_REPO_ROOT / ".env", _PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def _validate_required_env(self) -> None:
        """The three settings the application cannot start without."""
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is required. Set in environment or .env file "
                "(e.g. postgresql+asyncpg://user:pass@localhost:5432/dbname)."
            )
        if not self.secret_key.get_secret_value():
            raise ValueError(
                "SECRET_KEY is required. Generate with: openssl rand -hex 32. "
                "On Vercel: set in Project → Settings → Environment Variables."
            )
        if not self.encryption_salt.get_secret_value():
            raise ValueError(
                "ENCRYPTION_SALT is required. Generate with: openssl rand -hex 16. "
                "On Vercel: set in Project → Settings → Environment Variables."
            )

    def _validate_storage_backend(self) -> None:
        """The storage backend must be one we implement, and s3 needs a bucket."""
        if self.storage_backend == "s3":
            if not self.s3_bucket:
                raise ValueError(
                    "s3_bucket is required when storage_backend is 's3'. "
                    "Set S3_BUCKET environment variable or update .env file."
                )
        elif self.storage_backend != "local":
            raise ValueError(
                f"Invalid storage_backend '{self.storage_backend}'. "
                "Must be one of: 'local', 's3'"
            )

    def _validate_production_safety(self) -> None:
        """Settings that are merely inadvisable in development but unsafe in production."""
        # Production: do not run with debug=True (leaks stack traces in 500 responses).
        if self.telemetry_environment == "production" and self.debug:
            raise ValueError(
                "debug must be False when telemetry_environment is 'production'. "
                "Set DEBUG=false or TELEMETRY_ENVIRONMENT=development."
            )
        # CORS: wildcard origins with credentials are insecure.
        origins = [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
        if "*" in origins or self.allowed_origins.strip() == "*":
            raise ValueError(
                "allowed_origins must not be '*' (use explicit origins, e.g. "
                "ALLOWED_ORIGINS=https://app.example.com)."
            )

    def _connector_requirements(self) -> list[tuple[bool, object, str]]:
        """(enabled, required value, message) for each connector setting, in report order."""
        return [
            (
                self.connector_email_enabled,
                self.connector_email_tenant_id,
                "CONNECTOR_EMAIL_TENANT_ID is required when CONNECTOR_EMAIL_ENABLED=true.",
            ),
        ]

    def _validate_connectors(self) -> None:
        """Connectors: fail fast when enabled but required config is missing."""
        for enabled, value, message in self._connector_requirements():
            if enabled and not value:
                raise ValueError(message)

    @model_validator(mode="after")
    def validate_required_and_storage(self) -> "Settings":
        """Validate required env and storage backend.

        DATABASE_URL is required (PostgreSQL). Storage backend validated below.
        Checks run in the order the messages are most useful: missing secrets first,
        then storage, then production safety, then connectors.
        """
        self._validate_required_env()
        self._validate_storage_backend()
        self._validate_production_safety()
        self._validate_connectors()
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (single instance per process).

    Validation runs on first call, not at import time. In tests, call
    get_settings.cache_clear() before overriding env vars so the next
    get_settings() uses the new values.

    Returns:
        Loaded and validated Settings instance.
    """
    return Settings()
