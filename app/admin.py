"""Admin panel /admin: left sidebar, one screen per section.

Sections: analytics (KPI/funnel/sources/events), visits, actions, orders, clients,
coupons, settings (prices/products -> config/products.json), emails (outbox).

Access is SEPARATE from the customer /login: password from .env (ADMIN_PASS).
Cookie dr_a = HMAC of the password (stateless; changing the password logs out).
Empty ADMIN_PASS = admin disabled (404). Admin UI is English-only.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import re

from flask import (Blueprint, Response, abort, redirect, render_template, request,
                   url_for)

from app import admin_free_analytics as fa
from app import admin_funnels as fn
from app import admin_tasks as tasks
from app import geoip, jobs
from app.db import get_db, now
from config import settings

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")

ADMIN_COOKIE = "dr_a"

# Sidebar: (endpoint, label). Tasks is first on purpose - it is the only section that
# asks the owner to do something.
SECTIONS = [
    ("admin.todo", "Tasks"),
    ("admin.analytics", "Analytics"),
    ("admin.visits", "Visits"),
    ("admin.actions", "Actions"),
    ("admin.orders", "Orders"),
    ("admin.clients", "Clients"),
    ("admin.coupons", "Coupons"),
    ("admin.prices", "Prices"),
    ("admin.site_settings", "Site settings"),
    ("admin.report_texts", "Report texts"),
    ("admin.emails", "Emails"),
    ("admin.free_analytics", "Freemium"),
    ("admin.free", "Beta"),
]

# How many minutes in the queue counts as stuck: free_worker polls once a second and a
# reading takes under a minute, so five minutes in 'queued' means the unit is not running.
FREE_STUCK_MINUTES = 5

# The owner's verdict on an interpretation key - the main result of the beta.
FREE_VERDICTS = [("confirmed", "confirmed by a source"),
                 ("narrow", "only in a narrow context"),
                 ("folklore", "folklore")]

# Funnel steps moved to app/admin_funnels.py: there they are counted by VISIT and are
# nested by construction. Only the sidebar and the periods live here.

PERIODS = [("1", "today"), ("7", "7 days"), ("30", "30 days"), ("all", "all time")]

# Analytics shows ONLY humans: bots (device='bot') are excluded everywhere.
# device IS NULL = worker server events (payment/delivery) - keep those.
NOT_BOT = "(device IS NULL OR device <> 'bot')"


def _admin_token() -> str:
    return hmac.new(settings.ADMIN_PASS.encode(), b"dr-admin-v1",
                    hashlib.sha256).hexdigest()


def _is_admin() -> bool:
    if not settings.ADMIN_PASS:
        return False
    return hmac.compare_digest(request.cookies.get(ADMIN_COOKIE, ""), _admin_token())


def _guard():
    if not settings.ADMIN_PASS:
        abort(404)
    if not _is_admin():
        abort(redirect(url_for("admin.login_form")))


def _render(section_endpoint, template, **ctx):
    return render_template(template, sections=SECTIONS, active=section_endpoint, **ctx)


@bp_admin.get("/login")
def login_form():
    if not settings.ADMIN_PASS:
        abort(404)
    if _is_admin():
        return redirect(url_for("admin.analytics"))
    return render_template("admin/login.html", error=None)


@bp_admin.post("/login")
def login_submit():
    if not settings.ADMIN_PASS:
        abort(404)
    if not hmac.compare_digest(request.form.get("password", ""), settings.ADMIN_PASS):
        return render_template("admin/login.html", error="Wrong password"), 401
    resp = redirect(url_for("admin.analytics"))
    resp.set_cookie(ADMIN_COOKIE, _admin_token(), max_age=30 * 24 * 3600,
                    httponly=True, samesite="Lax")
    return resp


@bp_admin.post("/logout")
def logout():
    resp = redirect("/")
    resp.delete_cookie(ADMIN_COOKIE)
    return resp


@bp_admin.get("/")
def index():
    _guard()
    return redirect(url_for("admin.analytics"))


def _period():
    days = request.args.get("days", "7")
    if days not in {p[0] for p in PERIODS}:
        days = "7"
    if days == "all":
        return days, "0000"
    since = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.timedelta(days=int(days))).isoformat(timespec="seconds")
    return days, since


def _utm_label(j):
    try:
        u = json.loads(j) if j else None
    except ValueError:
        u = None
    if not u:
        return "(direct / no UTM)"
    return " / ".join(filter(None, [u.get("utm_source"), u.get("utm_medium"),
                                    u.get("utm_campaign")]))


DRILL_CAP = 60


def _drill_member(row):
    vid = row["visitor_id"]
    cid = row["cid"]
    return {
        "id": (vid or (f"c{cid}" if cid else ""))[:12],
        "geo": geoip.geo_label(row["gc"], row["gr"]),
        "device": row["dev"] or "-",
        "customer": f"c{cid}" if cid else "",
        "time": row["last"][:16].replace("T", " "),
    }


@bp_admin.get("/todo")
def todo():
    """What has to be done BY HAND: key events in GA4, credentials, a legal review.
    First in the sidebar on purpose - it is the only section that asks for action."""
    _guard()
    return _render("admin.todo", "admin/todo.html", **tasks.load(get_db()),
                   msg=request.args.get("msg"))


@bp_admin.post("/todo/add")
def todo_add():
    _guard()
    title = (request.form.get("title") or "").strip()
    if not title:
        return redirect(url_for("admin.todo", msg="A task needs a title"))
    tasks.add(get_db(), title, (request.form.get("details") or "").strip())
    return redirect(url_for("admin.todo"))


@bp_admin.post("/todo/<int:task_id>/toggle")
def todo_toggle(task_id):
    _guard()
    tasks.toggle(get_db(), task_id)
    return redirect(url_for("admin.todo"))


@bp_admin.post("/todo/<int:task_id>/delete")
def todo_delete(task_id):
    _guard()
    ok = tasks.delete(get_db(), task_id)
    return redirect(url_for("admin.todo", msg=None if ok else
                            "This task cannot be deleted - it can only be closed"))


@bp_admin.get("/analytics")
def analytics():
    _guard()
    days, since = _period()
    show_all = request.args.get("show") == "all"
    if show_all:
        eng, eng_p = "", []
    else:
        eng = (" AND (visitor_id IS NULL OR visitor_id IN"
               " (SELECT visitor_id FROM events WHERE type='engaged' AND created_at >= ?))")
        eng_p = [since]
    db = get_db()

    humans = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events"
        f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND created_at >= ?", (since,)).fetchone()["c"]
    engaged = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events"
        f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND type = 'engaged' AND created_at >= ?",
        (since,)).fetchone()["c"]
    landing_only = humans - engaged
    visitors = humans if show_all else engaged
    bots = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events"
        " WHERE visitor_id IS NOT NULL AND device = 'bot' AND created_at >= ?", (since,)).fetchone()["c"]
    orders_total = db.execute(
        "SELECT COUNT(*) c FROM orders WHERE created_at >= ?", (since,)).fetchone()["c"]
    paid = db.execute(
        "SELECT COUNT(*) c, COALESCE(SUM(price_cents), 0) s FROM orders"
        " WHERE paid_at IS NOT NULL AND paid_at >= ?", (since,)).fetchone()
    kpi = {
        "visitors": visitors, "orders": orders_total, "paid": paid["c"],
        "revenue_usd": paid["s"] // 100,
        "conversion": f"{paid['c'] / visitors * 100:.1f}%" if visitors else "-",
    }

    # Funnels by VISIT (app/admin_funnels.py). The old funnel divided nine independent
    # sets of unique visitors by one another - the steps were not nested, and "paid"
    # arrived from a webhook with no visitor at all.
    funnels = fn.build(db, since)

    sources, src_members = {}, {}
    for row in db.execute(
            "SELECT utm_json, visitor_id, MAX(geo_country) gc, MAX(geo_region) gr,"
            " MAX(device) dev, MAX(customer_id) cid, MAX(created_at) last FROM events"
            f" WHERE type = 'landing_view' AND {NOT_BOT} AND created_at >= ?{eng}"
            " GROUP BY utm_json, visitor_id ORDER BY last DESC", (since, *eng_p)):
        label = _utm_label(row["utm_json"])
        s = sources.setdefault(label, {"visitors": 0, "orders": 0, "paid": 0, "usd": 0})
        s["visitors"] += 1
        lst = src_members.setdefault(label, [])
        if len(lst) < DRILL_CAP:
            lst.append(_drill_member(row))
    for row in db.execute("SELECT utm_json, paid_at, price_cents FROM orders WHERE created_at >= ?",
                          (since,)):
        s = sources.setdefault(_utm_label(row["utm_json"]),
                               {"visitors": 0, "orders": 0, "paid": 0, "usd": 0})
        s["orders"] += 1
        if row["paid_at"]:
            s["paid"] += 1
            s["usd"] += row["price_cents"] // 100

    events = db.execute(
        "SELECT type, visitor_id, customer_id, device, geo_country, geo_region,"
        f" payload_json, created_at FROM events WHERE {NOT_BOT} AND created_at >= ?{eng}"
        " ORDER BY id DESC LIMIT 60", (since, *eng_p)).fetchall()
    events_view = [{
        "time": e["created_at"][:19].replace("T", " "), "type": e["type"],
        "geo": geoip.geo_label(e["geo_country"], e["geo_region"]),
        "device": e["device"] or ("-" if e["visitor_id"] else "server"),
        "who": f"c{e['customer_id']}" if e["customer_id"] else (e["visitor_id"] or "")[:8],
        "payload": (e["payload_json"] or "")[:90],
    } for e in events]

    sources_view = [(name, s, src_members.get(name, []))
                    for name, s in sorted(sources.items(), key=lambda kv: -kv[1]["visitors"])]
    return _render("admin.analytics", "admin/analytics.html",
                   days=days, periods=PERIODS, show=request.args.get("show"),
                   kpi=kpi, funnels=funnels, sources=sources_view, events=events_view,
                   bots=bots, humans=humans, engaged=engaged, landing_only=landing_only,
                   free=fa.dashboard_counters(db, since),
                   ga_configured=bool(settings.GA_MEASUREMENT_ID))


@bp_admin.get("/visits")
def visits():
    _guard()
    days, since = _period()
    show = request.args.get("show")
    db = get_db()
    devices = db.execute(
        "SELECT COALESCE(device, '-') d, COUNT(DISTINCT visitor_id) c FROM events"
        f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND created_at >= ? GROUP BY device"
        " ORDER BY c DESC", (since,)).fetchall()
    devices_view = [{"device": r["d"], "n": r["c"]} for r in devices]

    src = {}
    for row in db.execute(
            "SELECT utm_json, COUNT(DISTINCT visitor_id) c FROM events"
            f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND created_at >= ? GROUP BY utm_json",
            (since,)):
        src[_utm_label(row["utm_json"])] = src.get(_utm_label(row["utm_json"]), 0) + row["c"]
    sources = sorted(src.items(), key=lambda kv: -kv[1])

    geo_rows = db.execute(
        "SELECT geo_country, COUNT(DISTINCT visitor_id) c FROM events"
        f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND geo_country IS NOT NULL"
        " AND created_at >= ? GROUP BY geo_country ORDER BY c DESC LIMIT 15", (since,)).fetchall()
    geo_view = [{"country": geoip.country_name(r["geo_country"]), "n": r["c"]} for r in geo_rows]

    engaged_expr = "MAX(CASE WHEN type = 'engaged' THEN 1 ELSE 0 END)"
    having = "" if show == "all" else f" HAVING {engaged_expr} = 0"
    rows = db.execute(
        "SELECT visitor_id, COUNT(*) n, MIN(created_at) first_seen, MAX(created_at) last_seen,"
        " MAX(device) device, MAX(referer) referer, MAX(utm_json) utm_json,"
        " MAX(customer_id) customer_id, MAX(geo_country) geo_country, MAX(geo_region) geo_region,"
        f" {engaged_expr} engaged FROM events WHERE visitor_id IS NOT NULL AND {NOT_BOT}"
        f" AND created_at >= ? GROUP BY visitor_id{having} ORDER BY last_seen DESC LIMIT 200",
        (since,)).fetchall()

    ids = [r["visitor_id"] for r in rows]
    timeline = _visitor_timelines(db, ids, since)
    orders_by_vis = _visitor_orders(db, ids)

    visitors_view = [{
        "id": (r["visitor_id"] or "")[:10], "device": r["device"] or "-",
        "utm": _utm_label(r["utm_json"]), "referer": (r["referer"] or "")[:60] or "(direct)",
        "events": r["n"], "engaged": bool(r["engaged"]),
        "customer": f"c{r['customer_id']}" if r["customer_id"] else "",
        "geo": geoip.geo_label(r["geo_country"], r["geo_region"]),
        "first": r["first_seen"][:16].replace("T", " "),
        "last": r["last_seen"][:16].replace("T", " "),
        "timeline": timeline.get(r["visitor_id"], []),
        "orders": orders_by_vis.get(r["visitor_id"], []),
    } for r in rows]

    total = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events"
        f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND created_at >= ?", (since,)).fetchone()["c"]
    engaged = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events"
        f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND type = 'engaged' AND created_at >= ?",
        (since,)).fetchone()["c"]
    bots = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events"
        " WHERE visitor_id IS NOT NULL AND device = 'bot' AND created_at >= ?",
        (since,)).fetchone()["c"]
    bounce = f"{(total - engaged) / total * 100:.0f}%" if total else "-"
    return _render("admin.visits", "admin/visits.html",
                   days=days, periods=PERIODS, show=show, shown=len(rows),
                   devices=devices_view, sources=sources, geo=geo_view,
                   visitors=visitors_view, total=total, engaged=engaged,
                   bounce=bounce, bots=bots)


def _visitor_timelines(db, ids, since, cap=100):
    """Full event feed for the visitors on screen (up to cap each)."""
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    rows = db.execute(
        "SELECT visitor_id, type, payload_json, device, referer,"
        " geo_country, geo_region, created_at"
        f" FROM events WHERE visitor_id IN ({ph}) AND created_at >= ?"
        " ORDER BY id DESC", (*ids, since)).fetchall()
    out = {}
    for e in rows:
        lst = out.setdefault(e["visitor_id"], [])
        if len(lst) >= cap:
            continue
        lst.append({
            "time": e["created_at"][:19].replace("T", " "),
            "type": e["type"],
            "payload": (e["payload_json"] or ""),
            "device": e["device"] or "",
            "referer": (e["referer"] or ""),
            "geo": geoip.geo_label(e["geo_country"], e["geo_region"]),
        })
    return out


def _visitor_orders(db, ids):
    """Orders tied to the visitors on screen (orders.visitor_id)."""
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    out = {}
    try:
        rows = db.execute(
            f"SELECT id, visitor_id, status FROM orders WHERE visitor_id IN ({ph})",
            tuple(ids)).fetchall()
    except Exception:
        return {}
    for r in rows:
        out.setdefault(r["visitor_id"], []).append(
            {"id": r["id"], "status": r["status"]})
    return out


@bp_admin.get("/actions")
def actions():
    _guard()
    days, since = _period()
    q = (request.args.get("q") or "").strip()
    db = get_db()
    params = [since]
    where = f"created_at >= ? AND {NOT_BOT}"
    if q:
        where += " AND type LIKE ?"
        params.append(f"%{q}%")
    bots = db.execute(
        "SELECT COUNT(*) c FROM events WHERE created_at >= ? AND device = 'bot'"
        + (" AND type LIKE ?" if q else ""),
        [since] + ([f"%{q}%"] if q else [])).fetchone()["c"]

    summary = db.execute(
        f"SELECT type, COUNT(*) n, COUNT(DISTINCT visitor_id) u, MAX(created_at) last"
        f" FROM events WHERE {where} GROUP BY type ORDER BY n DESC", params).fetchall()
    summary_view = [{"type": r["type"], "n": r["n"], "users": r["u"],
                     "last": r["last"][:16].replace("T", " ") if r["last"] else ""}
                    for r in summary]
    total = sum(r["n"] for r in summary)
    recent = db.execute(
        f"SELECT type, visitor_id, device, payload_json, created_at"
        f" FROM events WHERE {where} ORDER BY id DESC LIMIT 100", params).fetchall()
    recent_view = [{"time": e["created_at"][:19].replace("T", " "), "type": e["type"],
                    "who": (e["visitor_id"] or "")[:8], "device": e["device"] or "-",
                    "payload": (e["payload_json"] or "")[:80]} for e in recent]
    return _render("admin.actions", "admin/actions.html",
                   days=days, periods=PERIODS, q=q,
                   summary=summary_view, total=total, recent=recent_view, bots=bots)


@bp_admin.get("/orders")
def orders():
    _guard()
    days, since = _period()
    rows = get_db().execute(
        "SELECT o.*, r.public_token,"
        " (SELECT COUNT(*) FROM drawings d WHERE d.order_id = o.id) AS drawings_n"
        " FROM orders o LEFT JOIN reports r ON r.order_id = o.id"
        " WHERE o.created_at >= ? ORDER BY o.id DESC LIMIT 300", (since,)).fetchall()
    orders_view = []
    for o in rows:
        child = json.loads(o["child_json"] or "{}")
        orders_view.append({
            "id": o["id"], "created": o["created_at"][:16].replace("T", " "),
            "email": o["email"], "child": child.get("name", ""),
            "product": o["product_code"], "usd": o["price_cents"] // 100,
            "coupon": o["coupon_code"] or "", "status": o["status"],
            "drawings": o["drawings_n"], "token": o["public_token"],
            "locale": o["locale"], "utm": _utm_label(o["utm_json"]) if o["utm_json"] else "",
        })
    return _render("admin.orders", "admin/orders.html",
                   days=days, periods=PERIODS, orders=orders_view,
                   msg=request.args.get("msg"))


@bp_admin.post("/orders/<int:order_id>/resend")
def order_resend(order_id):
    _guard()
    days = request.form.get("days", "7")
    conn = get_db()
    order = conn.execute("SELECT id, status FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        abort(404)
    if order["status"] == "created":
        msg = f"Order {order_id}: not paid - nothing to send"
    elif order["status"] in ("paid", "generating"):
        msg = f"Order {order_id}: already in progress"
    elif jobs.report_pdf_path(conn, order_id):
        jobs.resend_report_email(conn, order_id)
        msg = f"Order {order_id}: report email re-sent"
    else:
        conn.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order_id,))
        conn.commit()
        msg = f"Order {order_id}: queued for regeneration"
    return redirect(url_for("admin.orders", days=days, msg=msg))


@bp_admin.post("/orders/<int:order_id>/regenerate")
def order_regenerate(order_id):
    _guard()
    days = request.form.get("days", "7")
    conn = get_db()
    order = conn.execute("SELECT id, status FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        abort(404)
    if order["status"] == "created":
        msg = f"Order {order_id}: not paid - nothing to regenerate"
    elif order["status"] == "generating":
        msg = f"Order {order_id}: already generating"
    else:
        conn.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order_id,))
        conn.commit()
        msg = f"Order {order_id}: regeneration queued (current prompt)"
    return redirect(url_for("admin.orders", days=days, msg=msg))


@bp_admin.get("/clients")
def clients():
    _guard()
    rows = get_db().execute(
        "SELECT c.id, c.email, c.created_at,"
        " (SELECT GROUP_CONCAT(name, ', ') FROM children ch WHERE ch.customer_id = c.id) kids,"
        " (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id) n_orders,"
        " (SELECT COALESCE(SUM(price_cents), 0) FROM orders o"
        "   WHERE o.customer_id = c.id AND o.paid_at IS NOT NULL) paid_c"
        " FROM customers c ORDER BY c.id DESC LIMIT 500").fetchall()
    clients_view = [{"id": r["id"], "email": r["email"], "created": r["created_at"][:10],
                     "kids": r["kids"] or "", "orders": r["n_orders"], "usd": r["paid_c"] // 100}
                    for r in rows]
    return _render("admin.clients", "admin/clients.html", clients=clients_view)


@bp_admin.get("/coupons")
def coupons():
    _guard()
    rows = get_db().execute("SELECT * FROM coupons ORDER BY rowid DESC").fetchall()
    return _render("admin.coupons", "admin/coupons.html",
                   coupons=rows, error=request.args.get("err"))


@bp_admin.post("/coupons/create")
def coupons_create():
    _guard()
    code = re.sub(r"[^A-Za-z0-9_-]", "", request.form.get("code", "")).upper()
    try:
        percent = int(request.form.get("percent", ""))
    except ValueError:
        percent = 0
    multi = 1 if request.form.get("multi_use") else 0
    if not code or not (1 <= percent <= 100):
        return redirect(url_for("admin.coupons", err="Code and a 1-100% discount are required"))
    db = get_db()
    if db.execute("SELECT 1 FROM coupons WHERE upper(code) = ?", (code,)).fetchone():
        return redirect(url_for("admin.coupons", err=f"Code {code} already exists"))
    db.execute("INSERT INTO coupons (code, percent_off, multi_use, active) VALUES (?, ?, ?, 1)",
               (code, percent, multi))
    db.commit()
    return redirect(url_for("admin.coupons"))


@bp_admin.post("/coupons/<code>/toggle")
def coupons_toggle(code):
    _guard()
    db = get_db()
    db.execute("UPDATE coupons SET active = 1 - active WHERE code = ?", (code,))
    db.commit()
    return redirect(url_for("admin.coupons"))


def _heartbeats(db):
    """Are the background units alive? deploy.sh does not start a new unit and there is no
    monitoring - without this row, after a reboot of the box free readings would silently
    stop being generated and nothing on any screen would say so.

    Each unit gets its own threshold: free_worker marks itself once a second, while the
    paid worker is silent for the whole time it generates a report (minutes). A shared
    120s limit would paint normal operation as an alarm."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    seen = {r["name"]: r["last_seen_at"] for r in
            db.execute("SELECT name, last_seen_at FROM service_heartbeat")}
    out = []
    for name, label, limit in (("free_worker", "free_worker (free readings)", 120),
                               ("worker", "worker (paid reports)", 600)):
        ts = seen.get(name)
        ago = None
        if ts:
            try:
                ago = int((now_utc - datetime.datetime.fromisoformat(ts)).total_seconds())
            except ValueError:
                ago = None
        out.append({"name": name, "label": label, "ago": ago,
                    "ok": ago is not None and ago < limit})
    return out


