"""PayPal Business provider (Orders API v2) behind the payment abstraction.

Flow:
  create_paypal_order(order_id, price_cents) -> approval URL (user is redirected there)
  -> PayPal redirects back to /pay/paypal/return -> we CAPTURE -> payments.mark_paid
  -> webhook (/pay/paypal/webhook) also confirms via mark_paid (idempotent).

Selected when settings.PAYMENT_BACKEND == 'paypal'. With no creds the app stays on the
stub backend, so this module is only exercised once the owner sets PAYPAL_* in .env
(sandbox first). Uses `requests`; no extra deps.
"""
from __future__ import annotations

import logging

import requests
from flask import url_for

from config import settings

log = logging.getLogger("paypal")

_API = {"sandbox": "https://api-m.sandbox.paypal.com",
        "live": "https://api-m.paypal.com"}


def _base() -> str:
    return _API.get(settings.PAYPAL_ENV, _API["sandbox"])


def _access_token() -> str:
    r = requests.post(
        f"{_base()}/v1/oauth2/token",
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def create_paypal_order(order_id: int, price_cents: int) -> str:
    """Create a PayPal order, store its id on our order, return the approval URL."""
    from app.db import get_db
    amount = f"{price_cents / 100:.2f}"
    return_url = url_for("main.paypal_return", order_id=order_id, _external=True)
    cancel_url = url_for("main.paypal_cancel", order_id=order_id, _external=True)
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "custom_id": str(order_id),
            "amount": {"currency_code": settings.CURRENCY, "value": amount},
            "description": f"{settings.SITE_NAME} report #{order_id}",
        }],
        "application_context": {
            "brand_name": settings.SITE_NAME, "user_action": "PAY_NOW",
            "return_url": return_url, "cancel_url": cancel_url,
        },
    }
    r = requests.post(f"{_base()}/v2/checkout/orders",
                      json=payload,
                      headers={"Authorization": f"Bearer {_access_token()}",
                               "Content-Type": "application/json"}, timeout=20)
    r.raise_for_status()
    data = r.json()
    get_db().execute("UPDATE orders SET payment_id = ? WHERE id = ?",
                     (data["id"], order_id))
    get_db().commit()
    for link in data.get("links", []):
        if link.get("rel") == "approve":
            return link["href"]
    raise RuntimeError(f"PayPal order {data.get('id')} has no approval link")


def capture_order(paypal_order_id: str) -> bool:
    """Capture an approved PayPal order. True if completed."""
    r = requests.post(
        f"{_base()}/v2/checkout/orders/{paypal_order_id}/capture",
        headers={"Authorization": f"Bearer {_access_token()}",
                 "Content-Type": "application/json"}, timeout=30)
    if r.status_code not in (200, 201):
        log.error("PayPal capture %s failed: %s %s", paypal_order_id, r.status_code, r.text[:300])
        return False
    return r.json().get("status") == "COMPLETED"


def verify_webhook(headers, body: bytes) -> bool:
    """Verify a webhook signature with PayPal. Requires PAYPAL_WEBHOOK_ID."""
    if not settings.PAYPAL_WEBHOOK_ID:
        log.warning("PAYPAL_WEBHOOK_ID not set - cannot verify webhook")
        return False
    import json
    payload = {
        "auth_algo": headers.get("Paypal-Auth-Algo"),
        "cert_url": headers.get("Paypal-Cert-Url"),
        "transmission_id": headers.get("Paypal-Transmission-Id"),
        "transmission_sig": headers.get("Paypal-Transmission-Sig"),
        "transmission_time": headers.get("Paypal-Transmission-Time"),
        "webhook_id": settings.PAYPAL_WEBHOOK_ID,
        "webhook_event": json.loads(body.decode("utf-8")),
    }
    try:
        r = requests.post(
            f"{_base()}/v1/notifications/verify-webhook-signature",
            json=payload,
            headers={"Authorization": f"Bearer {_access_token()}",
                     "Content-Type": "application/json"}, timeout=20)
        r.raise_for_status()
        return r.json().get("verification_status") == "SUCCESS"
    except Exception:
        log.exception("PayPal webhook verification error")
        return False
