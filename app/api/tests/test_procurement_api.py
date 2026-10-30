import importlib.util
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://sourcingiq:sourcingiq@127.0.0.1:55432/sourcingiq",
)

from app.main import app  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.environ.get("SOURCINGIQ_INTEGRATION") != "1",
    reason="Set SOURCINGIQ_INTEGRATION=1 when PostgreSQL is migrated and seeded.",
)

AUTH = {"Authorization": "Bearer local-demo"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _rfq_body() -> dict[str, object]:
    needed_by = (datetime.now(UTC).date() + timedelta(days=10)).isoformat()
    return {
        "material": "TMT steel",
        "specification": "Fe 500D",
        "quantity": "10",
        "unit": "tonne",
        "delivery_location": "Bengaluru, Karnataka",
        "needed_by": needed_by,
        "budget": {"amount": "650000.00", "currency": "INR"},
    }


def test_rfq_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/rfqs", json=_rfq_body())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def _seed() -> None:
    path = Path(__file__).resolve().parents[2] / "database" / "seed" / "seed.py"
    spec = importlib.util.spec_from_file_location("sourcingiq_seed", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed()


def test_catalogue_fixtures_match_expected_costs(client: TestClient) -> None:
    _seed()
    created = client.post("/api/v1/rfqs", json=_rfq_body(), headers=AUTH)
    assert created.status_code == 201, created.text
    rfq_id = created.json()["id"]
    offers = client.get(f"/api/v1/rfqs/{rfq_id}/offers", headers=AUTH)
    assert offers.status_code == 200, offers.text
    body = offers.json()
    assert body["data_mode"] == "synthetic_demo"
    assert body["calculation_version"] == "landed-cost-v1"
    by_name = {item["supplier_name"]: item for item in body["offers"]}
    assert by_name["Harbour Steel"]["eligible"] is True
    assert by_name["Harbour Steel"]["landed_cost"]["amount"] == "620000.00"
    assert "Lowest landed cost among eligible offers" in by_name["Harbour Steel"]["ranking_reasons"]
    assert by_name["Metro Metals"]["eligible"] is True
    assert by_name["Metro Metals"]["landed_cost"]["amount"] == "630000.00"
    assert by_name["Inland Mills"]["eligible"] is False
    assert "Fe 415" in by_name["Inland Mills"]["exclusion_reasons"][0]
    assert by_name["Short Stock Yard"]["eligible"] is False
    assert "available quantity" in by_name["Short Stock Yard"]["exclusion_reasons"][0]
    assert by_name["Distant Freight Co"]["eligible"] is False
    assert "deadline" in by_name["Distant Freight Co"]["exclusion_reasons"][0]
    assert by_name["Untaxed Traders"]["eligible"] is False
    assert by_name["Untaxed Traders"]["landed_cost"] is None
    eligible_names = [item["supplier_name"] for item in body["offers"] if item["eligible"]]
    assert eligible_names[0] == "Harbour Steel"
    assert "Inland Mills" not in eligible_names
    listed = client.get("/api/v1/rfqs", headers=AUTH)
    assert listed.status_code == 200
    assert any(item["id"] == rfq_id for item in listed.json()["items"])
    missing = client.get("/api/v1/rfqs/00000000-0000-4000-8000-000000009999", headers=AUTH)
    assert missing.status_code == 404


def test_idempotency_replays_and_conflicts(client: TestClient) -> None:
    _seed()
    headers = {**AUTH, "Idempotency-Key": "phase1-create-1"}
    first = client.post("/api/v1/rfqs", json=_rfq_body(), headers=headers)
    second = client.post("/api/v1/rfqs", json=_rfq_body(), headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    changed = dict(_rfq_body())
    changed["notes"] = "different"
    conflict = client.post("/api/v1/rfqs", json=changed, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CONFLICT"


def test_supplier_detail_is_marked_synthetic(client: TestClient) -> None:
    _seed()
    listing = client.get("/api/v1/suppliers", headers=AUTH, params={"material": "TMT steel"})
    assert listing.status_code == 200
    harbour = next(item for item in listing.json()["items"] if item["name"] == "Harbour Steel")
    assert harbour["data_source"] == "synthetic"
    assert harbour["verification_status"] == "demo_unverified"
    detail = client.get(f"/api/v1/suppliers/{harbour['id']}", headers=AUTH)
    assert detail.status_code == 200
    assert detail.json()["quotations"][0]["source_type"] == "synthetic_seed"