@bp_admin.get("/free-analytics")
def free_analytics():
    """Freemium BEHAVIOUR: how far people get, what they pick, who buys afterwards.
    "Beta" next door is about the QUALITY of the texts (the interpretation library).
    Mixing the two on one screen would mean reading neither."""
    _guard()
    days, since = _period()
    return _render("admin.free_analytics", "admin/free_analytics.html",
                   days=days, periods=PERIODS, **fa.page_data(get_db(), since))


@bp_admin.get("/free")
def free():
    """The beta: individual readings and the interpretation library."""
    _guard()
    days, since = _period()
    db = get_db()

    rows = db.execute(
        "SELECT * FROM free_analyses WHERE created_at >= ?"
        " ORDER BY id DESC LIMIT 300", (since,)).fetchall()
    purchases = fa.purchases_index(db, rows)
    items = []
    for r in rows:
        interps = db.execute(
            "SELECT * FROM free_interpretations WHERE analysis_id = ? ORDER BY id",
            (r["id"],)).fetchall()
        data = json.loads(r["result_json"] or "{}")
        items.append({
            "id": r["id"], "token": r["token"],
            "created": (r["created_at"] or "")[:16].replace("T", " "),
            "child": r["child_name"], "age": r["age"],
            "concern": fa.concern_label(r["concern_key"]), "duration": r["duration_key"],
            "status": r["status"], "reason": r["reason_key"],
            "flags": ", ".join(data.get("flags") or []),
            "correlate": data.get("concern_correlate_visible"),
            "email": r["email"] or "", "seconds": r["elapsed_s"],
            "repairs": r["repair_rounds"], "dropped": r["hypothesis_dropped"],
            "image_deleted": bool(r["image_deleted_at"]),
            "has_image": bool(r["image_path"]),
            "parent_text": r["parent_text"] or "",
            "interps": [dict(i) for i in interps],
            "purchases": purchases.get(r["id"]) or [],
        })

    # The library: grouped by key, with the parents' votes and the current verdict. This
    # is the main result of the beta - what the model actually says about real drawings,
    # graded.
    lib = db.execute(
        "SELECT i.key, COUNT(*) AS n,"
        " SUM(CASE WHEN i.parent_vote = 'yes' THEN 1 ELSE 0 END) AS yes_n,"
        " SUM(CASE WHEN i.parent_vote = 'no' THEN 1 ELSE 0 END) AS no_n,"
        " MIN(i.created_at) AS first_at, k.verdict, k.note"
        " FROM free_interpretations i"
        " LEFT JOIN free_interpretation_keys k ON k.key = i.key"
        " GROUP BY i.key ORDER BY n DESC").fetchall()
    library = []
    for k in lib:
        examples = db.execute(
            "SELECT phrase, new_key_description, age_scope, child_age, parent_vote"
            " FROM free_interpretations WHERE key = ? ORDER BY id DESC LIMIT 3",
            (k["key"],)).fetchall()
        library.append({**dict(k), "examples": [dict(e) for e in examples],
                        "in_dictionary": k["key"] in _dict_keys()})

    funnel = []
    for status, label in (("draft", "answered the questions"),
                          ("queued", "uploaded a drawing"),
                          ("generating", "being read"), ("done", "got a reading"),
                          ("insufficient", "refused (unusable photo)"),
                          ("failed", "failed")):
        n = db.execute("SELECT COUNT(*) c FROM free_analyses"
                       " WHERE status = ? AND created_at >= ?",
                       (status, since)).fetchone()["c"]
        funnel.append({"status": status, "label": label, "n": n})

    voted = db.execute("SELECT COUNT(*) c FROM free_interpretations"
                       " WHERE parent_vote IS NOT NULL").fetchone()["c"]
    with_email = db.execute(
        "SELECT COUNT(*) c FROM free_analyses WHERE email IS NOT NULL"
        " AND created_at >= ?", (since,)).fetchone()["c"]
    stuck = db.execute(
        "SELECT COUNT(*) c FROM free_analyses WHERE status IN ('queued','generating')"
        " AND created_at < ?",
        ((datetime.datetime.now(datetime.timezone.utc)
          - datetime.timedelta(minutes=FREE_STUCK_MINUTES)).isoformat(timespec="seconds"),
         )).fetchone()["c"]

    return _render("admin.free", "admin/free.html", days=days, periods=PERIODS,
                   items=items, library=library, funnel=funnel, voted=voted,
                   with_email=with_email, stuck=stuck, verdicts=FREE_VERDICTS,
                   heartbeats=_heartbeats(db), stuck_minutes=FREE_STUCK_MINUTES,
                   used_today=_free_used_today(db),
                   limits=settings.get_free_limits(),
                   msg=request.args.get("msg"))


