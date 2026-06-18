"""Locale handling for DrawReport — Flask-Babel + /<lang>/ URL prefix.

Resolver order for the bare '/' redirect: cookie -> Accept-Language -> default.
Inside a localized request the locale comes from the URL prefix (g.lang_code),
which the main blueprint auto-injects back into url_for via url_defaults.

Business logic must NEVER branch on `if locale == "en"`; only data/content
(prompt, catalog, products text, email) differs by locale.
"""
from flask import g, request, url_for

from config import settings


def is_active(locale) -> bool:
    return bool(locale) and locale in settings.LOCALES


def resolve_locale() -> str:
    """Pick a locale for a visitor with no locale in the URL (the '/' redirect)."""
    cookie = request.cookies.get(settings.LOCALE_COOKIE)
    if is_active(cookie):
        return cookie
    best = request.accept_languages.best_match(settings.LOCALES)
    return best or settings.DEFAULT_LOCALE


def select_locale() -> str:
    """Babel locale selector — uses the URL-prefix locale stored on g."""
    lang = g.get("lang_code", None)
    return lang if is_active(lang) else settings.DEFAULT_LOCALE


def alternate_urls() -> dict:
    """{locale: absolute_url} for the current page in every active locale (hreflang)."""
    out = {}
    rule = request.url_rule
    if rule is None or "lang_code" not in (rule.arguments or set()):
        return out
    args = dict(request.view_args or {})
    for loc in settings.LOCALES:
        a = dict(args)
        a["lang_code"] = loc
        try:
            out[loc] = settings.PUBLIC_BASE_URL.rstrip("/") + url_for(rule.endpoint, **a)
        except Exception:
            pass
    return out
