"""Main (locale-prefixed) blueprint: every public page lives at /<locale>/... .

Phase 3 ships the landing, sample pages, hosted report rendering, robots/sitemap.
Order flow, auth, cabinet, blog, legal land in later phases (stubs for now).
"""
from __future__ import annotations

import datetime
import json

from flask import (Blueprint, Response, abort, g, redirect, render_template,
                   request, url_for)
from flask_babel import gettext as _

from app.content import get_faq, get_testimonials
from app.db import get_db
from app.orders import FormError, validate_and_create_order
from app.payments import create_payment, mark_paid
from app.samples import get_sample_by_token, get_samples
from app.track import track_event
from config import settings
from config.form_fields import child_fields, coupon_field, drawing_fields, email_field
from pipeline.render import REPORT_STRINGS, drawing_to_data_uri, format_report_date
from pipeline.schema import validate_report

MONTHS_EN = [("01", "January"), ("02", "February"), ("03", "March"), ("04", "April"),
             ("05", "May"), ("06", "June"), ("07", "July"), ("08", "August"),
             ("09", "September"), ("10", "October"), ("11", "November"), ("12", "December")]

bp = Blueprint("main", __name__)
# Root (non-locale) blueprint: robots.txt, sitemap.xml live at the site root.
bp_root = Blueprint("root", __name__)


@bp.url_value_preprocessor
def pull_lang(endpoint, values):
    """Pop the URL-prefix locale into g and 404 on an inactive locale."""
    lang = (values.pop("lang_code", None) if values else None) or settings.DEFAULT_LOCALE
    if lang not in settings.LOCALES:
        abort(404)
    g.lang_code = lang


@bp.url_defaults
def add_lang(endpoint, values):
    """Auto-inject the active locale into url_for('main.*') calls."""
    if not endpoint.startswith("main."):
        return
    if "lang_code" in values:
        return
    values["lang_code"] = g.get("lang_code") or settings.DEFAULT_LOCALE


# --- Landing ---------------------------------------------------------------

_css_cache: "tuple[tuple[float, float], str] | None" = None


def _inline_css() -> str:
    """Critical landing CSS inlined (spec §4.2). Cache by mtime: edits show without
    a restart."""
    global _css_cache
    css_dir = settings.BASE_DIR / "static" / "css"
    files = (css_dir / "tokens.css", css_dir / "components.css")
    stamp = tuple(f.stat().st_mtime for f in files)
    if _css_cache is None or _css_cache[0] != stamp:
        _css_cache = (stamp, "".join(f.read_text(encoding="utf-8") for f in files))
    return _css_cache[1]


def _schema_jsonld(locale: str, min_price) -> str:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    org = {
        "@context": "https://schema.org", "@type": "Organization",
        "name": settings.SITE_NAME, "url": base + "/",
        "logo": f"{base}/static/img/og-default.png",
        "description": ("Educational analysis of a child's drawing from a photo: a personal "
                        "report on what the drawing shows about the child - strengths, interests "
                        "and skills - grounded in the developmental stages of children's art. "
                        "Not a diagnosis."),
        "knowsLanguage": locale,
    }
    website = {"@context": "https://schema.org", "@type": "WebSite",
               "name": settings.SITE_NAME, "url": base + "/", "inLanguage": locale}
    product = {
        "@context": "https://schema.org", "@type": "Product",
        "name": "A personal report on your child's drawings",
        "description": ("A warm, personal PDF report on a child's drawings: strengths, how they "
                        "work with color, form and detail, and what you can support at home. "
                        "7 areas of development with scores and plain-language explanations. "
                        "Educational observation, not a diagnosis."),
        "brand": {"@type": "Brand", "name": settings.SITE_NAME},
        "offers": [
            {"@type": "Offer", "name": p["title"],
             "price": p["price_usd"], "priceCurrency": settings.CURRENCY,
             "url": f"{base}/{locale}/order?product={code}",
             "availability": "https://schema.org/InStock"}
            for code, p in settings.get_products().items() if p["enabled"]
        ],
    }
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}}
                       for q, a in get_faq(locale)],
    }
    return json.dumps([org, website, product, faq], ensure_ascii=False)


