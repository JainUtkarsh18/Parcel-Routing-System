from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_route_single_parcel():
    response = client.post(
        "/api/route",
        json={"weight": 0.8, "value": 100, "destination_country": "Germany"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["department"] == "Mail Department"


def test_batch_upload_routes_valid_records_and_reports_invalid_records():
    payload = b"""[cot
        {"weight": 0.8, "value": 100, "destination_country": "Germany"},
        {"weight": -1, "value": 100, "destination_country": "France"}
    ]"""
    response = client.post(
        "/api/route/batch",
        files={"file": ("parcels.json", payload, "application/json")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_records"] == 2
    assert body["successfully_routed"] == 1
    assert body["failed_validation"] == 1
