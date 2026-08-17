"""Analytics: anonymous visitor cookie, VISIT (30 min), first/last-touch UTM, channel.

Three levels of identity, and they must not be confused:
  * `visitor_id` (cookie dr_v, one year) - a person. Answers "how many different people".
  * `visit_id`   (cookie dr_s, 30 sliding minutes) - a session. Answers "what did this
    person do in one sitting"; only this makes the funnel NESTED and its steps ordered.
    Without visits a "funnel" is one set of unique visitors divided by another, where a
    later step can come out larger than the one before it.
  * first-touch `utm` (cookie dr_utm, one year) - how the person FIRST heard of us;
    the UTM/gclid of the current visit is what brought them RIGHT NOW. For paid traffic
    the second one decides: the purchase comes from the last click, while the first
    touch may have been organic six months ago.

GA4 (client-side) is separate (templates/_analytics.html); this module is the
first-party data that feeds the /admin dashboards.
"""
from __future__ import annotations

import json
import secrets

from flask import g, request

VISITOR_COOKIE = "dr_v"
VISIT_COOKIE = "dr_s"
UTM_COOKIE = "dr_utm"
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")
COOKIE_MAX_AGE = 365 * 24 * 3600
VISIT_MAX_AGE = 30 * 60          # visit window; extended on every request

# Paths that are NOT a page view: beacons, polling, static, service endpoints.
# Counting them as "pages of the visit" would declare waiting for a report to be
# active reading. Matched after the /<lang>/ prefix is stripped (see _bare_path).
NON_PAGE_PREFIXES = ("/static/", "/t/e", "/track/", "/free/status/", "/free/img/",
                     "/pay/", "/cabinet/drawing/", "/admin",
                     "/favicon.ico", "/robots.txt", "/sitemap.xml")

# Search engines and social networks, for classifying the channel by referer.
_SEARCH_HOSTS = ("google.", "bing.com", "duckduckgo.com", "search.", "yahoo.",
                 "ecosia.org", "brave.com", "startpage.com", "baidu.com", "yandex.")
_SOCIAL_HOSTS = ("facebook.", "instagram.", "t.co", "twitter.", "x.com", "reddit.",
                 "pinterest.", "youtube.", "tiktok.", "linkedin.", "threads.net",
                 "t.me", "telegram", "whatsapp.", "quora.com", "substack.com")
# Ad markers. gclid/fbclid are set by the ad platform itself, so they are the exact
# "this was advertising" signal.
_AD_MEDIUMS = ("cpc", "ppc", "paid", "cpm", "banner", "ads", "display", "retargeting")


def _clean(v: str | None, limit: int = 120) -> str | None:
    return v.strip()[:limit] if v and v.strip() else None


def _bare_path(path: str | None = None) -> str:
    """Path with the /<lang>/ prefix stripped, so the prefix lists below stay
    language-independent. '/en/free/status/x' -> '/free/status/x'."""
    p = path if path is not None else request.path
    from config import settings
    for code in settings.LOCALES:
        if p == f"/{code}":
            return "/"
        if p.startswith(f"/{code}/"):
            return p[len(code) + 1:]
    return p


def classify_channel(utm: dict | None, click_id: str | None,
                     referer: str | None) -> str:
    """Channel of the visit. Check order = order of how trustworthy the signal is."""
    if click_id:
        return "ads"
    if utm:
        medium = (utm.get("utm_medium") or "").lower()
        source = (utm.get("utm_source") or "").lower()
        if medium in _AD_MEDIUMS:
            return "ads"
        if any(s in source for s in ("facebook", "instagram", "tiktok", "pinterest",
                                     "reddit", "twitter", "linkedin")):
            return "social"
        if medium in ("email", "newsletter"):
            return "email"
        return "utm"
    if not referer:
        return "direct"
    host = referer.split("//", 1)[-1].split("/", 1)[0].lower()
    from config import settings
    if settings.SITE_DOMAIN and settings.SITE_DOMAIN in host:
        return "internal"
    if any(s in host for s in _SEARCH_HOSTS):
        return "organic"
    if any(s in host for s in _SOCIAL_HOSTS):
        return "social"
    return "referral"


def before_request() -> None:
    """Assigns visitor_id/visit_id, captures first-touch UTM and this visit's tags."""
    g.visitor_id = request.cookies.get(VISITOR_COOKIE) or secrets.token_urlsafe(12)
    g.new_visitor = VISITOR_COOKIE not in request.cookies

    # Visit: the cookie is short-lived, so its ABSENCE is itself the signal of a new
    # session - no timestamps and no server-side time comparison needed.
    g.visit_id = request.cookies.get(VISIT_COOKIE) or secrets.token_urlsafe(9)
    g.new_visit = VISIT_COOKIE not in request.cookies

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
    # Tags of THIS visit (last touch) - kept apart from the first touch.
    g.utm_now = utm_in_url or None
    g.click_id = _clean(request.args.get("gclid") or request.args.get("fbclid")
                        or request.args.get("msclkid"), 64)


def _is_page_view(response) -> bool:
    """An HTML page served successfully. Beacons, images and polling are not pages."""
    if response.status_code >= 400 or response.status_code in (301, 302, 303, 307, 308):
        return False
    if _bare_path().startswith(NON_PAGE_PREFIXES):
        return False
    return (response.mimetype or "").startswith("text/html")


