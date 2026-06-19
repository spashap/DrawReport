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
REPORTS_DIR = DATA_DIR / "reports"     # /data/reports/{order_id}/...
DB_PATH = DATA_DIR / "drawreport.sqlite3"

# --- Products & prices (USD) ---
# Product model (same as Golos):
#   snapshot    — up to 3 drawings -> ONE consolidated report; price independent of count
#   development — 2 drawing sets >= 6 months apart (may be "coming soon" at launch)
# All numbers come from config/products.json (future admin). Never hardcode prices.
_PRODUCTS_FILE = BASE_DIR / "config" / "products.json"
_products_cache: "tuple[float, dict] | None" = None


def get_products() -> dict:
    """Read products.json with an mtime cache — edits visible without restart."""
    global _products_cache
    import json
    mtime = _PRODUCTS_FILE.stat().st_mtime
    if _products_cache is None or _products_cache[0] != mtime:
        _products_cache = (mtime, json.loads(_PRODUCTS_FILE.read_text(encoding="utf-8")))
    return _products_cache[1]

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
PALETTE = ""  # css class on <html>: "" = Golden Hour (default), "pu" | "dk" | "cl"

# --- Report generation ---
GEMINI_MAX_ATTEMPTS = 5          # Golos spec §7.2
IMAGE_MAX_LONG_SIDE = 2000       # px, resize before sending to Gemini
UPLOAD_MAX_BYTES = 15 * 1024 * 1024

# --- Worker / email (Resend) ---
WORKER_POLL_SECONDS = 5                # poll period for orders.status='paid'
WORKER_LOG = DATA_DIR / "worker.log"   # UTF-8 worker log (console output stays ASCII!)
MAIL_BACKEND = os.getenv("MAIL_BACKEND", "outbox")   # 'outbox' (files) | 'resend'
OUTBOX_DIR = DATA_DIR / "outbox"       # backend 'outbox': emails as HTML files (dev)
MAIL_FROM_EMAIL = os.getenv("MAIL_FROM_EMAIL", "hello@drawreport.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", SITE_NAME)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_API_URL = os.getenv("RESEND_API_URL", "https://api.resend.com/emails")
RESEND_TIMEOUT = 20                    # seconds per HTTP request to Resend

# --- Auth (Golos spec §9) ---
SESSION_DAYS = 30
LOGIN_CODE_TTL_MINUTES = 30
LOGIN_CODE_RESEND_MINUTES = 10
LOGIN_CODE_MAX_ATTEMPTS = 5
