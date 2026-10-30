import os

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_settings_require_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_url_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://sourcingiq:sourcingiq@127.0.0.1:55432/sourcingiq",
    )
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.demo_mode is True


def test_env_example_has_no_live_key() -> None:
    example = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env.example"))
    text = open(example, encoding="utf-8").read()
    assert "LLM_API_KEY=" in text
    assert "sk-" not in text