@bp.get("/")
def index():
    locale = g.lang_code
    track_event("landing_view")
    products = settings.get_products()
    min_price = min(p["price_usd"] for p in products.values() if p["enabled"])
    return render_template(
        "landing.html",
        products=products,
        samples=get_samples(locale),
        faq=get_faq(locale),
        testimonials=get_testimonials(locale),
        blog_posts=[],  # wired in Phase 7
        min_price=min_price,
        inline_css=_inline_css(),
        schema_jsonld=_schema_jsonld(locale, min_price),
    )


# --- Samples + hosted reports ---------------------------------------------

def _render_report_page(report_data: dict, drawing_specs: list[dict], locale: str):
    """Render the full hosted report (with site header) via Flask render_template,
    so url_for/gettext work. drawing_specs: [{"path": Path, "caption": str}, ...].
    Reused for samples now and DB-backed order reports in Phase 5."""
    report = validate_report(report_data)
    drawings = [{"src": drawing_to_data_uri(d["path"]), "caption": d["caption"]}
                for d in drawing_specs]
    return render_template(
        "report.html", report=report, drawings=drawings,
        s=REPORT_STRINGS.get(locale, REPORT_STRINGS[settings.DEFAULT_LOCALE]),
        generated_date=format_report_date(datetime.date.today(), locale),
        locale=locale, site_header=True,
    )


@bp.get("/sample/<token>")
def sample(token):
    """Indexable example page (SEO). The full report document lives at /r/<token>."""
    s = get_sample_by_token(token, g.lang_code)
    if s is None:
        abort(404)
    return render_template("sample.html", s=s)


@bp.get("/r/<token>")
def hosted_report(token):
    """Full hosted report. Samples now; DB-backed order reports add in Phase 5."""
    s = get_sample_by_token(token, g.lang_code)
    if s is not None:
        data = json.loads(s.report_path.read_text(encoding="utf-8"))
        # the sample's drawing sits next to its report under the matching def
        from app.samples import _SAMPLE_DEFS  # local: small internal lookup
        sd = next((d for d in _SAMPLE_DEFS.get(g.lang_code, []) if d["token"] == token), None)
        drawing = settings.BASE_DIR / sd["drawing"] if sd else None
        specs = [{"path": drawing, "caption": s.caption}] if drawing else []
        return _render_report_page(data, specs, g.lang_code)
    abort(404)


# --- Stubs: real implementations land in later phases ---------------------

# --- Order flow ------------------------------------------------------------

def _render_order_form(values, errors, status=200):
    locale = g.lang_code
    products = settings.get_products()
    code = (request.args.get("product") or values.get("product") or "snapshot")
    if code not in products or not products[code]["enabled"]:
        code = "snapshot"
    import datetime
    html = render_template(
        "order.html",
        product_code=code, product=products[code],
        drawings_max=products[code]["drawings_max"],
        child_fields=child_fields(locale), drawing_fields=drawing_fields(locale),
        email_field=email_field(locale), coupon_field=coupon_field(locale),
        months=MONTHS_EN, current_year=datetime.date.today().year,
        values=values, errors=errors,
    )
    return (html, status)


@bp.get("/order")
def order():
    track_event("order_form_view", {"product": request.args.get("product", "snapshot")})
    return _render_order_form(values={}, errors={})


