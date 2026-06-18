"""Main (locale-prefixed) blueprint. Registered under url_prefix="/<lang_code>",
so every public page lives at /<locale>/... .

Phase 0 ships only the home placeholder; later phases add the landing, order
flow, cabinet, samples, blog, legal, robots/sitemap on this same blueprint.
"""
from flask import Blueprint, abort, g, render_template
from flask_babel import gettext as _

from config import settings

bp = Blueprint("main", __name__)


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


@bp.route("/")
def index():
    return render_template("landing.html")


# --- Stubs: real implementations land in later phases. Defined now so url_for()
#     resolves everywhere and the nav/links work end to end. ---
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


@bp.route("/sample/<token>")
def sample(token):
    return render_template("stub.html", title=_("Sample report"))


@bp.route("/legal/<page>")
def legal(page):
    return render_template("stub.html", title=_("Legal"))
