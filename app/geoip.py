"""Offline IP -> country/region lookup from data/geoip.db (built on the server by
scripts/build_geoip.py from the DB-IP City Lite dataset, CC BY 4.0).

Degrades gracefully: if the DB is missing (e.g. local dev), lookup() returns None
and analytics simply records no geo. The raw IP is never stored.
"""
from __future__ import annotations

import ipaddress
import sqlite3

from config import settings

_GEO_DB = settings.DATA_DIR / "geoip.db"
_conn: sqlite3.Connection | None = None
_checked = False


def _db() -> sqlite3.Connection | None:
    global _conn, _checked
    if _checked:
        return _conn
    _checked = True
    if _GEO_DB.exists():
        try:
            _conn = sqlite3.connect(f"file:{_GEO_DB}?mode=ro", uri=True,
                                    check_same_thread=False)
            _conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            _conn = None
    return _conn


def lookup(ip: str | None) -> dict | None:
    """{'country','region','city'} for an IPv4 address, or None. Best-effort."""
    if not ip:
        return None
    conn = _db()
    if conn is None:
        return None
    try:
        n = int(ipaddress.ip_address(ip))
    except ValueError:
        return None
    try:
        row = conn.execute(
            "SELECT country, region, city FROM ranges WHERE ip_from <= ? AND ip_to >= ?"
            " ORDER BY ip_from DESC LIMIT 1", (n, n)).fetchone()
    except sqlite3.Error:
        return None
    return dict(row) if row else None


def country_name(code: str | None) -> str:
    """Display name for a country code. We store ISO codes; no names DB, so return
    the code (good enough for the admin dashboards)."""
    return code or "-"


def geo_label(country: str | None, region: str | None) -> str:
    """'US / California' style label for the admin tables."""
    parts = [p for p in (country_name(country) if country else None, region) if p and p != "-"]
    return " / ".join(parts) if parts else "-"
