"""Application configuration (settings and environment).

Single source of truth for all configuration. Uses pydantic-settings
with .env support. Required fields (e.g. DATABASE_URL, SECRET_KEY) are
validated at load time.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and .env.

    All settings are optional with defaults except those validated in
    validate_required_and_storage (database_url, secret_key, encryption_salt,
    and storage backend when applicable).
    """

    # App
    app_name: str = "new-timeline"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database: "postgres" (SQLAlchemy + Alembic) or "firestore" (Firestore only)
    database_backend: str = "firestore"
    database_url: str = ""
    database_echo: bool = False

    # Security
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours
    encryption_salt: str = ""

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
    s3_secret_key: str | None = None
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    allowed_mime_types: str = "*/*"

    # Tenant
    tenant_header_name: str = "X-Tenant-ID"

    # Firebase / Firestore: use key (env) or path (file). For Vercel, use key.
    firebase_service_account_key: str | None = None  # Full JSON string (e.g. FIREBASE_SERVICE_ACCOUNT_KEY)
    firebase_service_account_path: str | None = None  # Path to JSON file

    # Redis Cache
    redis_enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_max_connections: int = 10
    cache_ttl_permissions: int = 300
    cache_ttl_schemas: int = 600
    cache_ttl_tenants: int = 900

    # OpenTelemetry
    telemetry_enabled: bool = True
    telemetry_exporter: str = "console"
    telemetry_otlp_endpoint: str | None = None
    telemetry_jaeger_endpoint: str | None = "localhost"
    telemetry_sample_rate: float = 1.0
    telemetry_environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_required_and_storage(self) -> "Settings":
        """Validate required env and storage backend.

        - Postgres: DATABASE_URL required.
        - Firestore: FIREBASE_SERVICE_ACCOUNT_PATH required; Alembic not used.
        """
        if self.database_backend == "postgres":
            if not self.database_url:
                raise ValueError(
                    "DATABASE_URL is required when database_backend is 'postgres'. "
                    "Set in environment or .env file."
                )
        elif self.database_backend == "firestore":
            if not self.firebase_service_account_key and not self.firebase_service_account_path:
                raise ValueError(
                    "When database_backend is 'firestore', set FIREBASE_SERVICE_ACCOUNT_KEY (full JSON string) "
                    "or FIREBASE_SERVICE_ACCOUNT_PATH (path to JSON file)."
                )
        else:
            raise ValueError(
                f"database_backend must be 'postgres' or 'firestore', got: {self.database_backend!r}"
            )
        if not self.secret_key:
            raise ValueError("SECRET_KEY is required. Generate with: openssl rand -hex 32")
        if not self.encryption_salt:
            raise ValueError("ENCRYPTION_SALT is required. Generate with: openssl rand -hex 16")
        if self.storage_backend == "s3":
            if not self.s3_bucket:
                raise ValueError(
                    "s3_bucket is required when storage_backend is 's3'. "
                    "Set S3_BUCKET environment variable or update .env file."
                )
        elif self.storage_backend not in ("local", "s3"):
            raise ValueError(
                f"Invalid storage_backend '{self.storage_backend}'. "
                "Must be one of: 'local', 's3'"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (single instance per process).

    Returns:
        Loaded and validated Settings instance.
    """
    return Settings()


# Module-level instance for convenience (uses same cache as get_settings).
settings = get_settings()
