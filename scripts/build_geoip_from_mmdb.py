"""Build data/geoip.db - DrawReport's compact offline IP -> country/region table - from a
MaxMind GeoLite2 City database (.mmdb).

Why this exists: app/geoip.py was written against a SQLite `ranges` table that the deploy
README said scripts/build_geoip.py would produce from DB-IP Lite. That script was never
copied into this repo, so from launch until 2026-09-06 every visit was recorded with no
country. The same server already holds a GeoLite2-City.mmdb for the cosmyday project
(/var/www/cosmyday-api/data/, read-only for us), so the fastest fix is to convert that
file into the table app/geoip.py already reads. No new dependency lands in DrawReport's
venv: run this with ANY python that has `maxminddb` installed, e.g. on the server

    /var/www/cosmyday-api/venv/bin/python scripts/build_geoip_from_mmdb.py \
        /var/www/cosmyday-api/data/GeoLite2-City.mmdb

then restart the units (app/geoip.py opens the file once and caches the result, so a
running gunicorn that started without the file keeps answering None until restarted).

What is kept: country ISO code + first subdivision ISO code, IPv4 only. City is dropped
(nothing in the admin reads it) and adjacent networks with the same (country, region) are
merged, which shrinks ~3.5M city-level networks to a few hundred thousand rows.
IPv6 networks are skipped: app/geoip.py stores the address as a SQLite INTEGER, which is
64-bit, and the site's traffic is overwhelmingly IPv4.

Data: GeoLite2 by MaxMind, https://www.maxmind.com - attribution required where the data
is shown (it is shown only in the private admin). Re-run whenever the source file is
refreshed. ASCII-only stdout.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "geoip.db"
BATCH = 50_000

SCHEMA = """
CREATE TABLE ranges (
    ip_from INTEGER PRIMARY KEY,   -- inclusive; PRIMARY KEY doubles as the lookup index
    ip_to   INTEGER NOT NULL,      -- inclusive
    country TEXT,                  -- ISO 3166-1 alpha-2
    region  TEXT,                  -- first subdivision ISO code (e.g. 'CA'), may be NULL
    city    TEXT                   -- always NULL in this build; column kept for app/geoip.py
);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
"""


def _key(rec: dict) -> tuple[str | None, str | None]:
    country = (rec.get("country") or rec.get("registered_country") or {}).get("iso_code")
    subs = rec.get("subdivisions") or []
    region = subs[0].get("iso_code") if subs else None
    return country, region


def _networks(reader):
    """Yield (start_int, end_int, country, region) for every IPv4 network, in order."""
    skipped_v6 = 0
    for net, rec in reader:
        if net.version == 6:
            mapped = net.network_address.ipv4_mapped
            if mapped is None:
                skipped_v6 += 1
                continue
            # ::ffff:a.b.c.d/N -> IPv4 /(N-96)
            net = ipaddress.ip_network(f"{mapped}/{net.prefixlen - 96}", strict=False)
        country, region = _key(rec)
        if not country:
            continue
        yield (int(net.network_address), int(net.broadcast_address), country, region)
    print(f"  IPv6-only networks skipped: {skipped_v6}")


def _merged(rows):
    """Coalesce adjacent ranges with identical (country, region)."""
    cur = None
    for start, end, country, region in rows:
        if cur and cur[1] + 1 == start and cur[2] == country and cur[3] == region:
            cur[1] = end
        else:
            if cur:
                yield tuple(cur)
            cur = [start, end, country, region]
    if cur:
        yield tuple(cur)


def build(mmdb: Path, out: Path) -> int:
    import maxminddb  # imported here so the docstring's "any python" advice is honest

    reader = maxminddb.open_database(str(mmdb))
    md = reader.metadata()
    print(f"source: {mmdb} ({md.database_type}, built {time.strftime('%Y-%m-%d', time.gmtime(md.build_epoch))})")

    tmp = out.with_suffix(out.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(tmp)
    conn.executescript(SCHEMA)
    n = 0
    batch = []
    t0 = time.time()
    for row in _merged(_networks(reader)):
        batch.append(row)
        if len(batch) >= BATCH:
            conn.executemany("INSERT INTO ranges (ip_from, ip_to, country, region) VALUES (?,?,?,?)", batch)
            n += len(batch)
            batch.clear()
            print(f"  {n} rows...", flush=True)
    if batch:
        conn.executemany("INSERT INTO ranges (ip_from, ip_to, country, region) VALUES (?,?,?,?)", batch)
        n += len(batch)
    conn.executemany("INSERT INTO meta (key, value) VALUES (?,?)", [
        ("source", "GeoLite2 by MaxMind (https://www.maxmind.com)"),
        ("source_file", str(mmdb)),
        ("source_build_epoch", str(md.build_epoch)),
        ("built_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("ip_versions", "4"),
    ])
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    reader.close()
    os.replace(tmp, out)  # atomic: a reader never sees a half-written file
    print(f"wrote {out} : {n} ranges, {out.stat().st_size // 1_000_000} MB, {time.time() - t0:.0f}s")
    return n


def verify(out: Path) -> None:
    """Same query app/geoip.py runs, against a few addresses whose country is not in doubt."""
    conn = sqlite3.connect(f"file:{out}?mode=ro", uri=True)
    probes = {"8.8.8.8": "US", "1.0.1.1": "CN", "77.88.8.8": "RU", "5.78.181.152": "US", "81.2.69.142": "GB"}
    bad = 0
    for ip, want in probes.items():
        n = int(ipaddress.ip_address(ip))
        row = conn.execute("SELECT country, region FROM ranges WHERE ip_from <= ? AND ip_to >= ?"
                           " ORDER BY ip_from DESC LIMIT 1", (n, n)).fetchone()
        got = row[0] if row else None
        flag = "ok " if got == want else "?? "
        bad += got != want
        print(f"  {flag}{ip:16} -> {got} {row[1] if row else ''}  (expected {want})")
    conn.close()
    if bad:
        print(f"WARNING: {bad} probe(s) differ - a stale source can legitimately disagree on a few")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mmdb", type=Path, help="path to GeoLite2-City.mmdb (or -Country.mmdb)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output SQLite file (default {DEFAULT_OUT})")
    ap.add_argument("--verify-only", action="store_true", help="skip the build, just probe --out")
    a = ap.parse_args()
    if not a.verify_only:
        if not a.mmdb.exists():
            print(f"ERROR: {a.mmdb} not found")
            return 2
        build(a.mmdb, a.out)
    verify(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
