"""SQLite layer: stdlib sqlite3, no ORM (Golos simplicity rule). Schema = Golos
spec §5 adapted for DrawReport: price in USD cents, generic payment_id (PayPal),
per-order locale (the report is generated in the order's language).
"""
from __future__ import annotations

import datetime
import json
import secrets
import sqlite3

from flask import g

from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS children (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    name TEXT NOT NULL,
    gender TEXT,                          -- 'f' / 'm' (authoritative source of gender)
    birth_ym TEXT,                        -- 'YYYY-MM' (age computed at the drawing date)
    birth_info TEXT,                      -- as entered by the parent
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,                  -- from the form; customer created on payment
    customer_id INTEGER REFERENCES customers(id),
    child_id INTEGER REFERENCES children(id),
    product_code TEXT NOT NULL,           -- 'snapshot' / 'development'
    price_cents INTEGER NOT NULL,         -- USD cents
    coupon_code TEXT,
    locale TEXT NOT NULL DEFAULT 'en',    -- report + email language
    status TEXT NOT NULL DEFAULT 'created',
        -- created / paid / generating / failed / delivered / insufficient
    payment_id TEXT,                      -- provider order/payment id (PayPal)
    base_order_id INTEGER REFERENCES orders(id),  -- Development: the order it builds on
    child_json TEXT,                      -- child data from the form (before child row)
    visitor_id TEXT,                      -- analytics: who bought
    utm_json TEXT,                        -- first-touch UTM at order time
    created_at TEXT NOT NULL,
    paid_at TEXT
);
CREATE TABLE IF NOT EXISTS drawings (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    file_path TEXT NOT NULL,
    drawn_at TEXT,                        -- 'YYYY-MM' (required in the form)
    context_json TEXT,                    -- all form fields for this drawing
    uploaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    html_path TEXT,
    pdf_path TEXT,
    report_json_path TEXT,                -- raw Gemini JSON - must be stored
    public_token TEXT UNIQUE,
    generated_at TEXT,
    attempts INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    token TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS login_codes (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    requested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coupons (
    code TEXT PRIMARY KEY,
    percent_off INTEGER NOT NULL,
    multi_use INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    uses_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    visitor_id TEXT,
    visit_id TEXT,                        -- the visit (see web_visits): without it the funnel lies
    customer_id INTEGER,
    type TEXT NOT NULL,
    path TEXT,                            -- WHICH page it happened on (else a goal has no address)
    payload_json TEXT,
    utm_json TEXT,
    user_agent TEXT,                      -- raw UA (for device parsing)
    device TEXT,                          -- mobile / tablet / desktop / bot
    referer TEXT,                         -- where they came from (origin)
    geo_country TEXT,                     -- country by IP (we do NOT store the IP)
    geo_region TEXT,
    geo_city TEXT,
    created_at TEXT NOT NULL
);
-- A visit = one continuous session of one person (30-minute window, cookie dr_s).
-- Without this table a "funnel" counts unique visitors per period and divides one set
-- by another: steps are not nested, a later step can come out larger than an earlier
-- one, there is no duration, and a campaign cannot be tied to an order.
-- One row per visit; events reference it through events.visit_id.
CREATE TABLE IF NOT EXISTS web_visits (
    visit_id TEXT PRIMARY KEY,
    visitor_id TEXT,
    started_at TEXT NOT NULL,
    last_at TEXT NOT NULL,
    entry_path TEXT,                      -- page they came in on
    exit_path TEXT,                       -- page they left from
    pages INTEGER DEFAULT 0,              -- HTML page views in this visit
    engaged INTEGER DEFAULT 0,            -- scrolled / clicked / 15s of visible time
    max_scroll INTEGER DEFAULT 0,         -- 25/50/75/100 - scroll depth for the visit
    device TEXT,                          -- mobile / tablet / desktop / bot (UA)
    screen_w INTEGER,                     -- SCREEN WIDTH from the client: the UA knows nothing about layout
    is_touch INTEGER,
    channel TEXT,                         -- ads / organic / social / referral / direct / internal / utm
    utm_json TEXT,                        -- UTM of THIS visit (last touch)
    gclid TEXT,                           -- ad click id - the only exact link to a campaign
    referer TEXT,
    geo_country TEXT,
    geo_region TEXT,
    customer_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type, created_at);
CREATE INDEX IF NOT EXISTS idx_events_visitor ON events(visitor_id, created_at);
CREATE INDEX IF NOT EXISTS idx_visits_started ON web_visits(started_at);
CREATE INDEX IF NOT EXISTS idx_visits_visitor ON web_visits(visitor_id, started_at);
CREATE INDEX IF NOT EXISTS idx_visits_channel ON web_visits(channel, started_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_drawings_order ON drawings(order_id);
-- The index on events(visit_id) is built in _migrate(): on an OLD database
-- executescript skips CREATE TABLE events, the column does not exist yet, and the
-- index would fail here.
"""


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")  # worker + web write the same DB
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Light migrations for existing DBs (CREATE IF NOT EXISTS won't add columns to
    an existing table). Idempotent: only ADD COLUMN if missing."""
    ev_cols = {r["name"] for r in conn.execute("PRAGMA table_info(events)")}
    for col in ("user_agent", "device", "referer", "geo_country", "geo_region",
                "geo_city", "visit_id", "path"):
        if col not in ev_cols:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT")
    # Only AFTER the ALTER: on an old DB the visit_id column does not exist while
    # executescript(SCHEMA) runs, so the index has to be built here.
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_visit ON events(visit_id)")

    ord_cols = {r["name"] for r in conn.execute("PRAGMA table_info(orders)")}
    if "locale" not in ord_cols:
        conn.execute("ALTER TABLE orders ADD COLUMN locale TEXT NOT NULL DEFAULT 'en'")
    if "payment_id" not in ord_cols:
        conn.execute("ALTER TABLE orders ADD COLUMN payment_id TEXT")
    # The visit an order was placed in. Payment arrives by webhook WITHOUT a browser,
    # so the order_paid event cannot be attached to a visit - "paid" in the visit
    # funnel is counted from the order row itself, not from the event.
    if "visit_id" not in ord_cols:
        conn.execute("ALTER TABLE orders ADD COLUMN visit_id TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_visit ON orders(visit_id)")


def get_db() -> sqlite3.Connection:
    """Per-request connection (Flask g). Closed in teardown (app/__init__)."""
    if "db" not in g:
        g.db = connect()
    return g.db


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def track(event_type: str, visitor_id: str | None = None,
          visit_id: str | None = None,
          customer_id: int | None = None, payload: dict | None = None,
          path: str | None = None,
          utm: dict | None = None, conn: sqlite3.Connection | None = None,
          user_agent: str | None = None, device: str | None = None,
          referer: str | None = None, geo_country: str | None = None,
          geo_region: str | None = None, geo_city: str | None = None) -> None:
    """Server-side analytics event. Never breaks the request.
    conn - explicit connection for non-Flask processes (worker).
    We never store the IP, only a derived geo label (country/region/city)."""
    try:
        db = conn if conn is not None else get_db()
        db.execute(
            "INSERT INTO events (visitor_id, visit_id, customer_id, type, path,"
            " payload_json, utm_json,"
            " user_agent, device, referer, geo_country, geo_region, geo_city, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (visitor_id, visit_id, customer_id, event_type, path,
             json.dumps(payload, ensure_ascii=False) if payload else None,
             json.dumps(utm, ensure_ascii=False) if utm else None,
             user_agent, device, referer,
             geo_country, geo_region, geo_city, now()),
        )
        db.commit()
    except Exception:
        pass
