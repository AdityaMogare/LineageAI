from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", validation_alias="LINEAGEAI_ENVIRONMENT")
    api_host: str = Field(default="127.0.0.1", validation_alias="LINEAGEAI_API_HOST")
    api_port: int = Field(default=8000, validation_alias="LINEAGEAI_API_PORT")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        validation_alias="LINEAGEAI_CORS_ORIGINS",
    )

    moonshot_api_key: str | None = Field(default=None, validation_alias="MOONSHOT_API_KEY")
    moonshot_base_url: str = Field(
        default="https://api.moonshot.ai/v1", validation_alias="MOONSHOT_BASE_URL"
    )
    moonshot_model: str = Field(default="kimi-k3", validation_alias="MOONSHOT_MODEL")

    datahub_gms_url: str = Field(
        default="http://localhost:8080", validation_alias="DATAHUB_GMS_URL"
    )
    datahub_token: str | None = Field(default=None, validation_alias="DATAHUB_TOKEN")
    datahub_platform: str = Field(default="duckdb", validation_alias="DATAHUB_PLATFORM")
    datahub_env: str = Field(default="DEV", validation_alias="DATAHUB_ENV")
    metadata_mode: str = Field(default="demo", validation_alias="LINEAGEAI_METADATA_MODE")
    datahub_datasets: list[str] = Field(
        default_factory=lambda: ["orders", "customers", "products", "order_items"],
        validation_alias="DATAHUB_DATASETS",
    )

    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")
    github_repository: str | None = Field(default=None, validation_alias="GITHUB_REPOSITORY")
    github_base_branch: str = Field(default="main", validation_alias="GITHUB_BASE_BRANCH")
    github_models_path: str = Field(
        default="models/generated", validation_alias="GITHUB_MODELS_PATH"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
