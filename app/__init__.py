"""Flask app for DrawReport. Single process, server-rendered HTML.
Multi-language via Flask-Babel + /<lang>/ URL prefix (see app/i18n.py).

Blueprints/services are wired in as each phase lands them; create_app stays the
single composition point.
"""
from flask import Flask, g, redirect, render_template, request
from flask_babel import Babel

from app import i18n, track
from app.db import init_db
from config import settings

babel = Babel()


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(settings.BASE_DIR / "static"),
        template_folder=str(settings.BASE_DIR / "templates"),
    )
    app.config["MAX_CONTENT_LENGTH"] = settings.UPLOAD_MAX_BYTES * 3 + 1_000_000
    app.config["BABEL_DEFAULT_LOCALE"] = settings.DEFAULT_LOCALE
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = str(settings.TRANSLATIONS_DIR)
    babel.init_app(app, locale_selector=i18n.select_locale)

    init_db()
    app.before_request(track.before_request)
    app.after_request(track.after_request)

    # Bare "/" -> redirect to the visitor's resolved locale home.
    @app.route("/")
    def root():
        return redirect(f"/{i18n.resolve_locale()}/", code=302)

    from app.routes import bp, bp_root
    app.register_blueprint(bp, url_prefix="/<lang_code>")
    app.register_blueprint(bp_root)  # robots.txt, sitemap.xml at site root
    from app.admin import bp_admin
    app.register_blueprint(bp_admin)  # /admin (own password, English-only)

    @app.teardown_appcontext
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # Persist the active locale in a cookie (so "/" remembers next time).
    @app.after_request
    def remember_locale(resp):
        lang = g.get("lang_code")
        if lang and request.cookies.get(settings.LOCALE_COOKIE) != lang:
            resp.set_cookie(settings.LOCALE_COOKIE, lang,
                            max_age=settings.LOCALE_COOKIE_DAYS * 86400,
                            samesite="Lax")
        return resp

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", code=500), 500

    @app.context_processor
    def inject_globals():
        return {
            "static": "/static",
            "palette": settings.PALETTE,
            "site_name": settings.SITE_NAME,
            "site_domain": settings.SITE_DOMAIN,
            "ga_id": settings.GA_MEASUREMENT_ID,
            "version": settings.APP_VERSION,
            "locale": g.get("lang_code", settings.DEFAULT_LOCALE),
            "locales": settings.LOCALES,
            "public_base_url": settings.PUBLIC_BASE_URL,
            "alt_urls": i18n.alternate_urls,
        }

    return app
