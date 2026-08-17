"""The free funnel: the wizard, the summary, the upload, the waiting screen, the result.

The shape of the funnel, and why each step is where it is:

  /free            three questions, one screen each
  POST /free/summary   -> the summary, composed ON THE SERVER
  POST /free/upload    -> the drawing + "where shall we send it" -> queued
  GET  /free/status    -> polled by the waiting screen
  /free/r/<token>      -> the finished reading

THE SUMMARY IS COMPOSED ON THE SERVER, not in the browser. The one absolute requirement
of that block is that text is only ever joined at paragraph boundaries, and a bug in a
client-side assembler would produce exactly the artifact the whole product exists to
avoid - a sentence that reads as a claim about a child that nobody made.

THE EMAIL IS ASKED FOR AT UPLOAD, framed as "where shall we send the reading?", not as a
wall after forty seconds of waiting. Note what is NOT gated: the summary after the
questions costs nothing and is shown to everyone. The email buys delivery of the analysis,
which is a thing the parent actually wants at that moment.

Failed uploads are EVENTS, not just messages on screen. That was the largest hole in the
funnel: someone answers every question, presses the button, hits a size or format limit -
and analytics records nothing at all, so "uploaded a drawing" simply never happens with
no explanation of why.
"""
from __future__ import annotations

import json
from pathlib import Path

from flask import (Blueprint, Response, abort, g, jsonify, redirect,
                   render_template, request, url_for)

from app.db import get_db, new_token, now
from app.free_retention import cap_reached
from app.orders import EMAIL_RE
from app.track import track_event
from config import free_texts as T
from config import settings
from pipeline.free_schema import FreeAnalysis

bp_free = Blueprint("free", __name__, url_prefix="/free")

FREE_SCOPE_COOKIE = "dr_free"      # which analyses this browser may open
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}

# Magic bytes. A cheap sniff BEFORE the row is touched, so "a failed upload does not
# consume the daily cap" holds by construction rather than by reconciling statuses later.
_MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF", b"\x00\x00\x00")


def _sniff(blob: bytes) -> bool:
    return any(blob.startswith(m) for m in _MAGIC) or b"ftyp" in blob[:32]


def _scope_tokens() -> list[str]:
    try:
        v = json.loads(request.cookies.get(FREE_SCOPE_COOKIE) or "[]")
        return [t for t in v if isinstance(t, str)][:20]
    except ValueError:
        return []


def _owns(token: str) -> bool:
    return token in _scope_tokens()


def _norm_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def _existing_free(db, name_norm: str, age: int):
    """A finished reading for the same child from this browser. The limit is one free
    reading per child - and it is a REDIRECT, not a refusal: the honest next step is
    looking at drawings together, which is what the paid report does."""
    if not name_norm:
        return None
    scope = _scope_tokens()
    if not scope:
        return None
    ph = ",".join("?" * len(scope))
    return db.execute(
        f"SELECT id, token FROM free_analyses WHERE status = 'done'"
        f" AND child_name_norm = ? AND abs(age - ?) <= 1 AND token IN ({ph})"
        f" ORDER BY id DESC LIMIT 1", (name_norm, age, *scope)).fetchone()


# --- The wizard -------------------------------------------------------------------

@bp_free.get("/")
def page():
    track_event("free_view")
    return render_template("free.html", concerns=T.CONCERNS, durations=T.DURATIONS,
                           bands=T.AGE_BANDS, texts=T)


