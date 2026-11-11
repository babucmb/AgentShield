from uuid import uuid4

import httpx

from .config import PAYPAL_BASE_URL, PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, FRONTEND_URL, env
from .schemas import Product


class PayPalNotConfigured(RuntimeError):
    pass


class PayPalClient:
    def __init__(self) -> None:
        if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
            raise PayPalNotConfigured("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are required")

    def _token(self) -> str:
        response = httpx.post(f"{PAYPAL_BASE_URL}/v1/oauth2/token", auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET), data={"grant_type": "client_credentials"}, headers={"Accept": "application/json"}, timeout=20)
        response.raise_for_status()
        return response.json()["access_token"]

    def create_order(self, product: Product, quantity: int, proposal_id: str) -> dict:
        token = self._token()
        amount = f"{product.price * quantity:.2f}"
        payload = {"intent": "CAPTURE", "purchase_units": [{"reference_id": proposal_id, "description": product.name, "amount": {"currency_code": product.currency, "value": amount}, "items": [{"name": product.name, "unit_amount": {"currency_code": product.currency, "value": f"{product.price:.2f}"}, "quantity": str(quantity), "category": "PHYSICAL_GOODS"}]}], "application_context": {"return_url": f"{FRONTEND_URL}/checkout/success", "cancel_url": f"{FRONTEND_URL}/checkout/cancel", "user_action": "PAY_NOW"}}
        response = httpx.post(f"{PAYPAL_BASE_URL}/v2/checkout/orders", json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "PayPal-Request-Id": str(uuid4())}, timeout=20)
        response.raise_for_status()
        return response.json()

    def capture_order(self, order_id: str) -> dict:
        token = self._token()
        response = httpx.post(f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture", json={}, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "PayPal-Request-Id": str(uuid4())}, timeout=20)
        response.raise_for_status()
        return response.json()

    def verify_webhook(self, headers: dict[str, str], event: dict) -> bool:
        webhook_id = env("PAYPAL_WEBHOOK_ID")
        if not webhook_id: raise PayPalNotConfigured("PAYPAL_WEBHOOK_ID is required for webhook verification")
        token = self._token()
        body = {"auth_algo": headers.get("paypal-auth-algo"), "cert_url": headers.get("paypal-cert-url"), "transmission_id": headers.get("paypal-transmission-id"), "transmission_sig": headers.get("paypal-transmission-sig"), "transmission_time": headers.get("paypal-transmission-time"), "webhook_id": webhook_id, "webhook_event": event}
        response = httpx.post(f"{PAYPAL_BASE_URL}/v1/notifications/verify-webhook-signature", json=body, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=20)
        response.raise_for_status()
        return response.json().get("verification_status") == "SUCCESS"
