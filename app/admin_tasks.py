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
#
# Every name here is verified to actually reach gtag. That is not a formality: the
# first version of this list named order_submit_form and checkout_pay, which exist
# nowhere in the codebase, and `purchase`, which was tracked SERVER-side only and so
# could never arrive in GA4 at all (fixed in V0.046 - templates/order_success.html).
# A name that never fires is worse than a missing one: GA4 shows the key event at a
# confident zero rather than as an error.
#
# Scroll depth is deliberately NOT here. scroll_50/75 are engagement, not conversions;
# marking them as key events makes every conversion report and campaign objective
# count a scroll as a sale. They are already visible in our own Analytics section.
_CORE_GOALS = [
    ("purchase", "Paid - the sale itself"),
    ("order_pay", "Order form submitted, heading to payment"),
    ("free_upload_submit", "Free wizard: drawing uploaded"),
    ("free_to_order", "Free reading -> paid order"),
    ("landing_hero_order", "/en/report hero CTA"),
    ("home_hero_cta", "Home page primary CTA"),
    ("sec_pricing", "Scrolled to the pricing block"),
]


def _ga4_details() -> str:
    lines = [
        "CLOSED 2026-08-18 by owner decision: not worth the effort. Kept as a record so",
        "nobody reopens it without knowing what was already established.",
        "",
        "WHAT IT WOULD HAVE BOUGHT. GA4 collects every one of these events on its own",
        "and reports them as events. Marking one as a KEY event only changes whether it",
        "also counts in the conversion column and can be used as a campaign objective -",
        "which matters when there are ad campaigns to optimise, and not before. Our own",
        "Analytics and Actions sections already show all of it either way, so nothing is",
        "unmeasured while this stays closed.",
        "",
        "IF IT EVER BECOMES WORTH DOING. GA4 -> Admin -> Data display -> Events -> Key",
        "events tab. Star an event that is already listed, or use New key event to",
        "register one by name before it has ever fired. Names go in EXACTLY as written,",
        "no spaces. Note purchase is normally a key event by default in a new property.",
        "",
    ]
    for n, (ident, label) in enumerate(_CORE_GOALS, start=1):
        lines.append(f"{n:>3}. {ident:<22} {label}")
    lines += [
        "",
        "THE PART THAT DID MATTER, AND IS DONE (V0.046). The old version of this list",
        "named order_submit_form and checkout_pay, which exist nowhere in the codebase,",
        "and purchase, which was tracked SERVER-side only - so GA4 could show sessions",
        "and zero revenue forever, with no way to tell which channel actually sells.",
        "templates/order_success.html now fires purchase with transaction_id, value and",
        "USD, gated on paid_at. That was a real defect and no amount of clicking in GA4",
        "would have fixed it. The seven names above are all verified to reach gtag.",
        "",
        "Scroll depth is deliberately absent: scroll_50/75 are engagement, not",
        "conversions, and marking them would make every conversion report count a",
        "scroll as a sale.",
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
     "Mark key events in GA4 - closed, not worth the effort",
     _ga4_details(), "done"),
    ("legal_review",
     "Have a lawyer review the privacy policy and terms",
     "The drafts cover children's data (COPPA), refunds and PayPal, and keep the\n"
     "'educational observation, not a diagnosis' framing that matters for FTC claims.\n"
     "They were written to be reviewed, not to be relied on. This is not legal advice."),
    ("legal_identity",
     "Put your legal name and address on the legal pages (server .env)",
     "The pages currently name 'DrawReport Team' - a TRADING name, not a legal\n"
     "person. It cannot sue or be sued, so the contract names no real counterparty.\n"
     "Anything still unset (address, state, venue) is OMITTED from the page rather\n"
     "than printed, so the pages LOOK complete either way and nothing on them shows\n"
     "the gap. app.legal.unfilled_placeholders() is the only thing that can tell.\n"
     "\n"
     "In the SERVER .env, then restart drawreport-web:\n"
     "  LEGAL_ENTITY_NAME=      your full legal name (or the LLC, if you form one)\n"
     "  LEGAL_ENTITY_ADDRESS=   a contactable business address\n"
     "  LEGAL_STATE=            governing law, e.g. Florida\n"
     "  LEGAL_VENUE=            where a dispute is heard, e.g. Miami-Dade County, Florida\n"
     "  LEGAL_CONTACT_EMAIL=    defaults to team@drawreport.com; must be MONITORED\n"
     "\n"
     "WORTH A CONVERSATION FIRST. Operating as an individual means your own name and a\n"
     "contactable address go on a public website, which for most people working from\n"
     "home means a home address. A single-member LLC, or a registered-agent / virtual\n"
     "business address, lets a business name appear instead and separates personal\n"
     "assets from business liability - which matters more than usual for a service that\n"
     "makes interpretive statements about children. Ask the attorney doing the review."),
    ("logo_art",
     "Drop the real logo artwork into data/Images/ and run build_logos.py",
     "Placeholders ship today. The hero image is already built from your artwork; only\n"
     "the wordmark is still a placeholder. venv\\Scripts\\python.exe scripts\\build_logos.py"),
    ("seo_analytics_connected",
     "Connect GA4, Search Console, Bing and IndexNow",
     "DONE 2026-08-18 (V0.043). Recorded here because all four live in someone else's\n"
     "interface, so nothing in the code proves they are still connected.\n"
     "\n"
     "GA4          G-FBQFBZNBRC, property 'DrawReport' (account Pasha_webAnalytics).\n"
     "             Confirmed emitting on / and /en/report, absent on /admin, and a\n"
     "             realtime hit was seen. Linked to Search Console, so organic query\n"
     "             data reaches GA4.\n"
     "SEARCH       Verified as a DNS DOMAIN property, which covers www/non-www,\n"
     "CONSOLE      http/https and every subdomain. This is why GOOGLE_SITE_VERIFICATION\n"
     "             is empty and should STAY empty. Sitemap accepted: 12 URLs.\n"
     "BING         Verified by META TAG (BING_SITE_VERIFICATION), deliberately NOT by\n"
     "             importing from Search Console: that import wants a Google OAuth\n"
     "             grant covering EVERY property on the account (cosmyday,\n"
     "             belgradebest, fidgetgo, shepotzvezd). The tag is scoped to this site\n"
     "             alone. Bing RE-CHECKS it - removing the tag un-verifies the site.\n"
     "INDEXNOW     Key file live at /<INDEXNOW_KEY>.txt, 12 URLs submitted.\n"
     "\n"
     "WARNING. All four values live in the SERVER .env only, never in git. Rebuild the\n"
     "box without them and measurement stops SILENTLY - every template renders nothing\n"
     "when its value is empty and nothing warns you. The values are written down in\n"
     "drawreportDeploy/README.md, and Site settings shows which are currently set.\n"
     "\n"
     "NOT done by this: marking key events in GA4 - that is its own task, and it only\n"
     "became possible now that the tag is finally on the page.",
     "done"),
    ("seo_ahrefs_awt",
     "Sign up for Ahrefs Webmaster Tools (free) and run the first site audit",
     "WHY. The best free tool after Search Console, and it covers the two things GSC\n"
     "does not: a crawl-based technical audit of every page, and our own backlink\n"
     "profile. We currently have no idea who links to us.\n"
     "\n"
     "HOW. ahrefs.com/webmaster-tools -> create the account (free, no card) -> add\n"
     "drawreport.com -> verify VIA GOOGLE SEARCH CONSOLE. That path is one click\n"
     "because the GSC domain property already exists; the alternative is another meta\n"
     "tag. Then run Site Audit and read the errors before the warnings.\n"
     "\n"
     "NOTE. Needs an account, so it cannot be done for you. Expect the audit to flag\n"
     "thin content on the legal pages - that is expected and not worth fixing."),
    ("seo_uptime_monitor",
     "Put drawreport.com on an uptime monitor (UptimeRobot free tier)",
     "WHY. release.bat health-checks ONCE, at deploy time, and nothing watches the site\n"
     "between deploys. Two separate costs: a paying customer hits a dead checkout, and\n"
     "a crawler that meets a 5xx reads it as a site-quality signal rather than as bad\n"
     "luck. There is also no alert if gunicorn dies without nginx dying with it.\n"
     "\n"
     "HOW. uptimerobot.com -> free tier -> HTTP(s) monitor on\n"
     "https://drawreport.com/en/ every 5 minutes, alert to ADMIN_ALERT_EMAIL.\n"
     "Monitor /en/ rather than / : / only proves nginx answered and redirected, while\n"
     "/en/ is rendered by the app, so a 200 there proves gunicorn is actually alive.\n"
     "\n"
     "NOTE. This watches the WEB unit only. drawreport-worker and drawreport-free can\n"
     "die without the site going down - that is what the service_heartbeat table and\n"
     "the Tasks/Analytics pages are for."),
]


def _seed(db) -> None:
    """Idempotent: a task with a given key is created once in the life of the database."""
    for seed in _SEEDS:
        # A 4th element is an optional starting status. It exists so a step that was
        # already finished can be RECORDED here instead of appearing as outstanding
        # work someone then has to tick off - the point of those rows is the detail
        # text, which is the only place the settings live outside another company's UI.
        key, title, details = seed[:3]
        status = seed[3] if len(seed) > 3 else "open"
        row = db.execute("SELECT id FROM admin_tasks WHERE key = ?", (key,)).fetchone()
        if row is None:
            db.execute(
                "INSERT INTO admin_tasks (key, title, details, status, created_at,"
                " done_at) VALUES (?, ?, ?, ?, ?, ?)",
                (key, title, details, status, now(),
                 now() if status == "done" else None))
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
