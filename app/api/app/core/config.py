from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env",),
        extra="ignore",
    )

    database_url: str
    app_env: str = "local"
    log_level: str = "INFO"
    demo_mode: bool = True
    demo_auth_token: str = "local-demo"
    demo_approver_token: str = "local-approver"
    enable_negotiation_simulator: bool = True
    enable_rag: bool = True
    web_origin: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
