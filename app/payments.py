"""Payment behind an abstraction: stub now, PayPal (Phase 8) via the same interface.

  create_payment(order_id, price_cents) -> checkout URL (redirect target)
  mark_paid(order_id)                    -> the SINGLE "payment confirmed" point
                                            (stub button now, PayPal capture/webhook later).
                                            Idempotent: customer+child, session, status=paid.

Backend via settings.PAYMENT_BACKEND ('stub' | 'paypal'). PayPal lands in Phase 8 in
app/paypal.py and plugs in here; the rest of the app never changes.
"""
from __future__ import annotations

import json
import logging

from flask import url_for
from flask_babel import gettext as _

from app.db import get_db, now
from app.mailer import render_email, send_email
from config import settings

log = logging.getLogger("payments")


def create_payment(order_id: int, price_cents: int) -> str:
    """Return the checkout URL to redirect to. The stub renders our own page with a
    confirm button; PayPal (Phase 8) returns its hosted approval URL via the same
    contract."""
    if settings.PAYMENT_BACKEND == "paypal":
        from app.paypal import create_paypal_order
        return create_paypal_order(order_id, price_cents)
    return url_for("main.stub_checkout", order_id=order_id)


def mark_paid(order_id: int) -> dict | None:
    """Idempotently confirm payment. Returns {'customer_id','session_token','already_paid'}
    or None if the order isn't found. A duplicate call (e.g. webhook retry) is safe."""
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        return None
    if order["status"] != "created":            # already paid/processed - idempotent
        session = db.execute(
            "SELECT token FROM sessions WHERE customer_id = ? ORDER BY id DESC LIMIT 1",
            (order["customer_id"],)).fetchone()
        return {"customer_id": order["customer_id"],
                "session_token": session["token"] if session else None,
                "already_paid": True}

    email = order["email"].strip().lower()
    cust = db.execute("SELECT id FROM customers WHERE email = ?", (email,)).fetchone()
    if cust is None:
        cur = db.execute("INSERT INTO customers (email, created_at) VALUES (?, ?)",
                         (email, now()))
        customer_id = cur.lastrowid
    else:
        customer_id = cust["id"]

    # child: reuse by name for the same customer
    child = json.loads(order["child_json"] or "{}")
    child_id = None
    if child.get("name"):
        row = db.execute(
            "SELECT id FROM children WHERE customer_id = ? AND lower(name) = ?",
            (customer_id, child["name"].strip().lower())).fetchone()
        if row:
            child_id = row["id"]
        else:
            cur = db.execute(
                "INSERT INTO children (customer_id, name, gender, birth_ym, birth_info, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (customer_id, child["name"].strip(), child.get("gender"),
                 child.get("birth_ym"), json.dumps(child, ensure_ascii=False), now()))
            child_id = cur.lastrowid

    from app.auth import create_session
    token = create_session(db, customer_id)

    db.execute("UPDATE orders SET status = 'paid', customer_id = ?, child_id = ?, paid_at = ?"
               " WHERE id = ?", (customer_id, child_id, now(), order_id))
    if order["coupon_code"]:
        db.execute("UPDATE coupons SET uses_count = uses_count + 1 WHERE upper(code) = ?",
                   (order["coupon_code"],))
    db.commit()

    # Light "payment received" email (no attachment): sets the expectation and links to
    # the account. Sent only on the first transition to paid (dupes filtered above).
    # An email failure must not break payment confirmation.
    try:
        locale = order["locale"] or settings.DEFAULT_LOCALE
        html = render_email("payment_received.html", locale=locale,
                            login_url=f"{settings.PUBLIC_BASE_URL}/{locale}/login")
        send_email(email, f"{_('Payment received')} - {settings.SITE_NAME}", html,
                   kind="payment_received")
    except Exception:
        log.exception("payment_received email failed for order %s", order_id)

    return {"customer_id": customer_id, "session_token": token, "already_paid": False}
