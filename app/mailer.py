"""Email behind an abstraction: send_email() is the SINGLE send point.

Backend via settings.MAIL_BACKEND:
- 'outbox' - saved as an HTML file in data/outbox/ + an ASCII log line (dev);
- 'resend' - Resend HTTP API (https://api.resend.com/emails). From = MAIL_FROM_EMAIL.
  On a network/API failure the email is NOT lost: we fall back to outbox + log ERROR
  (the worker / auth flow never crashes).

Calling code (worker, auth, payments) is identical for both backends.
"""
from __future__ import annotations

import base64
import datetime
import json
import logging
import re
import urllib.error
import urllib.request
from html import escape, unescape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings

log = logging.getLogger("mailer")
_env = Environment(loader=FileSystemLoader(settings.BASE_DIR / "templates" / "email"),
                   autoescape=select_autoescape(["html"]))

_MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".html": "text/html", ".txt": "text/plain"}


class MailSendError(RuntimeError):
    """Transport error (Resend returned non-2xx / the network failed)."""


def render_email(template: str, locale: str = settings.DEFAULT_LOCALE, **ctx) -> str:
    """Render templates/email/<template> with the standard site context."""
    return _env.get_template(template).render(
        site_name=settings.SITE_NAME, base_url=settings.PUBLIC_BASE_URL,
        site_domain=settings.SITE_DOMAIN, locale=locale, **ctx)


def send_email(to: str, subject: str, html_body: str,
               attachments: list[Path] | None = None, kind: str = "mail") -> Path | None:
    """Send via the current backend. kind = slug for the file name / log.
    Returns the outbox file path (None on a successful Resend send)."""
    attachments = attachments or []
    if settings.MAIL_BACKEND == "resend":
        try:
            _resend_send(to, subject, html_body, attachments, kind)
            return None
        except Exception as e:  # network/API/timeout - don't lose the email
            log.error("EMAIL [%s] -> %s | Resend FAILED (%s) - fallback to outbox",
                      kind, to, e)
            return _outbox_write(to, subject, html_body, attachments, kind)
    return _outbox_write(to, subject, html_body, attachments, kind)


def _resend_send(to: str, subject: str, html_body: str,
                 attachments: list[Path], kind: str) -> None:
    """Transactional email via Resend. Raises MailSendError on a non-2xx response."""
    if not settings.RESEND_API_KEY:
        raise MailSendError("RESEND_API_KEY is empty")
    payload: dict = {
        "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>",
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": _html_to_text(html_body),
    }
    atts = []
    for p in attachments:
        p = Path(p)
        atts.append({"filename": p.name,
                     "content": base64.b64encode(p.read_bytes()).decode("ascii")})
    if atts:
        payload["attachments"] = atts

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        settings.RESEND_API_URL, data=data, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {settings.RESEND_API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=settings.RESEND_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as he:
        body = he.read().decode("utf-8", "replace")
        raise MailSendError(f"HTTP {he.code}: {body[:300]}")
    try:
        out = json.loads(raw)
    except ValueError:
        raise MailSendError(f"non-JSON response: {raw[:200]}")
    if out.get("id"):
        log.info("EMAIL [%s] -> %s | resend id=%s", kind, to, out["id"])
        return
    raise MailSendError(f"resend response: {raw[:300]}")


def _html_to_text(html: str) -> str:
    """Rough plaintext fallback from the HTML email (deliverability)."""
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|tr|h[1-6]|li|table)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", text)
    return text.strip()


def send_admin_alert(subject: str, body_text: str) -> Path | None:
    """Admin alert (worker errors, insufficient). Uses the same backend."""
    html = (f"<pre style='font: 13px/1.5 Consolas, monospace; white-space: pre-wrap'>"
            f"{escape(body_text)}</pre>")
    return send_email(settings.ADMIN_ALERT_EMAIL, f"[{settings.SITE_DOMAIN}] {subject}",
                      html, kind="alert")


def _outbox_write(to: str, subject: str, html_body: str,
                  attachments: list[Path], kind: str) -> Path:
    settings.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safe_kind = re.sub(r"[^a-z0-9_-]", "", kind.lower()) or "mail"
    path = settings.OUTBOX_DIR / f"{ts}_{safe_kind}.html"
    head = (f"<!--\nTo: {to}\nSubject: {subject}\n"
            + "".join(f"Attach: {a}\n" for a in attachments)
            + "-->\n")
    path.write_text(head + html_body, encoding="utf-8")
    log.info("EMAIL [%s] -> %s | %s", safe_kind, to, path.name)
    return path
