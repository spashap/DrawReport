"""Central config — everything the user sees is configurable here, not hardcoded
in logic (Golos spec law #2). Secrets come from .env (never committed).

DrawReport = US/English fork of Golos Risunka:
  - USD prices, Babel currency/date formatting (no rubles)
  - Google Analytics 4 (replaces Yandex Metrika)
  - PayPal Business (replaces YuKassa) behind the payment abstraction
  - Resend (replaces Unisender) behind the mailer abstraction
  - Multi-language from day one (Flask-Babel, /en/ URL prefix)
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- LLM (report generation) ---
# Provider-agnostic, matching the convention used across the owner's US projects.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")          # 'anthropic' | 'gemini'
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")        # primary model
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "claude-haiku-4-5-20251001")
LLM_MAX_ATTEMPTS = int(os.getenv("LLM_MAX_ATTEMPTS", "5"))     # per-model attempts (Golos §7.2)

# --- LLM (FREE analysis of one drawing) ---
# Its own model knob, separate from the paid report on purpose: the free analysis runs
# once per interested visitor rather than once per sale, so it is the only path where
# model cost is a per-visitor cost. Its own attempt/repair budget for the same reason -
# the parent is waiting on screen, so retries are cheaper to cap here than on the paid
# path where nobody is watching.
FREE_LLM_MODEL = os.getenv("FREE_LLM_MODEL", LLM_MODEL)
FREE_MAX_ATTEMPTS = int(os.getenv("FREE_MAX_ATTEMPTS", "3"))
FREE_REPAIR_ROUNDS = int(os.getenv("FREE_REPAIR_ROUNDS", "2"))
# The two free-analysis limits live in JSON, not in .env, so the owner can change them
# from the admin without a restart or a deploy - the same two-file split as products.json
# (config/ = tracked default, data/ = what the admin writes). See get_free_limits().
#
# They are NOT redundant. The daily cap protects the bill; the per-email cap stops one
# person consuming that daily cap before anyone else arrives. Note what neither can do:
# an email is self-declared and unverified, so a new address is a new quota. The daily cap
# is the only hard guarantee on spend; the per-email cap just makes it harder for one
# person to eat it.
FREE_LIMITS_DEFAULT_FILE = BASE_DIR / "config" / "free_limits.json"
FREE_LIMITS_RUNTIME_FILE = None   # set in the Paths block below (needs DATA_DIR)
_FREE_LIMITS_DEFAULT = {"daily_cap": 200, "per_email_daily": 2}
_free_limits_cache: "tuple[float, dict] | None" = None


def get_free_limits() -> dict:
    """Read free_limits.json with an mtime cache - admin edits are live without a restart.
    Falls back to safe defaults if the file is missing or corrupt: a broken file must not
    mean UNLIMITED spending."""
    global _free_limits_cache
    import json
    path = (FREE_LIMITS_RUNTIME_FILE
            if FREE_LIMITS_RUNTIME_FILE and FREE_LIMITS_RUNTIME_FILE.exists()
            else FREE_LIMITS_DEFAULT_FILE)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return dict(_FREE_LIMITS_DEFAULT)
    if _free_limits_cache is None or _free_limits_cache[0] != mtime:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return dict(_FREE_LIMITS_DEFAULT)
        _free_limits_cache = (mtime, {**_FREE_LIMITS_DEFAULT, **data})
    return _free_limits_cache[1]
# How long an uploaded free drawing is kept before deletion (days). The analysis text and
# the counters stay; only the child's photo goes.
FREE_PHOTO_RETENTION_DAYS = int(os.getenv("FREE_PHOTO_RETENTION_DAYS", "90"))
# FREE_DIR lives in the Paths block below, where DATA_DIR is defined.

# Anthropic (Claude) - default provider
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Gemini - alternate provider (LLM_PROVIDER=gemini); set LLM_MODEL to a gemini id then
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
# Optional proxy base url for the Gemini API (leave empty to call Google directly)
GOOGLE_GEMINI_BASE_URL = os.getenv("GOOGLE_GEMINI_BASE_URL", "")
ADMIN_ALERT_EMAIL = os.getenv("ADMIN_ALERT_EMAIL", "spashap@gmail.com")
# Admin panel /admin: separate password login (NOT mixed with customer /login).
# Empty ADMIN_PASS = admin panel fully disabled (404).
ADMIN_PASS = os.getenv("ADMIN_PASS", "")
# Google Analytics 4 measurement id, e.g. "G-XXXXXXXXXX". Empty = no GA snippet.
# Owner supplies the real id later; placeholder until then.
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "")
# Dev cheat: on localhost this email is shown its login code right on the page.
DEV_LOGIN_CODE_EMAIL = os.getenv("DEV_LOGIN_CODE_EMAIL", "spashap@gmail.com")

# --- Payment (PayPal Business) — see app/payments.py ---
PAYMENT_BACKEND = os.getenv("PAYMENT_BACKEND", "stub")   # 'stub' | 'paypal'
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_ENV = os.getenv("PAYPAL_ENV", "sandbox")          # 'sandbox' | 'live'
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "")

# --- i18n ---
# Active locales. English ships first; add "es", "de", ... here to enable a locale
# (every layer reads this list — routing, hreflang, prompt, content, email).
LOCALES = [s.strip() for s in os.getenv("LOCALES", "en").split(",") if s.strip()]
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "en")
LOCALE_COOKIE = "locale"
LOCALE_COOKIE_DAYS = 365
TRANSLATIONS_DIR = BASE_DIR / "translations"

# --- Paths ---
DATA_DIR = BASE_DIR / "data"
DRAWINGS_DIR = DATA_DIR / "drawings"   # /data/drawings/{order_id}/...
FREE_DIR = DATA_DIR / "free"           # /data/free/{token}.jpg - uploaded free drawings
FREE_LIMITS_RUNTIME_FILE = DATA_DIR / "free_limits.json"   # admin edits (see get_free_limits)
REPORTS_DIR = DATA_DIR / "reports"     # /data/reports/{order_id}/...
DB_PATH = DATA_DIR / "drawreport.sqlite3"

# --- Products & prices (USD) ---
# Product model (same as Golos):
#   snapshot    — up to 3 drawings -> ONE consolidated report; price independent of count
#   development — 2 drawing sets >= 6 months apart (may be "coming soon" at launch)
# All numbers come from products.json (edited in the admin). Never hardcode prices.
#
# TWO files on purpose. config/products.json is the DEFAULT and is tracked in git;
# data/products.json is what the admin writes and is not. Writing admin edits back
# into config/ would put a local modification on a git-tracked file, and the next
# `git pull` in deploy.sh would either refuse to run or silently discard the owner's
# prices. data/ is also the only directory owned by the service user on the server.
PRODUCTS_DEFAULT_FILE = BASE_DIR / "config" / "products.json"
PRODUCTS_RUNTIME_FILE = DATA_DIR / "products.json"
_products_cache: "tuple[float, dict] | None" = None


def get_products() -> dict:
    """Read products.json with an mtime cache — edits visible without restart."""
    global _products_cache
    import json
    path = PRODUCTS_RUNTIME_FILE if PRODUCTS_RUNTIME_FILE.exists() \
        else PRODUCTS_DEFAULT_FILE
    mtime = path.stat().st_mtime
    if _products_cache is None or _products_cache[0] != mtime:
        _products_cache = (mtime, json.loads(path.read_text(encoding="utf-8")))
    return _products_cache[1]


# Admin-controlled blocks appended to the END of a report (upsell by drawing count +
# disclaimers + a free block). Source: config/report_texts.json, edited at
# /admin/report-texts. The job picks the upsell/disclaimer by drawing count; empty = hidden.
# Same two-file split as products.json above: config/ is the tracked default, data/ is
# what the admin writes (see PRODUCTS_RUNTIME_FILE for why).
REPORT_TEXTS_DEFAULT_FILE = BASE_DIR / "config" / "report_texts.json"
REPORT_TEXTS_RUNTIME_FILE = DATA_DIR / "report_texts.json"
_report_texts_cache: "tuple[float, dict] | None" = None
# Safe defaults so a render never crashes if the file is missing/corrupt.
_REPORT_TEXTS_DEFAULT = {
    "upsell": {"1": "", "2": "", "3": ""},
    "disclaimer_main": "",
    "disclaimer_by_count": {"1": "", "2": "", "3": ""},
    "free_text": "",
}


def get_report_texts() -> dict:
    """Read report_texts.json with an mtime cache — admin edits visible without restart.
    Returns safe empty defaults if the file is missing/corrupt (a report still renders)."""
    global _report_texts_cache
    import json
    path = REPORT_TEXTS_RUNTIME_FILE if REPORT_TEXTS_RUNTIME_FILE.exists() \
        else REPORT_TEXTS_DEFAULT_FILE
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return dict(_REPORT_TEXTS_DEFAULT)
    if _report_texts_cache is None or _report_texts_cache[0] != mtime:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return dict(_REPORT_TEXTS_DEFAULT)
        _report_texts_cache = (mtime, data)
    return _report_texts_cache[1]

# --- Site ---
SITE_NAME = "DrawReport"
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "drawreport.com")
CURRENCY = "USD"
CURRENCY_SYMBOL = "$"
# Version: single source = the VERSION file (major.minor, minor 3 digits).
# Minor bumped before EVERY git push (scripts/bump_version.py); major only by owner.
try:
    APP_VERSION = (BASE_DIR / "VERSION").read_text(encoding="utf-8").strip()
except OSError:
    APP_VERSION = "0.000"
# Base url for links in emails (becomes https://drawreport.com on the VPS).
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000")
# The version badge in the page footer is a DEV aid - "V0.031" under the disclaimer reads
# to a visiting parent like unfinished software. It is derived rather than configured so
# nobody has to remember to set it: the base url already distinguishes the two worlds, and
# a build that forgets to flip a flag would show the badge in production, which is the
# failure that matters. SHOW_VERSION=1 in .env forces it on when debugging a live box.
SHOW_VERSION = os.getenv("SHOW_VERSION", "").strip().lower() in ("1", "true", "yes") or \
    any(h in PUBLIC_BASE_URL for h in ("localhost", "127.0.0.1"))
PALETTE = ""  # css class on <html>: "" = Golden Hour (default), "pu" | "dk" | "cl"

# --- Report generation ---
GEMINI_MAX_ATTEMPTS = 5          # Golos spec §7.2
IMAGE_MAX_LONG_SIDE = 2000       # px, resize before sending to Gemini
UPLOAD_MAX_BYTES = 15 * 1024 * 1024

# --- Worker / email (Resend) ---
WORKER_POLL_SECONDS = 5                # poll period for orders.status='paid'
WORKER_LOG = DATA_DIR / "worker.log"   # UTF-8 worker log (console output stays ASCII!)
MAIL_BACKEND = os.getenv("MAIL_BACKEND", "outbox")   # 'outbox' (files) | 'smtp' | 'resend'
OUTBOX_DIR = DATA_DIR / "outbox"       # backend 'outbox': emails as HTML files (dev)
MAIL_FROM_EMAIL = os.getenv("MAIL_FROM_EMAIL", "hello@drawreport.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", SITE_NAME)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_API_URL = os.getenv("RESEND_API_URL", "https://api.resend.com/emails")
RESEND_TIMEOUT = 20                    # seconds per HTTP request to Resend

# SMTP - the PORTABLE backend. Any provider (Brevo, SES, ZeptoMail, Zoho) is a config
# change rather than a new code path, which matters because free tiers move and the
# provider that fits today may not next year.
# Port decides the encryption: 465 = implicit TLS, anything else (587) = STARTTLS.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_TIMEOUT = 30                      # seconds per SMTP conversation

# --- Auth (Golos spec §9) ---
SESSION_DAYS = 30
LOGIN_CODE_TTL_MINUTES = 30
LOGIN_CODE_RESEND_MINUTES = 10
LOGIN_CODE_MAX_ATTEMPTS = 5
