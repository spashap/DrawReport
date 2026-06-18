"""Email-code login (Golos spec §9): 6-digit code, 30-min TTL, one-time;
30-day session (httpOnly cookie dr_s). Delivery via app.mailer (outbox in dev,
Resend in prod). Rate limit + max attempts as in Golos.
"""
from __future__ import annotations

import datetime
import logging
import secrets
import sqlite3

from flask import g, request
from flask_babel import gettext as _

from app.db import get_db, new_token, now
from app.mailer import render_email, send_email
from config import settings

log = logging.getLogger("auth")

SESSION_COOKIE = "dr_s"


class AuthError(Exception):
    """Message is safe to show to the user."""


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat(timespec="seconds")


def request_code(email: str, locale: str = settings.DEFAULT_LOCALE) -> None:
    """Create and "send" a login code. Raises AuthError on rate limit."""
    db = get_db()
    live = db.execute(
        "SELECT requested_at FROM login_codes WHERE email = ? AND used = 0"
        " AND attempts < ? AND expires_at > ? ORDER BY id DESC LIMIT 1",
        (email, settings.LOGIN_CODE_MAX_ATTEMPTS, _iso(_utcnow()))).fetchone()
    if live:
        resend_after = (datetime.datetime.fromisoformat(live["requested_at"])
                        + datetime.timedelta(minutes=settings.LOGIN_CODE_RESEND_MINUTES))
        if _utcnow() < resend_after:
            raise AuthError(_("A code was already sent - check your email (and spam). "
                              "You can request a new one in %(m)s minutes.",
                              m=settings.LOGIN_CODE_RESEND_MINUTES))

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = _iso(_utcnow() + datetime.timedelta(minutes=settings.LOGIN_CODE_TTL_MINUTES))
    db.execute("INSERT INTO login_codes (email, code, expires_at, requested_at)"
               " VALUES (?, ?, ?, ?)", (email, code, expires, now()))
    db.commit()

    html = render_email("login_code.html", locale=locale, code=code,
                        ttl_minutes=settings.LOGIN_CODE_TTL_MINUTES)
    send_email(email, f"{_('Your login code')} - {settings.SITE_NAME}", html, kind="login_code")
    # before Resend is wired, the code is read from the console/log (ASCII)
    log.info("LOGIN CODE for %s: %s", email, code)


def verify_code(email: str, code: str) -> str:
    """Verify the code. Returns a session token. Raises AuthError otherwise."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM login_codes WHERE email = ? AND used = 0"
        " ORDER BY id DESC LIMIT 1", (email,)).fetchone()
    if row is None:
        raise AuthError(_("No code found - request a new one."))
    if row["attempts"] >= settings.LOGIN_CODE_MAX_ATTEMPTS:
        raise AuthError(_("Too many attempts - request a new code."))
    if _iso(_utcnow()) > row["expires_at"]:
        raise AuthError(_("The code has expired - request a new one."))
    if code.strip() != row["code"]:
        db.execute("UPDATE login_codes SET attempts = attempts + 1 WHERE id = ?",
                   (row["id"],))
        db.commit()
        left = settings.LOGIN_CODE_MAX_ATTEMPTS - row["attempts"] - 1
        if left <= 0:
            raise AuthError(_("Too many attempts - request a new code."))
        raise AuthError(_("Wrong code. Attempts left: %(n)s.", n=left))

    db.execute("UPDATE login_codes SET used = 1 WHERE id = ?", (row["id"],))
    cust = db.execute("SELECT id FROM customers WHERE email = ?", (email,)).fetchone()
    if cust is None:
        cur = db.execute("INSERT INTO customers (email, created_at) VALUES (?, ?)",
                         (email, now()))
        customer_id = cur.lastrowid
    else:
        customer_id = cust["id"]
    token = create_session(db, customer_id)
    db.commit()
    return token


def create_session(db: sqlite3.Connection, customer_id: int) -> str:
    """30-day session. Used here and in payments.mark_paid (auto-login on purchase).
    No commit - the caller commits its own transaction."""
    token = new_token()
    expires = _iso(_utcnow() + datetime.timedelta(days=settings.SESSION_DAYS))
    db.execute("INSERT INTO sessions (customer_id, token, expires_at, created_at)"
               " VALUES (?, ?, ?, ?)", (customer_id, token, expires, now()))
    return token


def current_customer():
    """The current request's customer (by cookie) or None. Cached on g."""
    if "auth_customer" not in g:
        g.auth_customer = None
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            g.auth_customer = get_db().execute(
                "SELECT c.* FROM sessions s JOIN customers c ON c.id = s.customer_id"
                " WHERE s.token = ? AND s.expires_at > ?",
                (token, _iso(_utcnow()))).fetchone()
    return g.auth_customer


def destroy_session() -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db = get_db()
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        db.commit()
