"""Main (locale-prefixed) blueprint. Registered under url_prefix="/<lang_code>",
so every public page lives at /<locale>/... .

Phase 0 ships only the home placeholder; later phases add the landing, order
flow, cabinet, samples, blog, legal, robots/sitemap on this same blueprint.
"""
from flask import Blueprint, abort, g, render_template

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