@bp.post("/order")
def order_submit():
    files = [request.files[f"d{i}_file"] for i in (1, 2, 3)
             if request.files.get(f"d{i}_file") and request.files[f"d{i}_file"].filename]
    try:
        order_id = validate_and_create_order(
            request.form, files,
            visitor_id=getattr(g, "visitor_id", None),
            utm=getattr(g, "utm", None), locale=g.lang_code,
        )
    except FormError as e:
        track_event("order_form_errors", {"fields": list(e.errors)})
        return _render_order_form(values=request.form.to_dict(), errors=e.errors, status=400)
    track_event("order_created", {"order_id": order_id, "drawings": len(files)})
    order = get_db().execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return redirect(create_payment(order_id, order["price_cents"]))


@bp.get("/pay/stub/<int:order_id>")
def stub_checkout(order_id):
    order = get_db().execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        abort(404)
    track_event("checkout_view", {"order_id": order_id})
    product = settings.get_products()[order["product_code"]]
    return render_template("checkout_stub.html", order=order, product=product)


@bp.post("/pay/stub/<int:order_id>/confirm")
def stub_confirm(order_id):
    """Stub analogue of the PayPal webhook: single mark_paid point (idempotent)."""
    result = mark_paid(order_id)
    if result is None:
        abort(404)
    if not result["already_paid"]:
        track_event("order_paid", {"order_id": order_id}, customer_id=result["customer_id"])
    resp = redirect(url_for("main.order_success", order_id=order_id))
    if result["session_token"]:
        from app.auth import SESSION_COOKIE
        resp.set_cookie(SESSION_COOKIE, result["session_token"],
                        max_age=settings.SESSION_DAYS * 24 * 3600,
                        httponly=True, samesite="Lax")
    return resp


@bp.get("/order/success/<int:order_id>")
def order_success(order_id):
    order = get_db().execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        abort(404)
    return render_template("order_success.html", email=order["email"])


# --- First-party analytics beacon -----------------------------------------

_GOAL_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_:-")


@bp_root.post("/t/e")
def track_beacon():
    """First-party beacon (navigator.sendBeacon). Cheap, anonymous, never errors.
    Lives at the site root (no locale prefix) - matches the JS in _analytics.html."""
    if request.form.get("engaged") or request.args.get("engaged"):
        track_event("engaged")
        return ("", 204)
    goal = (request.form.get("g") or request.args.get("g") or "").strip().lower()
    if goal and len(goal) <= 64 and set(goal) <= _GOAL_CHARS:
        track_event("click:" + goal)
    return ("", 204)


@bp.route("/login")
def login():
    return render_template("stub.html", title=_("Log in"))


@bp.route("/cabinet")
def cabinet():
    return render_template("stub.html", title=_("Your account"))


@bp.route("/blog")
def blog_index():
    return render_template("stub.html", title=_("Blog"))


@bp.route("/blog/<slug>")
def blog_post(slug):
    return render_template("stub.html", title=_("Blog"))


@bp.route("/legal/<page>")
def legal(page):
    return render_template("stub.html", title=_("Legal"))


# --- Root (non-locale) routes: robots + sitemap ---------------------------

SEO_DISALLOW = ["/admin", "/cabinet", "/r/", "/order"]


@bp_root.get("/robots.txt")
def robots():
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    lines = ["User-agent: *", "Allow: /",
             *(f"Disallow: {d}" for d in SEO_DISALLOW),
             "", f"Sitemap: {base}/sitemap.xml", ""]
    return Response("\n".join(lines), mimetype="text/plain")


@bp_root.get("/sitemap.xml")
def sitemap():
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    today = datetime.date.today().isoformat()
    items = []
    for loc in settings.LOCALES:
        paths = [("/", "1.0"), ("/blog", "0.7"),
                 ("/legal/privacy", "0.2"), ("/legal/terms", "0.2"),
                 ("/legal/refund", "0.2")]
        paths += [(f"/sample/{s.token}", "0.8") for s in get_samples(loc)]
        for path, prio in paths:
            items.append(f"<url><loc>{base}/{loc}{path}</loc>"
                         f"<lastmod>{today}</lastmod><priority>{prio}</priority></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(items) + "\n</urlset>")
    return Response(xml, mimetype="application/xml")
