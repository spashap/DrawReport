"""The free-analysis job: one queued row -> a validated analysis in the database.

Mirrors app/jobs.run_order for the paid path, but the failure semantics differ: nobody
has paid, and the parent is waiting on screen. So a failure is terminal and cheap rather
than retried forever - the page tells them plainly and offers to try another photo.

The interpretation rows are written here rather than in the pipeline on purpose: the
library of admissible interpretations must record what was actually SHIPPED to a parent,
after the linter and any downgrade, not what the model first produced.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.db import now
from config import settings
from pipeline.free_llm import FreeGenerationError, generate_free_analysis
from pipeline.free_schema import FreeAnalysis, FreeInsufficient

log = logging.getLogger("free_jobs")


def _record_interpretation(conn, analysis_id: int, a: FreeAnalysis, child_age: int) -> None:
    """One row per interpretation actually shipped. hypothesis=None writes nothing -
    an empty cell is a legitimate outcome, not a missing record."""
    if a.hypothesis is None:
        return
    h = a.hypothesis
    conn.execute(
        "INSERT INTO free_interpretations (analysis_id, key, phrase, attribution,"
        " age_scope, new_key_description, child_age, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (analysis_id, h.key, h.phrase, h.attribution, h.age_scope,
         h.new_key_description or None, child_age, now()))
    # A key the owner has not ruled on yet gets a placeholder row so it shows up in the
    # admin list of things to label rather than only existing inside an analysis.
    conn.execute(
        "INSERT INTO free_interpretation_keys (key, verdict, note, decided_at)"
        " VALUES (?, NULL, NULL, NULL) ON CONFLICT(key) DO NOTHING", (h.key,))


def run_free(conn, analysis_id: int) -> str:
    """Generate one free analysis. Returns the final status."""
    row = conn.execute("SELECT * FROM free_analyses WHERE id = ?",
                       (analysis_id,)).fetchone()
    if row is None:
        return "missing"
    if not row["image_path"]:
        log.warning("free #%s: no image on the row - marking failed", analysis_id)
        conn.execute("UPDATE free_analyses SET status = 'failed' WHERE id = ?",
                     (analysis_id,))
        conn.commit()
        return "failed"

    conn.execute("UPDATE free_analyses SET status = 'generating', attempts = attempts + 1"
                 " WHERE id = ?", (analysis_id,))
    conn.commit()

    try:
        result = generate_free_analysis(
            Path(row["image_path"]),
            child_name=row["child_name"], age=row["age"],
            address_form=row["address_form"] or "they",
            concern_key=row["concern_key"],
            duration_label=row["duration_key"] or "",
            parent_text=row["parent_text"] or "",
            locale=row["locale"] or settings.DEFAULT_LOCALE,
        )
    except FreeGenerationError as e:
        log.error("free #%s: generation failed: %s", analysis_id, e)
        conn.execute("UPDATE free_analyses SET status = 'failed', done_at = ?"
                     " WHERE id = ?", (now(), analysis_id))
        conn.commit()
        return "failed"

    a = result.analysis
    if isinstance(a, FreeInsufficient):
        conn.execute(
            "UPDATE free_analyses SET status = 'insufficient', reason_key = ?,"
            " result_json = ?, model = ?, prompt_version = ?, elapsed_s = ?, done_at = ?"
            " WHERE id = ?",
            (a.reason_key, json.dumps(a.model_dump(), ensure_ascii=False), result.model,
             result.prompt_version, result.elapsed_s, now(), analysis_id))
        conn.commit()
        log.info("free #%s: insufficient (%s)", analysis_id, a.reason_key)
        return "insufficient"

    conn.execute(
        "UPDATE free_analyses SET status = 'done', result_json = ?, model = ?,"
        " prompt_version = ?, repair_rounds = ?, hypothesis_dropped = ?, elapsed_s = ?,"
        " done_at = ? WHERE id = ?",
        (json.dumps(a.model_dump(), ensure_ascii=False), result.model,
         result.prompt_version, result.repair_rounds,
         1 if result.hypothesis_dropped else 0, result.elapsed_s, now(), analysis_id))
    _record_interpretation(conn, analysis_id, a, row["age"])
    conn.commit()
    if row["email"]:
        # The emailed copy is why the parent gave us the address at upload. A mail
        # failure must never turn a finished reading into a failed one.
        try:
            from app.mailer import send_free_ready
            send_free_ready(conn, row["email"], row["token"], row["child_name"])
        except Exception as e:
            log.warning("free #%s: could not send the ready email: %s", analysis_id, e)
    log.info("free #%s: done in %.1fs (%d words, repairs=%d, dropped=%s)",
             analysis_id, result.elapsed_s, a.word_count(), result.repair_rounds,
             result.hypothesis_dropped)
    return "done"
