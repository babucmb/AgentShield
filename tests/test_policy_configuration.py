from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app, policies
from backend.app.persistence import save_policy
from backend.app.schemas import Policy


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_demo_policy():
    default = Policy()
    policies["demo"] = default
    save_policy("demo", default.model_dump(mode="json"))
    yield
    policies["demo"] = default
    save_policy("demo", default.model_dump(mode="json"))


def authenticated_headers():
    email = f"policy-{uuid4().hex}@example.test"
    registered = client.post("/api/auth/register", json={"email": email, "password": "strong-demo-password", "organization_name": "Policy Test"})
    return {"Authorization": f"Bearer {registered.json()['access_token']}"}


def set_policy(headers, **overrides):
    policy = {"max_transaction_amount": 3000, "daily_spending_limit": 10000, "monthly_spending_limit": 50000, "allowed_merchants": [], "blocked_merchants": [], "allowed_currencies": ["INR"], "restricted_categories": [], "max_quantity": 5, "requires_human_approval": True, "active": True}
    policy.update(overrides)
    response = client.put("/api/policy", headers=headers, json=policy)
    assert response.status_code == 200


def evaluate(instruction="Find a Bluetooth keyboard under ₹3,000. Ask me first.", product="keyboard-001", quantity=1):
    proposal = client.post("/api/proposals", json={"instruction": instruction, "product_id": product, "quantity": quantity}).json()
    return client.post(f"/api/proposals/{proposal['id']}/evaluate").json()


def test_policy_limits_and_restrictions():
    headers = authenticated_headers()
    set_policy(headers, max_transaction_amount=2000)
    assert evaluate()["decision"] == "BLOCK"
    set_policy(headers, max_transaction_amount=3000, max_quantity=1)
    assert evaluate(quantity=2)["decision"] == "BLOCK"
    set_policy(headers, allowed_merchants=["Only Trusted Store"])
    assert evaluate()["decision"] == "BLOCK"
    set_policy(headers, allowed_currencies=["USD"])
    assert evaluate()["decision"] == "BLOCK"
    set_policy(headers, restricted_categories=["keyboard"])
    assert evaluate()["decision"] == "BLOCK"


def test_policy_activation_and_approval_requirement():
    headers = authenticated_headers()
    set_policy(headers, active=False)
    assert evaluate()["decision"] == "BLOCK"
    set_policy(headers, active=True, requires_human_approval=True)
    assert evaluate()["decision"] == "REQUIRE_APPROVAL"


def test_daily_and_monthly_limits_fail_closed():
    headers = authenticated_headers()
    set_policy(headers, daily_spending_limit=1, monthly_spending_limit=1)
    result = evaluate()
    assert result["decision"] == "BLOCK"
    assert any(rule["name"] == "daily_limit" and not rule["passed"] for rule in result["rules"])
    assert any(rule["name"] == "monthly_limit" and not rule["passed"] for rule in result["rules"])
