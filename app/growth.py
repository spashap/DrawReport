"""Growth Data API: /internal/growth/* - read-only, aggregated, for an external growth agent.

Three questions an outside strategist (a ChatGPT connector, in practice) is allowed to ask:
  1. What happened?                        GET /internal/growth/summary?from=&to=
  2. Which sources / content caused it?    GET /internal/growth/content?from=&to=&limit=
  3. What did WE change meanwhile?         GET /internal/growth/changes?since=

Rules that shape everything below:
  * ITS OWN TOKEN. `Authorization: Bearer <GROWTH_AGENT_TOKEN>`, compared in constant time.
    Never the admin password: that cookie belongs to a person at a screen, this belongs to a
    machine that must be revocable on its own. Empty token -> 503 on every route.
  * NO PII, EVER. Counts and money only. Nothing here reads emails, child names, tokens,
    file paths, model text or user agents, so nothing can leak them. Identifiers (visit /
    visitor / order ids) are used as join keys in Python and never emitted.
  * BOUNDED. Every query carries both ends of the date window; the window itself is capped
    (settings.GROWTH_MAX_RANGE_DAYS) so a token holder cannot make the box scan everything.
  * TWO ATTRIBUTION MODELS, NEVER MERGED. DrawReport stores the visit's own tags
    (last touch: web_visits.utm_json / gclid / referer / channel) AND the first-touch UTM
    cookie (events.utm_json, orders.utm_json). A number that quietly picked one would be
    wrong half the time, so both are returned side by side under their own names.
  * REUSE. The visit funnels come from app.admin_funnels.build() (now with an `until`), the
    free->paid pairing from app.admin_free_analytics._attribute_orders(); this module only
    adds the date window, the attribution folds and the envelope.
  * ERRORS ARE OPAQUE TO THE CALLER. A failure is logged with its traceback under the
    "growth" logger and answered with a generic 500 JSON body.
"""
from __future__ import annotations

import datetime
import hmac
import json
import logging

from flask import Blueprint, Response, jsonify, request

from app import admin_free_analytics as fa
from app import admin_funnels as fn
from app.db import get_db
from config import settings

log = logging.getLogger("growth")

bp_growth = Blueprint("growth", __name__, url_prefix="/internal/growth")

SCHEMA_VERSION = "1"
PROJECT = "drawreport"

CONTENT_LIMIT_DEFAULT = 50
CONTENT_LIMIT_MAX = 200
CHANGES_LIMIT_MAX = 500
ATTRIBUTION_ROWS_MAX = 50      # per breakdown table inside /summary

# web_visits.device is 'bot' for crawlers/scanners/utilities (app/track.py parse_device);
# NULL only on rows older than the column. Both count as "not a known bot".
VISIT_NOT_BOT = "COALESCE(device, '') <> 'bot'"
# The one metric a human reader should trust: a non-bot visit that scrolled, clicked or
# stayed 15 seconds (static/js/track.js -> web_visits.engaged).
VISIT_HUMAN = f"engaged = 1 AND {VISIT_NOT_BOT}"

PRIMARY_METRIC = "visits_engaged_human"
PRIMARY_METRIC_DEFINITION = ("web_visits rows with engaged = 1 AND device <> 'bot': a "
                             "non-bot visit that scrolled, clicked, or stayed 15 seconds")

# Money that is NOT stored anywhere in the system. Returned as null with a warning so the
# caller cannot mistake absence for zero.
_UNAVAILABLE_MONEY = {
    "ad_spend_usd": "ad spend is not stored anywhere in DrawReport",
    "refunds_usd": "refunds are not tracked (no refund webhook or column)",
    "net_revenue_usd": "net revenue needs PayPal fees and refunds, neither is stored",
    "paypal_fees_usd": "PayPal fees are not stored",
}


# --- errors ---------------------------------------------------------------------------

