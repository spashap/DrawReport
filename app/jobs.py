"""Process a paid order: report pipeline + statuses + emails + events.

Used by the worker (worker.py) and the CLI (scripts/regenerate_report.py). No Flask:
the DB connection is passed explicitly. Order statuses:
  paid -> generating -> delivered | insufficient | failed (regenerate from any).
Console log is ASCII only (Windows cp1252, UseCase #8); report/email text goes to files.
"""
from __future__ import annotations

import base64
import datetime
import json
import logging
import sqlite3
import traceback
from pathlib import Path

from app.db import new_token, now, track
from app.mailer import render_email, send_admin_alert, send_email
from config import settings
from config.form_fields import child_to_common, drawing_to_story

log = logging.getLogger("jobs")


def run_order(conn: sqlite3.Connection, order_id: int) -> str:
    """Full cycle for one order. Returns the final status
    ('delivered' / 'insufficient' / 'failed' / 'missing' / 'unpaid').
    Never raises - an error becomes status 'failed' + an alert."""
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        log.error("order %s not found", order_id)
        return "missing"
    if order["status"] == "created":      # unpaid - don't spend Gemini
        log.warning("order %s is not paid yet - skipping", order_id)
        return "unpaid"

    conn.execute("UPDATE orders SET status = 'generating' WHERE id = ?", (order_id,))
    conn.commit()
    try:
        return _process(conn, order)
    except Exception as e:
        return _handle_failure(conn, order, e)


