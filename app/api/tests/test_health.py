import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://sourcingiq:sourcingiq@127.0.0.1:55432/sourcingiq",
)

from app.main import app  # noqa: E402
from app.services.health import Readiness  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_live_has_no_dependency_details(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "database" not in response.text.lower()
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_ready_reports_database_outage(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.health.check_readiness",
        lambda _engine: Readiness(database="unavailable", schema="unknown", data_mode=None),
    )
    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["database"] == "unavailable"
    assert "password" not in response.text.lower()
    assert "sourcingiq:" not in response.text


def test_ready_when_dependencies_are_up(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.api.health.check_readiness",
        lambda _engine: Readiness(database="ok", schema="ok", data_mode="synthetic_demo"),
    )
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["data_mode"] == "synthetic_demo"


def test_unknown_route_uses_safe_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["request_id"]
    assert "traceback" not in response.text.lower()
