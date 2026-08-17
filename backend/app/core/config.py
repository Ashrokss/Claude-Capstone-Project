"""
Configuration settings for VeriClaim AI MVP backend.

This module loads environment variables and provides configuration
across the application with type safety using Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application metadata
    app_name: str = "VeriClaim AI MVP"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # AI providers. Endpoints and model names are configuration, never
    # hardcoded, so a model can be swapped without a code change.
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    # llama-3.3-70b is listed by /models but never returns on this account;
    # 3.1-70b answers in ~9s at the same quality tier.
    nvidia_model: str = "meta/llama-3.1-70b-instruct"

    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    # Alias rather than a pinned version: Google closes specific versions
    # ("no longer available to new users") while the alias keeps resolving.
    gemini_model: str = "gemini-flash-latest"

    # Supabase Storage
    storage_bucket: str = "claim-evidence"
    signed_url_ttl_seconds: int = 3600

    # Supabase Configuration
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""
    # Symmetric secret Supabase signs project JWTs with (Project Settings -> API).
    # Backend-only; never expose it to the frontend.
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"
    database_url: str = ""

    # Application Features
    demo_mode: bool = True

    # Logging
    log_level: str = "INFO"
    # Deliberately independent of `debug`. SQLAlchemy's echo logs every
    # statement together with its bound parameters, which for this schema means
    # claimant names, emails and phone numbers written to the log file. Turning
    # on debug logging should not imply that.
    sql_echo: bool = False

    # CORS
    frontend_url: str = "http://localhost:3000"
    # Additional browser origins, comma-separated. `frontend_url` is always
    # included, so this only needs preview or staging domains.
    extra_cors_origins: str = ""

    # JWT Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # File Storage Configuration
    max_image_size_mb: int = 5
    max_document_size_mb: int = 10
    allowed_image_formats: str = "jpg,jpeg,png"
    allowed_document_formats: str = "pdf,jpg,jpeg,png"

    # AI Processing Configuration.
    # 70B-class models routinely take 30-50s for a long structured reply, so a
    # 30s ceiling times out on healthy calls.
    ai_request_timeout_seconds: int = 90
    ai_max_retries: int = 3
    # A full run makes six or more provider calls, and one NVIDIA call that
    # stalls burns its whole 90s timeout before being retried. An observed run
    # with a policy document to read took 304s, which the previous 300s ceiling
    # would have killed a few seconds from completion. Analysis is asynchronous
    # and polled, so a generous ceiling costs nothing; hitting it means the run
    # is genuinely stuck.
    ai_job_timeout_seconds: int = 900

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_image_formats_list(self) -> list[str]:
        """Get allowed image formats as a list."""
        return [fmt.strip() for fmt in self.allowed_image_formats.split(",")]

    @property
    def allowed_document_formats_list(self) -> list[str]:
        """Get allowed document formats as a list."""
        return [fmt.strip() for fmt in self.allowed_document_formats.split(",")]

    @property
    def cors_origins(self) -> list[str]:
        """
        Browser origins permitted to call the API.

        Returned as an explicit list rather than a wildcard: the API is called
        with credentials, and browsers reject `Access-Control-Allow-Origin: *`
        on credentialed requests.
        """
        origins = [self.frontend_url.strip()]
        origins += [o.strip() for o in self.extra_cors_origins.split(",")]
        # Preserve order, drop blanks and duplicates.
        return list(dict.fromkeys(o for o in origins if o))


# Global settings instance
settings = Settings()