class ApiError(Exception):
    """A client-facing error: status + short machine code + one plain sentence."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _json(payload: dict, status: int = 200, headers: dict | None = None) -> Response:
    resp = jsonify(payload)
    resp.status_code = status
    resp.headers["Cache-Control"] = "no-store"
    for k, v in (headers or {}).items():
        resp.headers[k] = v
    return resp


def _error(status: int, code: str, message: str) -> Response:
    headers = {"WWW-Authenticate": 'Bearer realm="growth"'} if status == 401 else None
    return _json({"schema_version": SCHEMA_VERSION, "project": PROJECT,
                  "error": {"code": code, "message": message}}, status, headers)


@bp_growth.errorhandler(ApiError)
def _handle_api_error(e: ApiError):
    return _error(e.status, e.code, e.message)


@bp_growth.errorhandler(Exception)
def _handle_crash(e: Exception):
    # HTTPExceptions raised by Flask itself (404 inside the prefix, 405) keep their status;
    # everything else is our bug and must not reach the caller as a traceback.
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return _error(e.code or 500, "http_error", e.name)
    log.exception("growth api failure on %s %s", request.method, request.path)
    return _error(500, "internal_error", "internal error (logged)")


# --- auth -----------------------------------------------------------------------------

def _authorize() -> None:
    token = settings.GROWTH_AGENT_TOKEN
    if not token:
        raise ApiError(503, "not_configured",
                       "the growth API is disabled: GROWTH_AGENT_TOKEN is not set")
    scheme, _, value = request.headers.get("Authorization", "").partition(" ")
    value = value.strip()
    if scheme.lower() != "bearer" or not value or not hmac.compare_digest(value, token):
        raise ApiError(401, "unauthorized", "missing or invalid bearer token")


@bp_growth.before_request
def _before():
    _authorize()


# --- time -----------------------------------------------------------------------------

def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _now_iso() -> str:
    return _utcnow().isoformat(timespec="seconds")


def _parse_day(raw: str | None, name: str) -> datetime.date:
    if not raw or len(raw) != 10:
        raise ApiError(400, "bad_request", f"{name} is required in the form YYYY-MM-DD")
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        raise ApiError(400, "bad_request", f"{name} is not a valid date (YYYY-MM-DD)")


def _period_args() -> tuple[datetime.date, datetime.date, str, str]:
    """from/to (inclusive days, UTC) -> (d_from, d_to, since, until) where since/until are
    ISO timestamp bounds usable as `col >= since AND col < until`. The stored timestamps
    are 'YYYY-MM-DDTHH:MM:SS+00:00', so plain string comparison is exact."""
    d_from = _parse_day(request.args.get("from"), "from")
    d_to = _parse_day(request.args.get("to"), "to")
    if d_from > d_to:
        raise ApiError(400, "bad_request", "from must not be after to")
    days = (d_to - d_from).days + 1
    if days > settings.GROWTH_MAX_RANGE_DAYS:
        raise ApiError(400, "bad_request",
                       f"range too long: {days} days, maximum is "
                       f"{settings.GROWTH_MAX_RANGE_DAYS}")
    since = f"{d_from.isoformat()}T00:00:00"
    until = f"{(d_to + datetime.timedelta(days=1)).isoformat()}T00:00:00"
    return d_from, d_to, since, until


def _limit_arg(default: int, cap: int) -> int:
    raw = request.args.get("limit")
    if raw is None or raw == "":
        return default
    try:
        n = int(raw)
    except ValueError:
        raise ApiError(400, "bad_request", "limit must be an integer")
    if n < 1:
        raise ApiError(400, "bad_request", "limit must be at least 1")
    return min(n, cap)


def _envelope(period_from: str, period_to: str, data: dict, warnings: list[str],
              status: str | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "project": PROJECT,
        "generated_at": _now_iso(),
        "period": {"from": period_from, "to": period_to, "timezone": "UTC"},
        "data_quality": {"status": status or ("partial" if warnings else "ok"),
                         "warnings": warnings},
        "data": data,
    }


# --- small helpers ----------------------------------------------------------------------

def _usd(cents: int | None) -> float:
    return round((cents or 0) / 100, 2)


def _utm(j: str | None) -> dict | None:
    """Parsed UTM dict with only the five standard keys, or None."""
    if not j:
        return None
    try:
        u = json.loads(j)
    except ValueError:
        return None
    if not isinstance(u, dict):
        return None
    out = {k: (str(u[k])[:120] if u.get(k) is not None else None)
           for k in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")}
    return out if any(out.values()) else None


def _blank_bucket() -> dict:
    return {"visits": 0, "engaged_visits": 0, "_visitors": set(), "free_uploads": 0,
            "free_completions": 0, "orders_created": 0, "paid_orders": 0,
            "_revenue_cents": 0}


def _add(bucket: dict, fact: dict) -> None:
    bucket["visits"] += fact["visits"]
    bucket["engaged_visits"] += fact["engaged_visits"]
    bucket["_visitors"].update(fact["visitors"])
    for k in ("free_uploads", "free_completions", "orders_created", "paid_orders"):
        bucket[k] += fact[k]
    bucket["_revenue_cents"] += fact["revenue_cents"]


def _finish(bucket: dict) -> dict:
    out = {k: v for k, v in bucket.items() if not k.startswith("_")}
    out["visitors"] = len(bucket["_visitors"])
    out["gross_revenue_usd"] = _usd(bucket["_revenue_cents"])
    return out


def _fold(facts: list[dict], key_fn) -> dict:
    """Sum facts into buckets by key_fn(fact); a key of None is skipped."""
    out: dict = {}
    for f in facts:
        k = key_fn(f)
        if k is None:
            continue
        b = out.get(k)
        if b is None:
            b = out[k] = _blank_bucket()
        _add(b, f)
    return out


def _sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (-r["engaged_visits"], -r["paid_orders"],
                                       -r["orders_created"], -r["visits"]))


# --- attribution facts --------------------------------------------------------------------
# A "fact" is one attributable unit with its tags and its outcomes. Folding facts by any
# key gives a breakdown; the two collectors below differ only in what a unit IS.

def _last_touch_facts(db, since: str, until: str) -> tuple[list[dict], dict]:
    """One fact per NON-BOT VISIT started in the window, tagged with that visit's own
    UTM / channel (last touch). Outcomes are joined by visit_id. Free analyses and orders
    created in the window whose visit is outside it (or bot-flagged) are counted in the
    returned `unattributed` dict rather than guessed."""
    facts: dict[str, dict] = {}
    for r in db.execute(
            "SELECT visit_id, visitor_id, engaged, channel, utm_json FROM web_visits"
            f" WHERE started_at >= ? AND started_at < ? AND {VISIT_NOT_BOT}",
            (since, until)):
        facts[r["visit_id"]] = {
            "visits": 1, "engaged_visits": 1 if r["engaged"] else 0,
            "visitors": {r["visitor_id"]} if r["visitor_id"] else set(),
            "channel": r["channel"] or "direct", "utm": _utm(r["utm_json"]),
            "free_uploads": 0, "free_completions": 0, "orders_created": 0,
            "paid_orders": 0, "revenue_cents": 0,
        }
    unattributed = {"free_uploads": 0, "free_completions": 0, "orders_created": 0,
                    "paid_orders": 0}
    for r in db.execute(
            "SELECT visit_id, uploaded_at, status FROM free_analyses"
            " WHERE created_at >= ? AND created_at < ?", (since, until)):
        f = facts.get(r["visit_id"] or "")
        target = f if f is not None else unattributed
        if r["uploaded_at"]:
            target["free_uploads"] += 1
        if r["status"] == "done":
            target["free_completions"] += 1
    for r in db.execute(
            "SELECT visit_id, paid_at, price_cents FROM orders"
            " WHERE created_at >= ? AND created_at < ?", (since, until)):
        f = facts.get(r["visit_id"] or "")
        target = f if f is not None else unattributed
        target["orders_created"] += 1
        if r["paid_at"]:
            target["paid_orders"] += 1
            if f is not None:
                f["revenue_cents"] += r["price_cents"] or 0
    return list(facts.values()), unattributed


def _first_touch_facts(db, since: str, until: str) -> list[dict]:
    """One fact per VISITOR seen in the window, tagged with the first-touch UTM cookie as
    recorded on their events (events.utm_json) - NULL when they never arrived with a UTM,
    which is every organic, referral and direct first visit. Orders carry their own copy
    (orders.utm_json, written at order time) and are trusted over the visitor map."""
    facts: dict[str, dict] = {}

    def fact(visitor_id: str | None, utm: dict | None) -> dict:
        key = visitor_id or "-"
        f = facts.get(key)
        if f is None:
            f = facts[key] = {
                "visits": 0, "engaged_visits": 0, "_visit_ids": set(), "_engaged_ids": set(),
                "visitors": {visitor_id} if visitor_id else set(),
                "channel": None, "utm": utm,
                "free_uploads": 0, "free_completions": 0, "orders_created": 0,
                "paid_orders": 0, "revenue_cents": 0,
            }
        elif f["utm"] is None and utm:
            f["utm"] = utm
        return f

    # Visits and engagement, from the beacon events (they carry the first-touch UTM).
    for r in db.execute(
            "SELECT visitor_id, visit_id, type, utm_json FROM events"
            " WHERE created_at >= ? AND created_at < ? AND visitor_id IS NOT NULL"
            " AND visit_id IS NOT NULL AND (device IS NULL OR device <> 'bot')"
            " AND type IN ('engaged', 'home_view', 'landing_view', 'free_view',"
            " 'order_form_view', 'free_upload')", (since, until)):
        f = fact(r["visitor_id"], _utm(r["utm_json"]))
        f["_visit_ids"].add(r["visit_id"])
        if r["type"] == "engaged":
            f["_engaged_ids"].add(r["visit_id"])
        elif r["type"] == "free_upload":
            f["free_uploads"] += 1
    for r in db.execute(
            "SELECT visitor_id FROM free_analyses WHERE status = 'done'"
            " AND created_at >= ? AND created_at < ?", (since, until)):
        fact(r["visitor_id"], None)["free_completions"] += 1
    for r in db.execute(
            "SELECT visitor_id, utm_json, paid_at, price_cents FROM orders"
            " WHERE created_at >= ? AND created_at < ?", (since, until)):
        f = fact(r["visitor_id"], _utm(r["utm_json"]))
        f["orders_created"] += 1
        if r["paid_at"]:
            f["paid_orders"] += 1
            f["revenue_cents"] += r["price_cents"] or 0
    for f in facts.values():
        f["visits"] = len(f.pop("_visit_ids"))
        f["engaged_visits"] = len(f.pop("_engaged_ids"))
    return list(facts.values())


def _utm_key(utm: dict | None, level: str):
    """Grouping key for a fact at a given level; None = the fact has no tag at that level."""
    if not utm:
        return None
    if level == "content":
        if not utm.get("utm_content"):
            return None
        return (utm.get("utm_source"), utm.get("utm_medium"), utm.get("utm_campaign"),
                utm.get("utm_content"))
    if level == "campaign":
        if not utm.get("utm_campaign"):
            return None
        return (utm.get("utm_source"), utm.get("utm_medium"), utm.get("utm_campaign"), None)
    if level == "source":
        if not utm.get("utm_source"):
            return None
        return (utm.get("utm_source"), utm.get("utm_medium"), None, None)
    raise ValueError(level)


def _utm_rows(facts: list[dict], level: str) -> list[dict]:
    rows = []
    for (src, med, camp, content), b in _fold(facts, lambda f: _utm_key(f["utm"], level)).items():
        rows.append({"level": level, "content_id": content, "source": src, "medium": med,
                     "campaign": camp, **_finish(b)})
    return _sort_rows(rows)


def _channel_rows(facts: list[dict]) -> list[dict]:
    rows = [{"channel": ch, **_finish(b)}
            for ch, b in _fold(facts, lambda f: f["channel"]).items()]
    return _sort_rows(rows)


def _totals(facts: list[dict]) -> dict:
    b = _blank_bucket()
    for f in facts:
        _add(b, f)
    return _finish(b)


# --- /summary -----------------------------------------------------------------------------

def _traffic(db, since: str, until: str) -> dict:
    t = db.execute(
        "SELECT COUNT(*) raw,"
        f" SUM(CASE WHEN {VISIT_NOT_BOT} THEN 1 ELSE 0 END) non_bot,"
        f" SUM(CASE WHEN {VISIT_HUMAN} THEN 1 ELSE 0 END) engaged_human,"
        f" COUNT(DISTINCT CASE WHEN {VISIT_NOT_BOT} THEN visitor_id END) visitors_non_bot,"
        f" COUNT(DISTINCT CASE WHEN {VISIT_HUMAN} THEN visitor_id END) visitors_engaged,"
        f" SUM(CASE WHEN {VISIT_HUMAN} THEN pages ELSE 0 END) engaged_pages"
        " FROM web_visits WHERE started_at >= ? AND started_at < ?", (since, until)).fetchone()
    # New = the visitor's first visit ever; returning = an earlier visit exists.
    nr = db.execute(
        "SELECT SUM(CASE WHEN EXISTS (SELECT 1 FROM web_visits p WHERE p.visitor_id = v.visitor_id"
        " AND p.started_at < v.started_at) THEN 1 ELSE 0 END) n_returning,"
        " COUNT(*) total FROM web_visits v"
        f" WHERE v.started_at >= ? AND v.started_at < ? AND {VISIT_HUMAN}",
        (since, until)).fetchone()
    device = {r["d"]: r["c"] for r in db.execute(
        "SELECT COALESCE(device, 'unknown') d, COUNT(*) c FROM web_visits"
        f" WHERE started_at >= ? AND started_at < ? AND {VISIT_HUMAN} GROUP BY d",
        (since, until))}
    countries = [{"country": r["c"] or "unknown", "engaged_visits": r["n"]} for r in db.execute(
        "SELECT geo_country c, COUNT(*) n FROM web_visits"
        f" WHERE started_at >= ? AND started_at < ? AND {VISIT_HUMAN}"
        " GROUP BY geo_country ORDER BY n DESC LIMIT 10", (since, until))]
    engaged = t["engaged_human"] or 0
    returning = nr["n_returning"] or 0
    return {
        "primary_metric": PRIMARY_METRIC,
        "primary_metric_definition": PRIMARY_METRIC_DEFINITION,
        "visits_raw": t["raw"] or 0,
        "visits_non_bot": t["non_bot"] or 0,
        "visits_engaged_human": engaged,
        "visitors_unique_non_bot": t["visitors_non_bot"] or 0,
        "visitors_unique_engaged_human": t["visitors_engaged"] or 0,
        "engaged_human_new_vs_returning": {"new": engaged - returning, "returning": returning},
        "avg_pages_per_engaged_visit": (round((t["engaged_pages"] or 0) / engaged, 2)
                                        if engaged else None),
        "device_engaged_human": device,
        "countries_engaged_human": countries,
    }


def _free_block(db, since: str, until: str) -> dict:
    f = db.execute(
        "SELECT COUNT(*) questionnaires,"
        " SUM(CASE WHEN status = 'draft' AND email IS NOT NULL THEN 1 ELSE 0 END) email_only,"
        " SUM(CASE WHEN uploaded_at IS NOT NULL THEN 1 ELSE 0 END) uploads,"
        " SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) completions,"
        " SUM(CASE WHEN status = 'insufficient' THEN 1 ELSE 0 END) insufficient,"
        " SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) failed,"
        " SUM(CASE WHEN status IN ('queued', 'generating') THEN 1 ELSE 0 END) in_progress,"
        " AVG(CASE WHEN status = 'done' THEN elapsed_s END) avg_elapsed_s"
        " FROM free_analyses WHERE created_at >= ? AND created_at < ?",
        (since, until)).fetchone()
    failures = {r["k"]: r["n"] for r in db.execute(
        "SELECT COALESCE(reason_key, status) k, COUNT(*) n FROM free_analyses"
        " WHERE status IN ('insufficient', 'failed') AND created_at >= ? AND created_at < ?"
        " GROUP BY k ORDER BY n DESC", (since, until))}
    # Refused uploads never become a row; they exist only as free_upload_failed{reason}.
    refused: dict[str, int] = {}
    for r in db.execute(
            "SELECT payload_json p, COUNT(*) n FROM events WHERE type = 'free_upload_failed'"
            " AND created_at >= ? AND created_at < ? GROUP BY p", (since, until)):
        try:
            reason = (json.loads(r["p"] or "{}") or {}).get("reason") or "unknown"
        except ValueError:
            reason = "unknown"
        refused[str(reason)[:40]] = refused.get(str(reason)[:40], 0) + r["n"]
    starts = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events WHERE type = 'free_view'"
        " AND visitor_id IS NOT NULL AND (device IS NULL OR device <> 'bot')"
        " AND created_at >= ? AND created_at < ?", (since, until)).fetchone()["c"]
    to_paid_clicks = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events WHERE type = 'free_to_order'"
        " AND visitor_id IS NOT NULL AND created_at >= ? AND created_at < ?",
        (since, until)).fetchone()["c"]
    # Free -> paid pairing, the same attribution the admin Freemium page uses
    # (direct token > same email > same visitor). Only counts leave this function.
    rows = db.execute(
        "SELECT id, token, visitor_id, email, child_name, concern_key, created_at"
        " FROM free_analyses WHERE created_at >= ? AND created_at < ?",
        (since, until)).fetchall()
    _per, pairs = fa._attribute_orders(db, rows)
    transitions = {k: {"orders": 0, "paid_orders": 0, "gross_revenue_usd": 0.0}
                   for k in ("direct", "same_email", "same_visitor")}
    kind_name = {"direct": "direct", "email": "same_email", "visitor": "same_visitor"}
    for p in pairs:
        t = transitions[kind_name[p["kind"]]]
        t["orders"] += 1
        if p["paid"]:
            t["paid_orders"] += 1
            t["gross_revenue_usd"] = round(t["gross_revenue_usd"] + p["usd"], 2)
    return {
        "wizard_openers_visitors": starts,
        "questionnaires_completed": f["questionnaires"] or 0,
        "email_only_no_drawing": f["email_only"] or 0,
        "uploads": f["uploads"] or 0,
        "completions": f["completions"] or 0,
        "insufficient": f["insufficient"] or 0,
        "failed": f["failed"] or 0,
        "in_progress": f["in_progress"] or 0,
        "avg_completion_seconds": (round(f["avg_elapsed_s"], 1)
                                   if f["avg_elapsed_s"] is not None else None),
        "failures_by_reason": failures,
        "uploads_refused_by_reason": refused,
        "to_paid_click_visitors": to_paid_clicks,
        "to_paid_transitions": transitions,
        "to_paid_transitions_note": ("cohort by questionnaire date; purchases counted with no "
                                     "date limit; 'direct' is exact (orders.free_token), the "
                                     "other two are matches by coincidence"),
    }


def _orders_block(db, since: str, until: str) -> tuple[dict, dict]:
    created = db.execute(
        "SELECT COUNT(*) n, SUM(CASE WHEN paid_at IS NOT NULL THEN 1 ELSE 0 END) paid,"
        " SUM(CASE WHEN status = 'created' THEN 1 ELSE 0 END) unpaid"
        " FROM orders WHERE created_at >= ? AND created_at < ?", (since, until)).fetchone()
    paid = db.execute(
        "SELECT COUNT(*) n, COALESCE(SUM(price_cents), 0) cents,"
        " SUM(CASE WHEN coupon_code IS NOT NULL THEN 1 ELSE 0 END) coupons,"
        " SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) delivered,"
        " SUM(CASE WHEN status = 'insufficient' THEN 1 ELSE 0 END) insufficient,"
        " SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) failed"
        " FROM orders WHERE paid_at >= ? AND paid_at < ?", (since, until)).fetchone()
    products = {r["p"]: {"paid_orders": r["n"], "gross_revenue_usd": _usd(r["c"])}
                for r in db.execute(
                    "SELECT product_code p, COUNT(*) n, SUM(price_cents) c FROM orders"
                    " WHERE paid_at >= ? AND paid_at < ? GROUP BY product_code",
                    (since, until))}
    delivered = db.execute(
        "SELECT COUNT(*) n FROM reports WHERE generated_at >= ? AND generated_at < ?",
        (since, until)).fetchone()["n"]
    drawings = db.execute(
        "SELECT AVG(n) a FROM (SELECT COUNT(d.id) n FROM orders o JOIN drawings d"
        " ON d.order_id = o.id WHERE o.paid_at >= ? AND o.paid_at < ? GROUP BY o.id)",
        (since, until)).fetchone()["a"]
    n_paid = paid["n"] or 0
    funnel = {
        "orders_created": created["n"] or 0,
        "orders_created_still_unpaid": created["unpaid"] or 0,
        "orders_created_and_paid": created["paid"] or 0,
        "paid_orders": n_paid,
        "reports_delivered": delivered,
        "paid_orders_by_status": {"delivered": paid["delivered"] or 0,
                                  "insufficient": paid["insufficient"] or 0,
                                  "failed": paid["failed"] or 0},
    }
    commercial = {
        "currency": settings.CURRENCY,
        "gross_revenue_usd": _usd(paid["cents"]),
        "paid_orders": n_paid,
        "average_order_value_usd": _usd(paid["cents"] // n_paid) if n_paid else None,
        "coupon_orders": paid["coupons"] or 0,
        "avg_drawings_per_paid_order": round(drawings, 2) if drawings is not None else None,
        "by_product": products,
        **{k: None for k in _UNAVAILABLE_MONEY},
        "note": ("gross revenue = SUM(orders.price_cents) for orders with paid_at in the "
                 "window (price after coupon, as charged); orders_created uses created_at"),
    }
    return funnel, commercial


def _doors(db, since: str, until: str) -> list[dict]:
    """The two nested visit funnels from app/admin_funnels.py, labels and counts only."""
    built = fn.build(db, since, until)
    return [{
        "door": d["key"], "title": d["title"], "visits": d["visits"],
        "gross_revenue_usd": float(d["revenue"]),
        "steps": [{"step": s["label"], "kind": s["kind"], "visits": s["n"],
                   "mobile": s["mobile"], "desktop": s["desktop"]} for s in d["steps"]],
    } for d in built["doors"]]


@bp_growth.get("/summary")
def summary():
    d_from, d_to, since, until = _period_args()
    db = get_db()
    warnings: list[str] = []

    traffic = _traffic(db, since, until)
    raw, human = traffic["visits_raw"], traffic["visits_engaged_human"]
    if raw:
        share = round((raw - traffic["visits_non_bot"]) / raw * 100)
        warnings.append(f"{share}% of raw visits are known bots; user-agent detection also "
                        "misses scanners and link fetchers, so visits_non_bot is still "
                        f"inflated - use {PRIMARY_METRIC} ({human}) as the human count")
    if traffic["visitors_unique_engaged_human"] < 30:
        warnings.append("small sample: fewer than 30 engaged human visitors in the window; "
                        "rates are not statistically meaningful")

    free = _free_block(db, since, until)
    orders_funnel, commercial = _orders_block(db, since, until)
    warnings += [f"{k} is null: {why}" for k, why in _UNAVAILABLE_MONEY.items()]

    lt_facts, unattributed = _last_touch_facts(db, since, until)
    ft_facts = _first_touch_facts(db, since, until)
    if any(unattributed.values()):
        warnings.append("last_touch: some free analyses / orders in the window belong to a "
                        "visit outside it or to a bot-flagged visit; see "
                        "attribution.last_touch.unattributed")
    ft_untagged = _totals([f for f in ft_facts if not f["utm"]])
    if ft_untagged["visitors"]:
        warnings.append("first_touch: the first-touch cookie is set only when a UTM was in the "
                        "URL, so organic/referral/direct first visits appear as utm=null")

    data = {
        "traffic": traffic,
        "funnel": {
            "doors": _doors(db, since, until),
            "free": free,
            "orders": orders_funnel,
        },
        "commercial": commercial,
        "attribution": {
            "note": ("last_touch = the tags of the visit itself (web_visits: utm, click id, "
                     "referer -> channel), outcomes joined by visit_id; first_touch = the "
                     "1-year first-touch UTM cookie as recorded on events/orders, outcomes "
                     "joined by visitor. They answer different questions and are never "
                     "merged."),
            "last_touch": {
                "totals": _totals(lt_facts),
                "by_channel": _channel_rows(lt_facts)[:ATTRIBUTION_ROWS_MAX],
                "by_utm_campaign": _utm_rows(lt_facts, "campaign")[:ATTRIBUTION_ROWS_MAX],
                "by_utm_source": _utm_rows(lt_facts, "source")[:ATTRIBUTION_ROWS_MAX],
                "untagged": _totals([f for f in lt_facts if not f["utm"]]),
                "unattributed": unattributed,
            },
            "first_touch": {
                "totals": _totals(ft_facts),
                "by_utm_campaign": _utm_rows(ft_facts, "campaign")[:ATTRIBUTION_ROWS_MAX],
                "by_utm_source": _utm_rows(ft_facts, "source")[:ATTRIBUTION_ROWS_MAX],
                "untagged": ft_untagged,
            },
        },
    }
    return _json(_envelope(d_from.isoformat(), d_to.isoformat(), data, warnings))


# --- /content -----------------------------------------------------------------------------

@bp_growth.get("/content")
def content():
    d_from, d_to, since, until = _period_args()
    limit = _limit_arg(CONTENT_LIMIT_DEFAULT, CONTENT_LIMIT_MAX)
    db = get_db()
    warnings: list[str] = []

    lt_facts, unattributed = _last_touch_facts(db, since, until)
    ft_facts = _first_touch_facts(db, since, until)

    def table(facts: list[dict]) -> dict:
        rows = _utm_rows(facts, "content")
        truncated = len(rows) > limit
        return {
            "content": rows[:limit],
            "content_truncated": truncated,
            "campaign": _utm_rows(facts, "campaign")[:limit],
            "source": _utm_rows(facts, "source")[:limit],
            "untagged": _totals([f for f in facts if not f["utm"]]),
        }

    last = table(lt_facts)
    first = table(ft_facts)
    if last["content_truncated"] or first["content_truncated"]:
        warnings.append(f"content rows truncated to limit={limit}")
    if not last["content"] and not first["content"]:
        warnings.append("no visit in the window carried utm_content; content-level "
                        "attribution needs utm_content on the inbound link")
    if any(unattributed.values()):
        warnings.append("last_touch: some outcomes in the window belong to a visit outside it "
                        "or to a bot-flagged visit; see last_touch.unattributed")
    warnings.append("utm_medium=social does not separate paid from organic clicks on the "
                    "same boosted post; use a distinct utm_medium per paid placement")
    last["unattributed"] = unattributed

    data = {
        "grouping": ("rows are grouped by (utm_source, utm_medium, utm_campaign, utm_content) "
                     "at level=content, by campaign and by source; a row exists only where the "
                     "tag exists - nothing is guessed"),
        "last_touch": last,
        "first_touch": first,
        "limit": limit,
    }
    return _json(_envelope(d_from.isoformat(), d_to.isoformat(), data, warnings))


# --- /changes -----------------------------------------------------------------------------

def _parse_ts(raw: str) -> datetime.datetime:
    """ISO-8601 -> aware UTC datetime. A trailing Z and a naive value are both accepted;
    naive means UTC."""
    s = raw.strip()
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"
    dt = datetime.datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def load_changes(path=None) -> tuple[list[dict], int]:
    """Parse growth/growth_changes.jsonl -> (entries sorted oldest first, malformed count).
    Blank lines are ignored; a line that is not a JSON object with an id and a parseable
    timestamp is skipped and counted, never raised: one bad line must not take the whole
    log offline."""
    path = path or settings.GROWTH_CHANGES_FILE
    entries: list[dict] = []
    bad = 0
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict) or not obj.get("id") or not obj.get("timestamp"):
                raise ValueError("not a change entry")
            obj["_ts"] = _parse_ts(str(obj["timestamp"]))
        except (ValueError, TypeError):
            bad += 1
            continue
        entries.append(obj)
    entries.sort(key=lambda e: (e["_ts"], str(e["id"])))
    return entries, bad


@bp_growth.get("/changes")
def changes():
    raw = request.args.get("since")
    if not raw:
        raise ApiError(400, "bad_request", "since is required (ISO-8601, e.g. 2026-09-01T00:00:00Z)")
    try:
        since_dt = _parse_ts(raw)
    except ValueError:
        raise ApiError(400, "bad_request", "since is not a valid ISO-8601 timestamp")
    limit = _limit_arg(CHANGES_LIMIT_MAX, CHANGES_LIMIT_MAX)
    warnings: list[str] = []
    entries, bad = load_changes()
    if bad:
        warnings.append(f"{bad} malformed line(s) in the change log were skipped")
    selected = [e for e in entries if e["_ts"] >= since_dt]
    if len(selected) > limit:
        warnings.append(f"truncated to the oldest {limit} entries; move since forward")
        selected = selected[:limit]
    out = [{k: v for k, v in e.items() if not k.startswith("_")} for e in selected]
    now = _now_iso()
    data = {"changes": out, "count": len(out)}
    return _json(_envelope(since_dt.isoformat(timespec="seconds"), now, data, warnings))
