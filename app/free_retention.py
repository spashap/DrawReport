"""Retention of free-analysis photos: delete the child's drawing after N days.

Why this exists at all: the free funnel accepts photographs of children's drawings from
people who have not bought anything and may never come back. Keeping those indefinitely
is the kind of thing a privacy policy has to be able to state plainly, and "we keep it
forever because nobody wrote the deletion job" is not a sentence anyone wants to write.

What is deleted: the image file only. The analysis text, the interpretation rows and the
counters stay - they are what the beta is for, and they contain no photograph. The row
records image_deleted_at so the page can say honestly that the drawing is no longer
stored rather than 404-ing with no explanation.
"""
from __future__ import annotations

import datetime
import logging
from pathlib import Path

from app.db import now
from config import settings

log = logging.getLogger("free_retention")


def _cutoff(days: int) -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=days)).isoformat(timespec="seconds")


def purge_old_images(conn, days: int | None = None) -> dict:
    """Delete drawing files older than the retention period. Idempotent and safe to run
    on every worker tick: rows already purged have image_path IS NULL and are skipped."""
    days = days if days is not None else settings.FREE_PHOTO_RETENTION_DAYS
    cutoff = _cutoff(days)
    rows = conn.execute(
        "SELECT id, token, image_path FROM free_analyses"
        " WHERE image_path IS NOT NULL AND uploaded_at IS NOT NULL AND uploaded_at < ?",
        (cutoff,)).fetchall()

    deleted, missing = 0, 0
    for r in rows:
        p = Path(r["image_path"])
        try:
            if p.exists():
                p.unlink()
                deleted += 1
            else:
                missing += 1        # already gone from disk - still clear the column
        except OSError as e:
            log.warning("free_retention: could not delete %s: %s", p, e)
            continue
        conn.execute(
            "UPDATE free_analyses SET image_path = NULL, image_deleted_at = ?"
            " WHERE id = ?", (now(), r["id"]))
    if rows:
        conn.commit()
        log.info("free_retention: %d file(s) deleted, %d already absent (older than %d days)",
                 deleted, missing, days)
    return {"considered": len(rows), "deleted": deleted, "missing": missing,
            "cutoff": cutoff, "days": days}


def delete_image(conn, analysis_id: int) -> bool:
    """Delete one photo on request, before the retention period is up.

    There was no deletion path in the project at all, and the first such request is
    inevitable: we store other people's children's drawings, and "wait ninety days" is not
    an answer a parent should have to accept."""
    row = conn.execute("SELECT image_path FROM free_analyses WHERE id = ?",
                       (analysis_id,)).fetchone()
    if row is None:
        return False
    existed = False
    if row["image_path"]:
        p = Path(row["image_path"])
        try:
            if p.exists():
                p.unlink()
                existed = True
        except OSError as e:
            log.warning("delete_image: could not delete %s: %s", p, e)
            return False
    conn.execute("UPDATE free_analyses SET image_path = NULL, image_deleted_at = ?"
                 " WHERE id = ?", (now(), analysis_id))
    conn.commit()
    return existed


def used_today(conn) -> int:
    """How many free analyses have actually been GENERATED today (UTC). Counts the ones
    that reached the model, not questionnaires: a draft row costs nothing."""
    start = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return conn.execute(
        "SELECT COUNT(*) c FROM free_analyses"
        " WHERE uploaded_at >= ? AND status IN ('queued','generating','done',"
        " 'insufficient','failed')", (start,)).fetchone()["c"]


def used_today_by_email(conn, email: str) -> int:
    """How many free analyses this email has had generated today (UTC).

    Counted from uploaded_at, not created_at: an email left through the "no drawing to
    hand" exit never reached the model and cost nothing, so it must not consume anyone's
    quota."""
    if not email:
        return 0
    start = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return conn.execute(
        "SELECT COUNT(*) c FROM free_analyses"
        " WHERE LOWER(email) = ? AND uploaded_at >= ?"
        " AND status IN ('queued','generating','done','insufficient','failed')",
        (email.strip().lower(), start)).fetchone()["c"]


def cap_reached(conn) -> bool:
    """Is the GLOBAL daily ceiling used up? Checked before accepting a drawing, not after:
    the point is to refuse the upload politely, not to take the photo and then refuse.
    0 = unlimited."""
    cap = settings.get_free_limits().get("daily_cap", 0)
    return cap > 0 and used_today(conn) >= cap


def email_cap_reached(conn, email: str) -> bool:
    """Has this address used up its own daily allowance? 0 = unlimited.

    This is cost control, NOT the one-reading-per-child limit - that one is a sales
    redirect ("the next step is looking at drawings together") and must not share wording
    with this, or a parent who hit a technical limit gets a sales pitch."""
    cap = settings.get_free_limits().get("per_email_daily", 0)
    return cap > 0 and used_today_by_email(conn, email) >= cap
