from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PARENT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Environment-backed settings for the live demo skeleton."""

    model_config = SettingsConfigDict(env_file=PARENT_ENV_FILE, extra="ignore")

    mistral_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("MISTRAL_API_KEY", "mistral_api_key"),
    )
    livedemo_db_url: str = Field(
        default="sqlite:////var/livedemo/db.sqlite",
        alias="LIVEDEMO_DB_URL",
    )
    livedemo_cors_origins: str = Field(
        default="http://localhost:5173",
        alias="LIVEDEMO_CORS_ORIGINS",
    )
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    frontend_port: int = Field(default=5173, alias="FRONTEND_PORT")

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.livedemo_cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
