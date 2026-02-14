"""Application configuration (settings and environment).

Single source of truth for all configuration. Uses pydantic-settings
with .env support. Required fields (e.g. DATABASE_URL, SECRET_KEY) are
validated at load time.
"""

from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Database: "postgres" (SQLAlchemy + Alembic) or "firestore" (Firestore only)
    database_backend: str = "firestore"
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
    access_token_expire_minutes: int = 480  # 8 hours
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
    storage_root: str = "/var/timeline/storage"
    storage_base_url: str | None = None
    s3_bucket: str | None = None
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: SecretStr | None = None
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    allowed_mime_types: str = "*/*"

    # Tenant
    tenant_header_name: str = "X-Tenant-ID"

    # OAuth audit PII retention (GDPR): days to keep ip_address/user_agent before purge.
    # Run purge_oauth_audit_pii (e.g. via cron) to anonymize after this period.
    oauth_audit_pii_retention_days: int = 90

    # Email webhook: if set, POST /email-accounts/{id}/webhook must send
    # X-Webhook-Signature-256: sha256=<hex(hmac_sha256(secret, body))>.
    email_webhook_secret: SecretStr | None = None

    # Request / middleware
    request_timeout_seconds: int = 60
    request_id_header: str = "X-Request-ID"
    correlation_id_header: str = "X-Correlation-ID"

    # Verification: tenant-wide chain verification (fail-fast over limit; use background job for large tenants).
    verification_max_events: int = 100_000
    verification_timeout_seconds: int = 55

    # Firebase / Firestore: use key (env) or path (file). For Vercel, use key.
    firebase_service_account_key: SecretStr | None = None
    firebase_service_account_path: str | None = None  # Path to JSON file

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

    # OpenTelemetry
    telemetry_enabled: bool = True
    telemetry_exporter: str = "console"
    telemetry_otlp_endpoint: str | None = None
    telemetry_jaeger_endpoint: str | None = None
    telemetry_sample_rate: float = 1.0
    telemetry_environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_required_and_storage(self) -> "Settings":
        """Validate required env and storage backend.

        - Postgres: DATABASE_URL required.
        - Firestore: FIREBASE_SERVICE_ACCOUNT_KEY or FIREBASE_SERVICE_ACCOUNT_PATH required; Alembic not used.
        """
        if self.database_backend == "postgres":
            if not self.database_url:
                raise ValueError(
                    "DATABASE_URL is required when database_backend is 'postgres'. "
                    "Set in environment or .env file."
                )
        elif self.database_backend == "firestore":
            has_key = (
                self.firebase_service_account_key
                and self.firebase_service_account_key.get_secret_value()
            )
            if not has_key and not self.firebase_service_account_path:
                raise ValueError(
                    "When database_backend is 'firestore', set FIREBASE_SERVICE_ACCOUNT_KEY (full JSON string) "
                    "or FIREBASE_SERVICE_ACCOUNT_PATH (path to JSON file)."
                )
        else:
            raise ValueError(
                f"database_backend must be 'postgres' or 'firestore', got: {self.database_backend!r}"
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
