from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
AUTH = {"Authorization": "Bearer local-demo"}


def test_quantity_must_be_positive() -> None:
    response = client.post(
        "/api/v1/rfqs",
        headers=AUTH,
        json={
            "material": "TMT steel",
            "specification": "Fe 500D",
            "quantity": "0",
            "unit": "tonne",
            "delivery_location": "Bengaluru, Karnataka",
            "needed_by": "2026-12-01",
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["field"] == "quantity"
    assert "greater than zero" in body["error"]["details"][0]["issue"]


def test_unsupported_currency_is_rejected() -> None:
    response = client.post(
        "/api/v1/rfqs",
        headers=AUTH,
        json={
            "material": "TMT steel",
            "specification": "Fe 500D",
            "quantity": "10",
            "unit": "tonne",
            "delivery_location": "Bengaluru, Karnataka",
            "needed_by": "2026-12-01",
            "budget": {"amount": "10.00", "currency": "USD"},
        },
    )
    assert response.status_code == 422
    issues = response.json()["error"]["details"]
    assert any(item["field"] == "budget.currency" for item in issues)
