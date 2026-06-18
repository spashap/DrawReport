"""Analytics for the admin dashboards: anonymous visitor cookie + first-touch UTM.

Server-side events feed the funnel:
  landing_view -> sample_view -> order_form_view -> order_created
              -> checkout_view -> order_paid -> report_delivered.
GA4 (client-side) is separate (templates/_analytics.html).
"""
from __future__ import annotations

import json
import secrets

from flask import g, request

VISITOR_COOKIE = "dr_v"
UTM_COOKIE = "dr_utm"
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")
COOKIE_MAX_AGE = 365 * 24 * 3600


def before_request() -> None:
    """Assign visitor_id and capture first-touch UTM (persisted in after_request)."""
    g.visitor_id = request.cookies.get(VISITOR_COOKIE) or secrets.token_urlsafe(12)
    g.new_visitor = VISITOR_COOKIE not in request.cookies

    utm_in_url = {k: request.args.get(k) for k in UTM_KEYS if request.args.get(k)}
    stored = request.cookies.get(UTM_COOKIE)
    if stored:
        try:
            g.utm = json.loads(stored)
        except ValueError:
            g.utm = None
    else:
        g.utm = utm_in_url or None
    g.utm_is_new = bool(utm_in_url) and not stored


def after_request(response):
    if getattr(g, "new_visitor", False):
        response.set_cookie(VISITOR_COOKIE, g.visitor_id, max_age=COOKIE_MAX_AGE,
                            httponly=True, samesite="Lax")
    if getattr(g, "utm_is_new", False) and g.utm:
        response.set_cookie(UTM_COOKIE, json.dumps(g.utm, ensure_ascii=False),
                            max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax")
    return response


# Bot markers in the User-Agent (lower-case). Bots land in device='bot' and are
# filtered out of the admin analytics (humans only).
BOT_UA_MARKERS = (
    "bot", "crawler", "spider", "headless", "slurp", "monitor",
    "scan", "audit", "sniff", "uptime", "pingdom", "pingadmin", "leakix",
    "masscan", "zgrab", "nmap", "nuclei", "wpscan", "sqlmap", "nikto",
    "scrapy", "phantomjs", "selenium", "puppeteer", "playwright",
    "curl", "wget", "python-requests", "urllib", "aiohttp", "httpx",
    "go-http", "okhttp", "java/", "libwww", "httpclient", "node-fetch",
    "gptbot", "chatgpt", "claude", "anthropic", "perplexity", "bytespider",
    "ccbot", "google-extended", "amazonbot", "applebot", "ai2bot",
    "ahrefs", "semrush", "mj12", "dotbot", "dataforseo", "petalbot", "blexbot",
    "facebookexternalhit", "telegrambot", "whatsapp", "twitterbot",
    "linkedinbot", "discordbot", "slackbot", "embedly",
)


def parse_device(ua: str | None) -> str:
    """Device from the User-Agent; bots/scanners/utilities are marked 'bot'."""
    s = (ua or "").lower().strip()
    if not s:
        return "unknown"
    if "+http" in s:                       # self-identifying crawler/monitor
        return "bot"
    if "mozilla" not in s:                 # curl/wget/scanners - not browsers
        return "bot"
    if any(b in s for b in BOT_UA_MARKERS):
        return "bot"
    if "ipad" in s or "tablet" in s or ("android" in s and "mobile" not in s):
        return "tablet"
    if any(m in s for m in ("mobi", "iphone", "ipod", "android", "phone")):
        return "mobile"
    return "desktop"


def client_ip() -> str | None:
    """Real client IP behind nginx (X-Real-IP / X-Forwarded-For). The IP is never
    stored - only used for the geo resolve in track_event()."""
    if not request:
        return None
    real = request.headers.get("X-Real-IP")
    if real:
        return real.strip()
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr


def track_event(event_type: str, payload: dict | None = None,
                customer_id: int | None = None) -> None:
    from app import geoip
    from app.db import track
    ua = request.user_agent.string if request else None
    geo = geoip.lookup(client_ip()) or {}
    track(event_type,
          visitor_id=getattr(g, "visitor_id", None),
          customer_id=customer_id,
          payload=payload,
          utm=getattr(g, "utm", None),
          user_agent=(ua or None),
          device=parse_device(ua),
          referer=(request.referrer if request else None),
          geo_country=geo.get("country"),
          geo_region=geo.get("region"))
