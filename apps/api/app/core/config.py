from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ECON Integration API"
    database_url: str = Field(repr=False)
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    # There is no application login. Enabling live reads exposes them to API callers.
    allow_live_reads: bool = False
    allow_local_management: bool = False
    allow_live_writes: bool = False
    auto_queue_transfers: bool = False
    workflow_revalidation_batch_size: int = Field(default=25, ge=1, le=100)
    workflow_observation_batch_size: int = Field(default=25, ge=1, le=100)
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
