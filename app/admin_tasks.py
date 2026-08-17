"""The "Tasks" section: work that has to be done BY HAND and does not live in code.

Why a table rather than a file in the repo: part of the work happens in other people's
interfaces (create conversions in GA4, verify a sending domain, hand out access, paste
a live client id) - there is nowhere in the code to put such a task, and it disappears
from a chat log.

Seeded tasks (non-empty `key`) are NOT deleted, only closed: otherwise they would come
back on the next page load after deletion, and the delete button would look broken.
Tasks added by hand are deleted for real.
"""
from __future__ import annotations

from app.db import now

# The events that matter most as GA4 conversions. Ours are recorded regardless - this
# list only exists because GA4 counts a conversion only for an event marked as one.
_CORE_GOALS = [
    ("order_submit_form", "Order form submitted"),
    ("purchase", "Paid"),
    ("landing_hero_order", "Hero CTA clicked"),
    ("checkout_pay", "Reached checkout"),
    ("sec_pricing", "Scrolled to the pricing"),
    ("scroll_50", "Scrolled half the page"),
    ("scroll_75", "Scrolled three quarters"),
]


def _ga4_details() -> str:
    lines = [
        "WHY. GA4 reports a conversion only for an event you have marked as a key",
        "event. Dozens of goals fire on the site, but until the event is marked, it",
        "shows up as a plain event and cannot be used as a campaign objective.",
        "Our own analytics does not depend on this: Analytics and Actions already",
        "show all of it.",
        "",
        "HOW. GA4 -> Admin -> Events -> mark as key event. The identifier is the left",
        "column, entered EXACTLY as written, no spaces.",
        "",
    ]
    for n, (ident, label) in enumerate(_CORE_GOALS, start=1):
        lines.append(f"{n:>3}. {ident:<22} {label}")
    lines += [
        "",
        "NOTE. GA_MEASUREMENT_ID must be set in the server .env first, otherwise the",
        "tag is not on the page at all and nothing reaches GA4.",
    ]
    return "\n".join(lines)


_SEEDS = [
    ("env_prod",
     "Fill in the production .env (PUBLIC_BASE_URL, ADMIN_PASS)",
     "PUBLIC_BASE_URL=https://drawreport.com so links in emails and the sitemap are\n"
     "absolute and correct. ADMIN_PASS must be a strong value: the admin cookie is an\n"
     "HMAC of it, so changing it logs every admin session out (which is the point).\n"
     "An empty ADMIN_PASS disables /admin entirely (404)."),
    ("resend_live",
     "Switch email to Resend (RESEND_API_KEY + MAIL_BACKEND=resend)",
     "The domain is already verified in DNS: resend._domainkey, the send subdomain SPF\n"
     "and its SES feedback MX are all live. What is left is the API key in the server\n"
     ".env and MAIL_BACKEND=resend. Until then MAIL_BACKEND stays 'outbox' and every\n"
     "message is written to data/outbox/ as an HTML file instead of being sent -\n"
     "visible in the Emails section."),
    ("paypal_live",
     "Switch payment to PayPal (PAYPAL_* + PAYMENT_BACKEND=paypal)",
     "Needs the live client id and secret from the PayPal Business account, plus the\n"
     "webhook id. Until PAYMENT_BACKEND=paypal the stub provider marks orders paid\n"
     "without taking money - fine for testing the pipeline, fatal if left on in\n"
     "production. Verify with one small real purchase after switching."),
    ("ga4_key_events",
     "Mark 7 key events in GA4 (~10 minutes, by hand)",
     _ga4_details()),
    ("legal_review",
     "Have a lawyer review the privacy policy and terms",
     "The drafts cover children's data (COPPA), refunds and PayPal, and keep the\n"
     "'educational observation, not a diagnosis' framing that matters for FTC claims.\n"
     "They were written to be reviewed, not to be relied on. This is not legal advice."),
    ("logo_art",
     "Drop the real logo artwork into data/Images/ and run build_logos.py",
     "Placeholders ship today. The hero image is already built from your artwork; only\n"
     "the wordmark is still a placeholder. venv\\Scripts\\python.exe scripts\\build_logos.py"),
]


def _seed(db) -> None:
    """Idempotent: a task with a given key is created once in the life of the database."""
    for key, title, details in _SEEDS:
        row = db.execute("SELECT id FROM admin_tasks WHERE key = ?", (key,)).fetchone()
        if row is None:
            db.execute(
                "INSERT INTO admin_tasks (key, title, details, status, created_at)"
                " VALUES (?, ?, ?, 'open', ?)", (key, title, details, now()))
    db.commit()


def load(db) -> dict:
    """Open on top, closed at the bottom - closed ones are not deleted: they show what
    has already been done, and things like access and key events come back around."""
    _seed(db)
    rows = db.execute(
        "SELECT * FROM admin_tasks ORDER BY status = 'done', id DESC").fetchall()
    items = [{
        "id": r["id"], "key": r["key"], "title": r["title"],
        "details": r["details"] or "",
        "done": r["status"] == "done",
        "created": (r["created_at"] or "")[:10],
        "done_at": (r["done_at"] or "")[:10],
        "seeded": bool(r["key"]),
    } for r in rows]
    return {"tasks": items,
            "open_n": sum(1 for i in items if not i["done"]),
            "done_n": sum(1 for i in items if i["done"])}


def add(db, title: str, details: str) -> None:
    db.execute("INSERT INTO admin_tasks (title, details, status, created_at)"
               " VALUES (?, ?, 'open', ?)", (title[:200], details[:8000], now()))
    db.commit()


def toggle(db, task_id: int) -> None:
    row = db.execute("SELECT status FROM admin_tasks WHERE id = ?",
                     (task_id,)).fetchone()
    if row is None:
        return
    if row["status"] == "done":
        db.execute("UPDATE admin_tasks SET status = 'open', done_at = NULL"
                   " WHERE id = ?", (task_id,))
    else:
        db.execute("UPDATE admin_tasks SET status = 'done', done_at = ?"
                   " WHERE id = ?", (now(), task_id))
    db.commit()


def delete(db, task_id: int) -> bool:
    """A seeded task cannot be deleted - it would come back on the next page load and
    the button would look broken. Those can only be closed."""
    row = db.execute("SELECT key FROM admin_tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None or row["key"]:
        return False
    db.execute("DELETE FROM admin_tasks WHERE id = ?", (task_id,))
    db.commit()
    return True
