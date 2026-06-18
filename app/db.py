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
    customer_id INTEGER,
    type TEXT NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type, created_at);
CREATE INDEX IF NOT EXISTS idx_events_visitor ON events(visitor_id, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_drawings_order ON drawings(order_id);
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
    for col in ("user_agent", "device", "referer", "geo_country", "geo_region", "geo_city"):
        if col not in ev_cols:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT")
    ord_cols = {r["name"] for r in conn.execute("PRAGMA table_info(orders)")}
    if "locale" not in ord_cols:
        conn.execute("ALTER TABLE orders ADD COLUMN locale TEXT NOT NULL DEFAULT 'en'")
    if "payment_id" not in ord_cols:
        conn.execute("ALTER TABLE orders ADD COLUMN payment_id TEXT")


def get_db() -> sqlite3.Connection:
    """Per-request connection (Flask g). Closed in teardown (app/__init__)."""
    if "db" not in g:
        g.db = connect()
    return g.db


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def track(event_type: str, visitor_id: str | None = None,
          customer_id: int | None = None, payload: dict | None = None,
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
            "INSERT INTO events (visitor_id, customer_id, type, payload_json, utm_json,"
            " user_agent, device, referer, geo_country, geo_region, geo_city, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (visitor_id, customer_id, event_type,
             json.dumps(payload, ensure_ascii=False) if payload else None,
             json.dumps(utm, ensure_ascii=False) if utm else None,
             user_agent, device, referer,
             geo_country, geo_region, geo_city, now()),
        )
        db.commit()
    except Exception:
        pass
