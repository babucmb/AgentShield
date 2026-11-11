from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def propose(instruction, product):
    response = client.post("/api/proposals", json={"instruction": instruction, "product_id": product})
    assert response.status_code == 200
    item = response.json()
    result = client.post(f"/api/proposals/{item['id']}/evaluate")
    assert result.status_code == 200
    return item, result.json()

def test_bluetooth_keyboard_requires_approval():
    _, result = propose("Find a Bluetooth keyboard under ₹3,000. Ask me before checkout.", "keyboard-001")
    assert result["decision"] == "REQUIRE_APPROVAL"

def test_wrong_feature_is_blocked():
    _, result = propose("Find a Bluetooth keyboard under ₹3,000.", "keyboard-002")
    assert result["decision"] == "BLOCK"

def test_over_budget_is_blocked():
    _, result = propose("Find a Bluetooth keyboard under ₹3,000.", "keyboard-003")
    assert result["decision"] == "BLOCK"

def test_approval_is_single_use():
    item, result = propose("Find a Bluetooth keyboard under ₹3,000. Ask me first.", "keyboard-001")
    approval = client.post(f"/api/proposals/{item['id']}/approval")
    assert approval.status_code == 200
    aid = approval.json()["id"]
    assert client.post(f"/api/approvals/{aid}", json={"approve": True}).status_code == 200
    assert client.post(f"/api/approvals/{aid}", json={"approve": True}).status_code == 409

def test_paypal_is_fail_closed_without_credentials():
    item, _ = propose("Find a Bluetooth keyboard under ₹3,000. Ask me first.", "keyboard-001")
    approval = client.post(f"/api/proposals/{item['id']}/approval").json()
    aid = approval["id"]
    client.post(f"/api/approvals/{aid}", json={"approve": True})
    assert client.post(f"/api/approvals/{aid}/paypal/order").status_code == 503
