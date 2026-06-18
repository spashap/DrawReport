"""Main (locale-prefixed) blueprint: every public page lives at /<locale>/... .

Phase 3 ships the landing, sample pages, hosted report rendering, robots/sitemap.
Order flow, auth, cabinet, blog, legal land in later phases (stubs for now).
"""
from __future__ import annotations

import datetime
import json

from flask import (Blueprint, Response, abort, g, render_template, request)
from flask_babel import gettext as _

from app.content import get_faq, get_testimonials
from app.samples import get_sample_by_token, get_samples
from config import settings
from pipeline.render import REPORT_STRINGS, drawing_to_data_uri, format_report_date
from pipeline.schema import validate_report

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

@bp.route("/order")
def order():
    return render_template("stub.html", title=_("Place an order"))


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