@bp_free.post("/summary")
def summary():
    f = request.form
    name = (f.get("name") or "").strip()[:40]
    band_key = f.get("band") or ""
    concern = f.get("concern") or ""
    if band_key not in T.BAND_BY_KEY or not name or concern not in T.CONCERN_KEYS:
        track_event("free_summary_invalid",
                    {"field": "band" if band_key not in T.BAND_BY_KEY
                     else ("name" if not name else "concern")})
        return jsonify({"error": "bad_input"}), 400
    age = T.band_age(band_key)
    address = f.get("address") if f.get("address") in T.ADDRESS_FORMS else "they"
    duration = f.get("duration") or ""
    parent_text = (f.get("parent_text") or "").strip()[:2000]

    s = T.assemble_summary(concern_key=concern,
                           duration_key=None if concern == "neutral" else duration,
                           age=age, address_form=address, name=name)

    db = get_db()
    token = new_token(12)
    db.execute(
        "INSERT INTO free_analyses (token, visitor_id, visit_id, child_name,"
        " child_name_norm, age, address_form, concern_key, duration_key, parent_text,"
        " status, locale, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,'draft',?,?)",
        (token, getattr(g, "visitor_id", None), getattr(g, "visit_id", None), name,
         _norm_name(name), age, address, concern, duration or None,
         parent_text or None, g.get("lang_code", settings.DEFAULT_LOCALE), now()))
    db.commit()
    track_event("free_summary", {"concern": concern, "age": age})

    limit_row = _existing_free(db, _norm_name(name), age)
    html = render_template(
        "_free_summary.html", paragraphs=s["paragraphs"], kinds=s["kinds"],
        ask=s["ask"], ask_note=s["ask_note"], lens_question=s["lens_question"],
        token=token, name=name, address=address, texts=T,
        wait_hint=T.wait_hint(concern, address),
        limit_token=limit_row["token"] if limit_row else None,
        limit_title=T.LIMIT_TITLE.format(name=name),
        limit_cta=T.LIMIT_CTA.format(name_poss=T.possessive(name)))
    return Response(html)


# --- Upload -----------------------------------------------------------------------

def _upload_failed(reason: str, payload: dict, code: int):
    track_event("free_upload_failed", {"reason": reason})
    return jsonify(payload), code


@bp_free.post("/upload/<token>")
def upload(token: str):
    db = get_db()
    row = db.execute("SELECT * FROM free_analyses WHERE token = ?", (token,)).fetchone()
    if row is None:
        return _upload_failed("not_found", {"error": "not_found"}, 404)
    if row["status"] not in ("draft", "failed", "rejected"):
        return _upload_failed("already", {"error": "already", "token": token}, 409)

    limit_row = _existing_free(db, row["child_name_norm"], row["age"])
    if limit_row is not None:
        return _upload_failed("limit", {"error": "limit", "token": limit_row["token"]}, 409)

    # The cap is checked BEFORE the photo is accepted: the point is to decline politely,
    # not to take the drawing and then decline.
    if cap_reached(db):
        track_event("free_cap_hit")
        return jsonify({"error": "cap"}), 429

    addr = (request.form.get("email") or "").strip().lower()
    if not EMAIL_RE.match(addr):
        return _upload_failed("email", {"error": "email"}, 400)

    fs = request.files.get("file")
    if fs is None or not fs.filename:
        return _upload_failed("no_file", {"error": "no_file"}, 400)
    ext = Path(fs.filename.lower()).suffix
    if ext not in ALLOWED_EXT:
        return _upload_failed("format", {"error": "format"}, 400)
    blob = fs.read()
    if len(blob) > settings.UPLOAD_MAX_BYTES:
        return _upload_failed("too_big", {"error": "too_big"}, 400)
    if len(blob) < 1024 or not _sniff(blob):
        return _upload_failed("broken", {"error": "broken"}, 400)

    settings.FREE_DIR.mkdir(parents=True, exist_ok=True)
    path = settings.FREE_DIR / f"{token}{ext}"
    path.write_bytes(blob)
    db.execute(
        "UPDATE free_analyses SET image_path = ?, email = ?, status = 'queued',"
        " uploaded_at = ? WHERE id = ?",
        (str(path), addr, now(), row["id"]))
    db.commit()
    track_event("free_upload", {"concern": row["concern_key"]})

    resp = jsonify({"ok": True, "token": token})
    scope = _scope_tokens()
    if token not in scope:
        scope.append(token)
    resp.set_cookie(FREE_SCOPE_COOKIE, json.dumps(scope[-20:]),
                    max_age=365 * 24 * 3600, httponly=True, samesite="Lax")
    return resp


