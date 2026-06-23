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

from app import geoip, jobs
from app.db import get_db
from config import settings

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")

ADMIN_COOKIE = "dr_a"

SECTIONS = [
    ("admin.analytics", "Analytics"),
    ("admin.visits", "Visits"),
    ("admin.actions", "Actions"),
    ("admin.orders", "Orders"),
    ("admin.clients", "Clients"),
    ("admin.coupons", "Coupons"),
    ("admin.site_settings", "Site settings"),
    ("admin.report_texts", "Report texts"),
    ("admin.emails", "Emails"),
]

FUNNEL_STEPS = [
    ("landing_view", "Landing"),
    ("engaged", "Engaged (scroll/15s)"),
    ("sample_view", "Viewed samples"),
    ("order_form_view", "Opened the form"),
    ("form_started", "Started filling"),
    ("order_created", "Created an order"),
    ("checkout_view", "Reached checkout"),
    ("order_paid", "Paid"),
    ("report_delivered", "Got the report"),
]

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

    ftypes = [ev for ev, _ in FUNNEL_STEPS]
    ph = ",".join("?" * len(ftypes))
    counts = {r["type"]: r["c"] for r in db.execute(
        "SELECT type, COUNT(DISTINCT COALESCE(visitor_id, 'c' || customer_id)) c FROM events"
        f" WHERE type IN ({ph}) AND {NOT_BOT} AND created_at >= ?{eng} GROUP BY type",
        (*ftypes, since, *eng_p))}
    fmembers = {}
    for row in db.execute(
            "SELECT type, COALESCE(visitor_id, 'c' || customer_id) who, visitor_id,"
            " MAX(geo_country) gc, MAX(geo_region) gr, MAX(device) dev,"
            " MAX(customer_id) cid, MAX(created_at) last FROM events"
            f" WHERE type IN ({ph}) AND {NOT_BOT} AND created_at >= ?{eng}"
            " GROUP BY type, who ORDER BY last DESC", (*ftypes, since, *eng_p)):
        lst = fmembers.setdefault(row["type"], [])
        if len(lst) < DRILL_CAP:
            lst.append(_drill_member(row))
    funnel, prev = [], None
    for ev, label in FUNNEL_STEPS:
        n = counts.get(ev, 0)
        funnel.append({
            "label": label, "n": n, "type": ev, "members": fmembers.get(ev, []),
            "pct_prev": f"{n / prev * 100:.0f}%" if prev else "",
            "pct_top": (f"{n / funnel[0]['n'] * 100:.1f}%" if funnel and funnel[0]["n"] else ""),
        })
        prev = n or None

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
                   kpi=kpi, funnel=funnel, sources=sources_view, events=events_view,
                   bots=bots, humans=humans, engaged=engaged, landing_only=landing_only,
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
    visitors_view = [{
        "id": (r["visitor_id"] or "")[:10], "device": r["device"] or "-",
        "utm": _utm_label(r["utm_json"]), "referer": (r["referer"] or "")[:60] or "(direct)",
        "events": r["n"], "engaged": bool(r["engaged"]),
        "customer": f"c{r['customer_id']}" if r["customer_id"] else "",
        "geo": geoip.geo_label(r["geo_country"], r["geo_region"]),
        "first": r["first_seen"][:16].replace("T", " "),
        "last": r["last_seen"][:16].replace("T", " "),
    } for r in rows]

    total = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events"
        f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND created_at >= ?", (since,)).fetchone()["c"]
    engaged = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events"
        f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND type = 'engaged' AND created_at >= ?",
        (since,)).fetchone()["c"]
    bounce = f"{(total - engaged) / total * 100:.0f}%" if total else "-"
    return _render("admin.visits", "admin/visits.html",
                   days=days, periods=PERIODS, show=show, devices=devices_view,
                   sources=sources, geo=geo_view, visitors=visitors_view,
                   total=total, engaged=engaged, bounce=bounce)


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
                   summary=summary_view, total=total, recent=recent_view)


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
    _guard()
    path = settings.BASE_DIR / "config" / "products.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for code, p in data.items():
        f = lambda k: request.form.get(f"{code}_{k}", "").strip()
        p["enabled"] = bool(request.form.get(f"{code}_enabled"))
        if f("title"):
            p["title"] = f("title")
        p["subtitle"] = f("subtitle")
        try:
            p["price_usd"] = int(f("price_usd"))
            old = f("old_price_usd")
            if old:
                p["old_price_usd"] = int(old)
            else:
                p.pop("old_price_usd", None)
        except ValueError:
            return redirect(url_for("admin.site_settings", saved="err"))
        p["features"] = [ln.strip() for ln in
                         request.form.get(f"{code}_features", "").splitlines() if ln.strip()]
    if not any(p["enabled"] for p in data.values()):
        return redirect(url_for("admin.site_settings", saved="err"))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
    """Overwrite config/report_texts.json. Empty field = block not rendered in the report."""
    _guard()
    path = settings.BASE_DIR / "config" / "report_texts.json"
    g = lambda k: request.form.get(k, "").strip()
    data = {
        "upsell": {n: g(f"upsell_{n}") for n in ("1", "2", "3")},
        "disclaimer_main": g("disclaimer_main"),
        "disclaimer_by_count": {n: g(f"disclaimer_by_count_{n}") for n in ("1", "2", "3")},
        "free_text": g("free_text"),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
