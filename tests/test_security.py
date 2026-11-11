from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_registration_login_and_api_key():
    email = f"judge-{uuid4().hex}@example.test"
    registered = client.post("/api/auth/register", json={"email": email, "password": "strong-demo-password", "organization_name": "Judge Workspace"})
    assert registered.status_code == 200
    token = registered.json()["access_token"]
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    key = client.post("/api/orgs/api-keys", headers={"Authorization": f"Bearer {token}"}, json={"label": "demo-agent"})
    assert key.status_code == 200
    assert key.json()["key"].startswith("ash_")
    assert client.get("/api/me", headers={"X-API-Key": key.json()["key"]}).status_code == 200


def test_idempotency_returns_same_proposal():
    idem = "test-" + uuid4().hex
    request = {"instruction": "Find a Bluetooth keyboard under ₹3,000", "product_id": "keyboard-001"}
    first = client.post("/api/proposals", headers={"Idempotency-Key": idem}, json=request)
    second = client.post("/api/proposals", headers={"Idempotency-Key": idem}, json=request)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
