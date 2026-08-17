"""Background worker for FREE analyses: status='queued' -> analysis -> done/failed.

Run:  venv\\Scripts\\python.exe free_worker.py [--once]
  --once  process the whole queue and exit (tests, cron); without it - forever loop.

A SEPARATE unit from the paid worker on purpose. The paid worker is busy for minutes at a
time generating an 8-page report; a parent waiting on the free page for their single
drawing must not sit behind that queue. On the VPS this becomes drawreport-free.

Polls faster than the paid worker (someone is watching a spinner), writes a heartbeat so
the admin can see the unit is alive, and runs the photo-retention purge once a day.
"""
import argparse
import datetime
import logging
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import free_jobs, free_retention
from app.db import connect, init_db, now
from config import settings

HEARTBEAT_NAME = "free_worker"
POLL_SECONDS = 1.0
RETENTION_EVERY_SECONDS = 24 * 3600


def setup_logging() -> None:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_h = logging.FileHandler(settings.DATA_DIR / "free_worker.log", encoding="utf-8")
    file_h.setFormatter(fmt)
    console_h = logging.StreamHandler()
    console_h.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_h)
    root.addHandler(console_h)
    for noisy in ("httpx", "anthropic", "google_genai", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def heartbeat(conn) -> None:
    """One row saying this unit is alive. deploy.sh does not start a new unit and there is
    no monitoring - without this, after a reboot of the box free analyses would silently
    stop being generated and nothing would say so."""
    conn.execute(
        "INSERT INTO service_heartbeat (name, last_seen_at) VALUES (?, ?)"
        " ON CONFLICT(name) DO UPDATE SET last_seen_at = excluded.last_seen_at",
        (HEARTBEAT_NAME, now()))
    conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser(description="free analysis worker")
    ap.add_argument("--once", action="store_true",
                    help="process pending free analyses and exit")
    args = ap.parse_args()
    setup_logging()
    log = logging.getLogger("free_worker")

    init_db()
    conn = connect()
    stale = conn.execute(
        "UPDATE free_analyses SET status = 'queued' WHERE status = 'generating'").rowcount
    conn.commit()
    if stale:
        log.warning("reset %d stale 'generating' analysis(es) back to 'queued'", stale)
    log.info("free worker started (model=%s, cap=%d/day, retention=%d days, once=%s)",
             settings.FREE_LLM_MODEL, settings.FREE_DAILY_CAP,
             settings.FREE_PHOTO_RETENTION_DAYS, args.once)

    last_retention = 0.0
    while True:
        if time.time() - last_retention > RETENTION_EVERY_SECONDS:
            last_retention = time.time()
            try:
                free_retention.purge_old_images(conn)
            except Exception as e:      # retention must never wedge the queue
                log.warning("retention pass failed: %s", e)

        row = conn.execute(
            "SELECT id FROM free_analyses WHERE status = 'queued'"
            " ORDER BY uploaded_at, id LIMIT 1").fetchone()
        if row:
            try:
                free_jobs.run_free(conn, row["id"])
            except Exception as e:      # one bad row must not kill the unit
                log.exception("free #%s crashed: %s", row["id"], e)
                conn.execute("UPDATE free_analyses SET status = 'failed', done_at = ?"
                             " WHERE id = ?", (now(), row["id"]))
                conn.commit()
            heartbeat(conn)
            continue
        if args.once:
            log.info("queue empty - exiting (--once)")
            free_retention.purge_old_images(conn)
            return 0
        heartbeat(conn)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
