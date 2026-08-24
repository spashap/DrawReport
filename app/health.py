"""Liveness of the background units, in ONE place.

Two consumers read this: the admin Tasks page (a human looking at a screen) and
`/healthz` (UptimeRobot, every 5 minutes, at 3am, when nobody is looking at any
screen). They MUST agree - a threshold that says "alive" on one and "dead" on
the other is worse than having neither, so the table below is the only place
either of them gets its numbers from.

Why the thresholds differ per unit: free_worker marks itself roughly once a
second, because someone is watching a spinner. The paid worker is silent for the
whole time it generates a report, which is minutes. A shared limit would either
paint normal paid-report generation as an outage or let a dead free worker sit
unnoticed for ten minutes.

The failure this exists to catch is specific and quiet: a worker unit dies (or
never comes back after a reboot) while gunicorn keeps serving perfectly. Every
page returns 200, the site looks healthy from outside, and meanwhile every free
reading queues forever and every paid order stops being delivered.
"""
from __future__ import annotations

import datetime

# (row name, human label, seconds after which silence means dead)
WATCHED = (
    ("free_worker", "free_worker (free readings)", 120),
    ("worker", "worker (paid reports)", 600),
)


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def now_iso() -> str:
    return _utcnow().isoformat(timespec="seconds")


def heartbeat(conn, name: str) -> None:
    """Mark a unit alive. Takes a RAW sqlite3 connection, not the Flask g.db:
    the callers are worker.py / free_worker.py, which run outside the app."""
    conn.execute(
        "INSERT INTO service_heartbeat (name, last_seen_at) VALUES (?, ?)"
        " ON CONFLICT(name) DO UPDATE SET last_seen_at = excluded.last_seen_at",
        (name, now_iso()))
    conn.commit()


def statuses(db) -> list[dict]:
    """One entry per watched unit: {name, label, ago, ok}. `ago` is None when the
    unit has never written a row at all - which is the after-a-reboot case, and
    is NOT ok."""
    now_utc = _utcnow()
    seen = {r["name"]: r["last_seen_at"] for r in
            db.execute("SELECT name, last_seen_at FROM service_heartbeat")}
    out = []
    for name, label, limit in WATCHED:
        ts = seen.get(name)
        ago = None
        if ts:
            try:
                ago = int((now_utc - datetime.datetime.fromisoformat(ts)).total_seconds())
            except ValueError:
                ago = None
        out.append({"name": name, "label": label, "ago": ago,
                    "limit": limit, "ok": ago is not None and ago < limit})
    return out


def report(db) -> tuple[bool, str]:
    """(everything_ok, plain-text body) for /healthz."""
    rows = statuses(db)
    ok = all(r["ok"] for r in rows)
    lines = [f"status: {'ok' if ok else 'stale'}"]
    for r in rows:
        age = "never" if r["ago"] is None else f"{r['ago']}s"
        lines.append(f"{r['name']}: {age} (limit {r['limit']}s)"
                     f"{'' if r['ok'] else '  <-- STALE'}")
    return ok, "\n".join(lines) + "\n"