def _dict_keys():
    from config.free_keys import INTERPRETATION_KEYS
    return set(INTERPRETATION_KEYS)


def _free_used_today(db):
    from app.free_retention import used_today
    return used_today(db)


@bp_admin.post("/free/key/<path:key>")
def free_key_verdict(key):
    """Grading an interpretation BY KEY - this is the main result of the beta."""
    _guard()
    verdict = (request.form.get("verdict") or "").strip()
    note = (request.form.get("note") or "").strip()
    if verdict not in {v[0] for v in FREE_VERDICTS}:
        return redirect(url_for("admin.free", msg="Unknown verdict"))
    db = get_db()
    db.execute(
        "INSERT INTO free_interpretation_keys (key, verdict, note, decided_at)"
        " VALUES (?, ?, ?, ?)"
        " ON CONFLICT(key) DO UPDATE SET verdict = excluded.verdict,"
        " note = excluded.note, decided_at = excluded.decided_at",
        (key, verdict, note, now()))
    db.commit()
    return redirect(url_for("admin.free", msg=f"{key}: {verdict}"))


@bp_admin.post("/free/<int:analysis_id>/delete-image")
def free_delete_image(analysis_id):
    """Delete a photo on the parent's request. There was NO deletion path in the project
    at all, and the first such request is inevitable: we are storing other people's
    children's drawings."""
    _guard()
    from app.free_retention import delete_image
    ok = delete_image(get_db(), analysis_id)
    return redirect(url_for("admin.free",
                            msg="Photo deleted" if ok else "The file was already gone"))