@bp_free.post("/save-place/<token>")
def save_place(token: str):
    """The "no drawing to hand" exit. The email buys ONE thing - the link back, with the
    answers kept - and we say exactly that. It is honest precisely because it matches what
    just happened to the parent: they answered the questions and have no photo yet."""
    db = get_db()
    row = db.execute("SELECT id, status FROM free_analyses WHERE token = ?",
                     (token,)).fetchone()
    if row is None:
        return jsonify({"error": "not_found"}), 404
    addr = (request.form.get("email") or "").strip().lower()
    if not EMAIL_RE.match(addr):
        return jsonify({"error": "email"}), 400
    db.execute("UPDATE free_analyses SET email = ? WHERE id = ?", (addr, row["id"]))
    db.commit()
    track_event("free_save_place")
    from app.mailer import send_free_save_place
    try:
        send_free_save_place(db, addr, token)
    except Exception:      # a mail failure must not lose the saved place
        pass
    return jsonify({"ok": True})


@bp_free.get("/status/<token>")
def status(token: str):
    row = get_db().execute(
        "SELECT status, reason_key FROM free_analyses WHERE token = ?",
        (token,)).fetchone()
    if row is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"status": row["status"], "reason": row["reason_key"],
                    "url": url_for("free.result", token=token)})


# --- The result -------------------------------------------------------------------

@bp_free.get("/r/<token>")
def result(token: str):
    db = get_db()
    row = db.execute("SELECT * FROM free_analyses WHERE token = ?", (token,)).fetchone()
    if row is None:
        abort(404)
    track_event("free_result_view", {"status": row["status"]})

    if row["status"] in ("draft", "queued", "generating"):
        return render_template("free_wait.html", token=token,
                               hint=T.wait_hint(row["concern_key"],
                                                row["address_form"] or "they"),
                               name=row["child_name"], texts=T)
    if row["status"] == "insufficient":
        data = json.loads(row["result_json"] or "{}")
        return render_template("free_result.html", insufficient=True,
                               reason=data.get("insufficient_reason", ""),
                               reason_key=row["reason_key"], token=token,
                               name=row["child_name"], texts=T)
    if row["status"] != "done":
        return render_template("free_result.html", failed=True, token=token,
                               name=row["child_name"], texts=T)

    a = FreeAnalysis.model_validate(json.loads(row["result_json"]))
    name, address = row["child_name"], (row["address_form"] or "they")

    # The authored paragraphs are emitted by the SERVER on the model's flag - fixed
    # wording in the model's mouth drifts between runs.
    notes = []
    if "sparse" in a.flags:
        notes += [T.g(p.replace("{name}", name), address) for p in T.SPARSE_PARAGRAPHS]
    if "coloring" in a.flags:
        notes.append(T.g(T.COLORING_PARAGRAPH, address))
    if a.concern_correlate_visible is False:
        notes.insert(0, T.MISMATCH_PARAGRAPH)

    source = None
    if a.hypothesis:
        from config.free_keys import source_for
        source = source_for(a.hypothesis.key)

    # A coloring page does NOT get the selling close: the parent is one step from giving
    # us usable material, and asking for money at that step loses the drawing and the sale.
    coloring = "coloring" in a.flags
    return render_template(
        "free_result.html", a=a, name=name, token=token, notes=notes, source=source,
        selling=None if coloring else T.selling_block(name, address),
        coloring_cta=T.coloring_cta(name, address) if coloring else None,
        texts=T, has_image=bool(row["image_path"]))


@bp_free.get("/img/<token>")
def image(token: str):
    """The uploaded drawing, served only to the browser that uploaded it. Not indexed,
    not guessable, and gone once retention has deleted the file."""
    if not _owns(token):
        abort(403)
    row = get_db().execute("SELECT image_path FROM free_analyses WHERE token = ?",
                           (token,)).fetchone()
    if row is None or not row["image_path"]:
        abort(404)
    p = Path(row["image_path"])
    if not p.exists():
        abort(404)
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    return Response(p.read_bytes(), mimetype=mime,
                    headers={"Cache-Control": "private, max-age=600"})


@bp_free.post("/to-order/<token>")
def to_order(token: str):
    """Move from the free reading into the paid order form, carrying the token so the
    purchase can be attributed to the analysis it came from. The indirect joins (email,
    visitor_id) stay, but they are guesswork; this is the only exact link."""
    track_event("free_to_order")
    return redirect(url_for("main.order", free=token))