def _process(conn: sqlite3.Connection, order: sqlite3.Row) -> str:
    # heavy imports (genai, weasyprint) only when there's work
    from pipeline.gemini import generate_report
    from pipeline.render import format_report_date, render_report_files
    from pipeline.schema import InsufficientReport

    order_id = order["id"]
    locale = order["locale"] or settings.DEFAULT_LOCALE
    child = json.loads(order["child_json"] or "{}")
    rows = conn.execute("SELECT * FROM drawings WHERE order_id = ? ORDER BY id",
                        (order_id,)).fetchall()
    if not rows:
        raise RuntimeError(f"order {order_id}: no drawings in DB")

    image_paths = [settings.BASE_DIR / r["file_path"] for r in rows]
    contexts = []
    for r in rows:
        ctx = json.loads(r["context_json"] or "{}")
        age = _age_display(child.get("birth_ym"), ctx.get("drawn_at"))
        contexts.append(drawing_to_story(ctx, age_display=age, locale=locale))

    out_dir = settings.REPORTS_DIR / str(order_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info("order %s: generating (%d drawing(s), locale=%s)", order_id, len(rows), locale)

    result = generate_report(image_paths, contexts,
                             common_context=child_to_common(child, locale),
                             locale=locale, raw_dump_dir=out_dir / "raw")
    (out_dir / "report_raw.json").write_text(result.raw_json_text, encoding="utf-8")

    if isinstance(result.report, InsufficientReport):
        return _handle_insufficient(conn, order, result.report, out_dir)

    report = result.report
    json_path = out_dir / "report.json"
    json_path.write_text(json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
                         encoding="utf-8")
    drawings = [
        {"src": "data:image/jpeg;base64," + base64.b64encode(j).decode("ascii"),
         "caption": f"Drawing {i + 1}" if len(result.image_jpegs) > 1 else report.child.name}
        for i, j in enumerate(result.image_jpegs)
    ]
    html_path, pdf_path = render_report_files(
        report, drawings, generated_date=format_report_date(datetime.date.today(), locale),
        out_dir=out_dir, locale=locale)

    token = _upsert_report_row(conn, order_id, html_path, pdf_path, json_path,
                               result.attempts_used)
    conn.execute("UPDATE orders SET status = 'delivered' WHERE id = ?", (order_id,))
    conn.commit()
    track("report_delivered", visitor_id=order["visitor_id"],
          customer_id=order["customer_id"],
          payload={"order_id": order_id, "attempts": result.attempts_used,
                   "repairs": result.repair_rounds, "lint_left": result.lint_hits_left},
          conn=conn)

    base = settings.PUBLIC_BASE_URL.rstrip("/")
    html = render_email("report_ready.html", locale=locale, child_name=report.child.name,
                        report_url=f"{base}/{locale}/r/{token}",
                        cabinet_url=f"{base}/{locale}/cabinet",
                        drawings_count=len(rows))
    send_email(order["email"], f"Your report is ready - {settings.SITE_NAME}", html,
               attachments=[pdf_path], kind="report_ready")
    log.info("order %s: DELIVERED (attempts=%d, repairs=%d)",
             order_id, result.attempts_used, result.repair_rounds)
    return "delivered"


def report_pdf_path(conn: sqlite3.Connection, order_id: int) -> Path | None:
    """Path to the order's finished PDF if it exists on disk; else None."""
    row = conn.execute("SELECT pdf_path FROM reports WHERE order_id = ?",
                       (order_id,)).fetchone()
    if not row or not row["pdf_path"]:
        return None
    pdf = settings.BASE_DIR / row["pdf_path"]
    return pdf if pdf.exists() else None


def resend_report_email(conn: sqlite3.Connection, order_id: int) -> bool:
    """Re-send the finished-report email (NO regeneration, no Gemini) - for when the
    report exists but the email didn't arrive. True if sent."""
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    row = conn.execute(
        "SELECT pdf_path, report_json_path, public_token FROM reports WHERE order_id = ?",
        (order_id,)).fetchone()
    if order is None or row is None or not row["pdf_path"] or not row["public_token"]:
        return False
    pdf_path = settings.BASE_DIR / row["pdf_path"]
    if not pdf_path.exists():
        return False
    locale = order["locale"] or settings.DEFAULT_LOCALE
    child_name = ""
    if row["report_json_path"]:
        try:
            data = json.loads((settings.BASE_DIR / row["report_json_path"]).read_text(encoding="utf-8"))
            child_name = (data.get("child") or {}).get("name", "")
        except (OSError, ValueError):
            pass
    if not child_name:
        child_name = json.loads(order["child_json"] or "{}").get("name", "")
    drawings_n = conn.execute("SELECT COUNT(*) AS n FROM drawings WHERE order_id = ?",
                              (order_id,)).fetchone()["n"]
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    html = render_email("report_ready.html", locale=locale, child_name=child_name,
                        report_url=f"{base}/{locale}/r/{row['public_token']}",
                        cabinet_url=f"{base}/{locale}/cabinet", drawings_count=drawings_n)
    send_email(order["email"], f"Your report is ready - {settings.SITE_NAME}", html,
               attachments=[pdf_path], kind="report_ready")
    if order["status"] != "delivered":
        conn.execute("UPDATE orders SET status = 'delivered' WHERE id = ?", (order_id,))
        conn.commit()
    log.info("order %s: report email RESENT to %s", order_id, order["email"])
    return True


def _handle_insufficient(conn: sqlite3.Connection, order: sqlite3.Row,
                         report, out_dir: Path) -> str:
    order_id = order["id"]
    locale = order["locale"] or settings.DEFAULT_LOCALE
    (out_dir / "insufficient.json").write_text(report.model_dump_json(indent=2),
                                               encoding="utf-8")
    conn.execute("UPDATE orders SET status = 'insufficient' WHERE id = ?", (order_id,))
    conn.commit()
    track("order_insufficient", visitor_id=order["visitor_id"],
          customer_id=order["customer_id"],
          payload={"order_id": order_id, "reason": report.insufficient_reason}, conn=conn)

    html = render_email("insufficient.html", locale=locale, reason=report.insufficient_reason)
    send_email(order["email"], f"We need better photos - {settings.SITE_NAME}",
               html, kind="insufficient")
    send_admin_alert(f"order {order_id}: insufficient input",
                     f"Order {order_id} ({order['email']}): the model judged the input "
                     f"insufficient.\n\nReason: {report.insufficient_reason}")
    log.warning("order %s: INSUFFICIENT input", order_id)
    return "insufficient"


def _handle_failure(conn: sqlite3.Connection, order: sqlite3.Row, exc: Exception) -> str:
    order_id = order["id"]
    detail = "\n".join([repr(exc), *getattr(exc, "attempts_log", []),
                        "", traceback.format_exc()])
    err_dir = settings.REPORTS_DIR / str(order_id)
    err_dir.mkdir(parents=True, exist_ok=True)
    (err_dir / "error.log").write_text(f"{now()}\n{detail}", encoding="utf-8")

    conn.execute("UPDATE orders SET status = 'failed' WHERE id = ?", (order_id,))
    conn.commit()
    track("report_failed", visitor_id=order["visitor_id"],
          customer_id=order["customer_id"],
          payload={"order_id": order_id, "error": type(exc).__name__}, conn=conn)
    send_admin_alert(f"order {order_id}: generation FAILED",
                     f"Order {order_id} ({order['email']}) failed to generate.\n"
                     f"Retry: scripts/regenerate_report.py {order_id}\n\n{detail}")
    log.error("order %s: FAILED (%s) - see %s", order_id, type(exc).__name__,
              err_dir / "error.log")
    return "failed"


def _upsert_report_row(conn: sqlite3.Connection, order_id: int, html_path: Path,
                       pdf_path: Path, json_path: Path, attempts: int) -> str:
    """Write the reports row. On regenerate the public_token is PRESERVED -
    the client's /r/<token> link never changes."""
    rel = lambda p: p.relative_to(settings.BASE_DIR).as_posix()  # POSIX for the Linux VPS
    row = conn.execute("SELECT id, public_token FROM reports WHERE order_id = ?",
                       (order_id,)).fetchone()
    token = (row["public_token"] if row and row["public_token"] else new_token(16))
    if row:
        conn.execute(
            "UPDATE reports SET html_path=?, pdf_path=?, report_json_path=?,"
            " public_token=?, generated_at=?, attempts=? WHERE id=?",
            (rel(html_path), rel(pdf_path), rel(json_path), token, now(), attempts, row["id"]))
    else:
        conn.execute(
            "INSERT INTO reports (order_id, html_path, pdf_path, report_json_path,"
            " public_token, generated_at, attempts) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (order_id, rel(html_path), rel(pdf_path), rel(json_path), token, now(), attempts))
    return token


def _age_display(birth_ym: str | None, drawn_at: str | None) -> str | None:
    """'YYYY-MM' birth + 'YYYY-MM' drawing -> "5 years 3 months". We compute the age
    ourselves - the model isn't trusted with date math."""
    if not birth_ym or not drawn_at:
        return None
    try:
        by, bm = map(int, birth_ym.split("-"))
        dy, dm = map(int, drawn_at.split("-"))
    except ValueError:
        return None
    total = (dy * 12 + dm) - (by * 12 + bm)
    if total < 0:
        return None
    years, months = divmod(total, 12)
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    return " ".join(parts) or "less than a month"