def _load_products_for_edit():
    src = settings.PRODUCTS_RUNTIME_FILE if settings.PRODUCTS_RUNTIME_FILE.exists() \
        else settings.PRODUCTS_DEFAULT_FILE
    return json.loads(src.read_text(encoding="utf-8"))


def _atomic_write_json(path, data):
    """Temp file + rename: a reader never sees half a JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


@bp_admin.get("/prices")
def prices():
    """Product prices: before the discount (struck through) and payable (after).
    PayPal is charged the PAYABLE price, minus any coupon - see orders.py.

    The freemium limits live on this page too: they are the other money knob. Every free
    reading costs a model call whether or not the parent ever buys."""
    _guard()
    db = get_db()
    return _render("admin.prices", "admin/prices.html",
                   products=settings.get_products(),
                   limits=settings.get_free_limits(),
                   used_today=_free_used_today(db),
                   saved=request.args.get("saved"),
                   err=request.args.get("err"))


@bp_admin.post("/prices/limits")
def prices_limits_save():
    """The two freemium limits. 0 = unlimited, and the form says so - a blank field that
    silently means "no limit" is how an unbounded bill happens."""
    _guard()
    out = {}
    for field in ("daily_cap", "per_email_daily"):
        raw = (request.form.get(field) or "").strip()
        try:
            n = int(raw)
        except ValueError:
            return redirect(url_for("admin.prices",
                                    err="Limits must be whole numbers (0 = unlimited)"))
        if n < 0:
            return redirect(url_for("admin.prices", err="A limit cannot be negative"))
        out[field] = n
    _atomic_write_json(settings.FREE_LIMITS_RUNTIME_FILE, out)
    return redirect(url_for("admin.prices", saved="limits"))


@bp_admin.post("/prices/save")
def prices_save():
    """Edits ONLY the price fields on top of the current products.json: the other keys
    (texts, features, enabled) are left alone."""
    _guard()
    data = _load_products_for_edit()
    for code, p in data.items():
        f = lambda k: request.form.get(f"{code}_{k}", "").strip()
        try:
            price = int(f("price_usd"))
        except ValueError:
            return redirect(url_for("admin.prices", err="Payable price must be a whole number of $"))
        if price < 1:
            return redirect(url_for("admin.prices", err="Payable price must be above zero"))
        # The pre-discount price is optional: empty => no struck-through price on the site.
        old = f("old_price_usd")
        if old:
            try:
                old_price = int(old)
            except ValueError:
                return redirect(url_for("admin.prices", err="Pre-discount price must be a whole number of $"))
            if old_price <= price:
                return redirect(url_for("admin.prices",
                                        err="Pre-discount price must be higher than the payable price"))
            p["old_price_usd"] = old_price
        else:
            p.pop("old_price_usd", None)
        p["price_usd"] = price
    _atomic_write_json(settings.PRODUCTS_RUNTIME_FILE, data)
    return redirect(url_for("admin.prices", saved="ok"))


@bp_admin.get("/settings")
def site_settings():
    _guard()
    return _render("admin.site_settings", "admin/settings.html",
                   products=settings.get_products(),
                   ga_id=settings.GA_MEASUREMENT_ID,
                   mail_backend=settings.MAIL_BACKEND, mail_from=settings.MAIL_FROM_EMAIL,
                   resend_key=bool(settings.RESEND_API_KEY),
                   payment_backend=settings.PAYMENT_BACKEND,
                   saved=request.args.get("saved"))


@bp_admin.post("/settings/products")
def settings_products_save():
    """Edits products on top of the current products.json: only the editable fields
    change, unknown keys are preserved as they are."""
    _guard()
    data = _load_products_for_edit()
    for code, p in data.items():
        f = lambda k: request.form.get(f"{code}_{k}", "").strip()
        p["enabled"] = bool(request.form.get(f"{code}_enabled"))
        if f("title"):
            p["title"] = f("title")
        p["subtitle"] = f("subtitle")
        # Prices are edited on their own page (/admin/prices).
        p["features"] = [ln.strip() for ln in
                         request.form.get(f"{code}_features", "").splitlines() if ln.strip()]
    if not any(p["enabled"] for p in data.values()):
        return redirect(url_for("admin.site_settings", saved="err"))  # a site with no products
    _atomic_write_json(settings.PRODUCTS_RUNTIME_FILE, data)
    return redirect(url_for("admin.site_settings", saved="ok"))


@bp_admin.get("/report-texts")
def report_texts():
    """Admin-controlled blocks at the END of a report (upsell by drawing count +
    disclaimers + a free block). Pass-through to the pipeline via config/report_texts.json."""
    _guard()
    return _render("admin.report_texts", "admin/report_texts.html",
                   texts=settings.get_report_texts(),
                   saved=request.args.get("saved"))


@bp_admin.post("/report-texts/save")
def report_texts_save():
    """Overwrite data/report_texts.json. Empty field = block not rendered in the report."""
    _guard()
    g = lambda k: request.form.get(k, "").strip()
    data = {
        "upsell": {n: g(f"upsell_{n}") for n in ("1", "2", "3")},
        "disclaimer_main": g("disclaimer_main"),
        "disclaimer_by_count": {n: g(f"disclaimer_by_count_{n}") for n in ("1", "2", "3")},
        "free_text": g("free_text"),
    }
    _atomic_write_json(settings.REPORT_TEXTS_RUNTIME_FILE, data)
    return redirect(url_for("admin.report_texts", saved="ok"))


@bp_admin.get("/emails")
def emails():
    _guard()
    files = []
    if settings.OUTBOX_DIR.exists():
        for p in sorted(settings.OUTBOX_DIR.glob("*.html"), reverse=True)[:200]:
            head = p.read_text(encoding="utf-8")[:600]
            to = re.search(r"^To: (.+)$", head, re.M)
            subj = re.search(r"^Subject: (.+)$", head, re.M)
            m = re.match(r"(\d{8})-(\d{6})", p.name)
            when = (f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:8]} "
                    f"{m.group(2)[:2]}:{m.group(2)[2:4]}" if m else "")
            files.append({"name": p.name, "when": when,
                          "to": to.group(1) if to else "",
                          "subject": subj.group(1) if subj else ""})
    return _render("admin.emails", "admin/emails.html", files=files)


@bp_admin.get("/emails/<name>")
def email_view(name):
    _guard()
    if not re.fullmatch(r"[\w.-]+\.html", name):
        abort(404)
    p = settings.OUTBOX_DIR / name
    if not p.exists():
        abort(404)
    return Response(p.read_text(encoding="utf-8"), mimetype="text/html")