def after_request(response):
    if getattr(g, "new_visitor", False):
        response.set_cookie(VISITOR_COOKIE, g.visitor_id, max_age=COOKIE_MAX_AGE,
                            httponly=True, samesite="Lax")
    if getattr(g, "utm_is_new", False) and g.utm:
        response.set_cookie(UTM_COOKIE, json.dumps(g.utm, ensure_ascii=False),
                            max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax")
    # The visit cookie is refreshed on EVERY request: 30 minutes of inactivity = a new
    # visit. Static is skipped entirely: one page pulls a dozen files, and each of them
    # would write a timestamp to the database without making the visit any more alive.
    bare = _bare_path()
    if (getattr(g, "visit_id", None) and not bare.startswith("/admin")
            and not bare.startswith(("/static/", "/favicon"))):
        response.set_cookie(VISIT_COOKIE, g.visit_id, max_age=VISIT_MAX_AGE,
                            httponly=True, samesite="Lax")
        try:
            _touch_visit(page=_is_page_view(response))
        except Exception:          # analytics never breaks the response
            pass
    return response


def _touch_visit(page: bool) -> None:
    """Creates/updates the visit row. Geo and channel are resolved ONCE, at creation."""
    from app import geoip
    from app.db import get_db, now
    db = get_db()
    if not getattr(g, "new_visit", False) and not page:
        # Existing visit and not a page (beacon/polling) - just a timestamp.
        db.execute("UPDATE web_visits SET last_at = ? WHERE visit_id = ?",
                   (now(), g.visit_id))
        db.commit()
        return
    path = request.path[:200]
    if getattr(g, "new_visit", False):
        geo = geoip.lookup(client_ip()) or {}
        ref = _clean(request.referrer, 300)
        utm_now = getattr(g, "utm_now", None)
        click_id = getattr(g, "click_id", None)
        db.execute(
            "INSERT INTO web_visits (visit_id, visitor_id, started_at, last_at,"
            " entry_path, exit_path, pages, device, channel, utm_json, gclid, referer,"
            " geo_country, geo_region)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(visit_id) DO NOTHING",
            (g.visit_id, g.visitor_id, now(), now(), path, path, 1 if page else 0,
             parse_device(request.user_agent.string if request else None),
             classify_channel(utm_now, click_id, ref),
             json.dumps(utm_now, ensure_ascii=False) if utm_now else None,
             click_id, ref, geo.get("country"), geo.get("region")))
        g.new_visit = False        # no second INSERT within the same request
    else:
        db.execute(
            "UPDATE web_visits SET last_at = ?, exit_path = ?, pages = pages + ?"
            " WHERE visit_id = ?", (now(), path, 1 if page else 0, g.visit_id))
    db.commit()


def mark_visit(**fields) -> None:
    """Updates fields of the current visit (engaged / max_scroll / screen_w / customer_id).

    max_scroll goes through MAX(): beacons arrive in arbitrary order, and writing "25"
    after "75" must not roll the depth back.
    """
    if not getattr(g, "visit_id", None) or not fields:
        return
    allowed = {"engaged", "max_scroll", "screen_w", "is_touch", "customer_id"}
    sets, params = [], []
    for k, v in fields.items():
        if k not in allowed or v is None:
            continue
        sets.append(f"{k} = MAX(COALESCE({k}, 0), ?)" if k == "max_scroll" else f"{k} = ?")
        params.append(v)
    if not sets:
        return
    try:
        from app.db import get_db
        db = get_db()
        db.execute(f"UPDATE web_visits SET {', '.join(sets)} WHERE visit_id = ?",
                   (*params, g.visit_id))
        db.commit()
    except Exception:              # analytics never breaks the request
        pass


# Bot markers in the User-Agent (lower-case). Layered defences:
#  1) "+http"/"+https" - a self-identifying crawler/monitor (Pingdom, leakix, Claude-User...);
#  2) no "mozilla" - a utility/scanner (curl, wget, scanners), not a browser;
#  3) an explicit name list - for bots that send a browser-like UA without a self URL.
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
    """Device from the User-Agent; bots/scanners/utilities are marked 'bot'.
    Bots land in device='bot' and are filtered out of the admin analytics (humans only)."""
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
        return fwd.split(",")[0].strip()   # first hop = the client
    return request.remote_addr


def track_event(event_type: str, payload: dict | None = None,
                customer_id: int | None = None, path: str | None = None) -> None:
    """`path` is overridden by beacons: the click arrives at /t/e but happened on a page
    the browser reports itself - otherwise every goal on the site looks like an event
    on /t/e."""
    from app import geoip
    from app.db import track
    ua = request.user_agent.string if request else None
    geo = geoip.lookup(client_ip()) or {}
    track(event_type,
          visitor_id=getattr(g, "visitor_id", None),
          visit_id=getattr(g, "visit_id", None),
          customer_id=customer_id,
          payload=payload,
          path=(path or (request.path[:200] if request else None)),
          utm=getattr(g, "utm", None),
          user_agent=(ua or None),
          device=parse_device(ua),
          referer=(request.referrer if request else None),
          geo_country=geo.get("country"),
          geo_region=geo.get("region"))
    if customer_id:
        mark_visit(customer_id=customer_id)
