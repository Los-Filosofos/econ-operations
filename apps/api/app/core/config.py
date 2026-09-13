from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ECON Integration API"
    database_url: str = Field(repr=False)
    # Session login is required by default; AUTH_REQUIRED=false is a local development mode.
    auth_required: bool = True
    session_secret: SecretStr | None = Field(default=None, repr=False)
    # Secure cookie by default; SESSION_HTTPS_ONLY=false only for local development over HTTP.
    session_https_only: bool = True
    session_max_age_seconds: int = Field(default=8 * 60 * 60, ge=60, le=30 * 24 * 60 * 60)
    allow_live_reads: bool = False
    allow_local_management: bool = False
    allow_live_writes: bool = False
    auto_queue_transfers: bool = False
    workflow_revalidation_batch_size: int = Field(default=25, ge=1, le=100)
    workflow_observation_batch_size: int = Field(default=25, ge=1, le=100)
    # Durable pause before a draft/blocked plan is revalidated again; sent/unknown movements
    # keep their next_review_at at the cycle time so that observation is never delayed.
    workflow_review_delay_seconds: int = Field(default=300, ge=0, le=3600)
    startrack_api_key: SecretStr | None = Field(default=None, repr=False)
    startrack_password: SecretStr | None = Field(default=None, repr=False)
    startrack_page_size: int = Field(default=25, ge=1, le=100)
    startrack_max_pages: int = Field(default=2, ge=1, le=10)
    startrack_timeout_seconds: float = Field(default=5, gt=0, le=30)
    startrack_budget_seconds: float = Field(default=20, gt=0, le=60)
    nexus_email: SecretStr | None = None
    nexus_password: SecretStr | None = None
    nexus_page_size: int = Field(default=25, ge=1, le=100)
    nexus_max_pages: int = Field(default=2, ge=1, le=5)
    nexus_timeout_seconds: float = Field(default=5, gt=0, le=15)
    nexus_budget_seconds: float = Field(default=20, gt=0, le=60)

    @model_validator(mode="after")
    def _session_secret_required(self) -> "Settings":
        if self.auth_required and not (
            self.session_secret and self.session_secret.get_secret_value()
        ):
            raise ValueError(
                "SESSION_SECRET es obligatorio cuando AUTH_REQUIRED=true; genera uno con "
                'python -c "import secrets; print(secrets.token_urlsafe(48))" o usa '
                "AUTH_REQUIRED=false solo para desarrollo local."
            )
        return self
