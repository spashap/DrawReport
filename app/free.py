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
from app.free_retention import cap_reached, email_cap_reached
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
        limit_title=T.LIMIT_TITLE.format(name_poss=T.possessive(name)),
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
        # Also goes through _upload_failed so it lands in the same "why uploads were
        # refused" table as every other refusal. Reporting it only under its own event
        # name would leave a hole in exactly the table built to have no holes.
        return _upload_failed("cap", {"error": "cap"}, 429)

    addr = (request.form.get("email") or "").strip().lower()
    if not EMAIL_RE.match(addr):
        return _upload_failed("email", {"error": "email"}, 400)
    # Per-address allowance, checked after the address is known but still BEFORE the file
    # is read or written: a refused upload must not cost us a disk write or a model call.
    if email_cap_reached(db, addr):
        track_event("free_email_cap_hit")
        return _upload_failed("email_cap", {"error": "email_cap"}, 429)

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
    interp_id = None
    if a.hypothesis:
        from config.free_keys import source_for
        source = source_for(a.hypothesis.key)
        got = db.execute(
            "SELECT id, parent_vote FROM free_interpretations WHERE analysis_id = ?"
            " ORDER BY id DESC LIMIT 1", (row["id"],)).fetchone()
        if got is not None and got["parent_vote"] is None:
            interp_id = got["id"]

    # A coloring page does NOT get the selling close: the parent is one step from giving
    # us usable material, and asking for money at that step loses the drawing and the sale.
    coloring = "coloring" in a.flags
    return render_template(
        "free_result.html", a=a, name=name, token=token, notes=notes, source=source,
        selling=None if coloring else T.selling_block(name, address),
        coloring_cta=T.coloring_cta(name, address) if coloring else None,
        texts=T, has_image=bool(row["image_path"]), interp_id=interp_id)


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


@bp_free.post("/vote/<int:interp_id>")
def vote(interp_id: int):
    """The parent's verdict on ONE interpretation, not on the reading as a whole.

    Tied to the interpretation rather than the analysis on purpose: "was this reading any
    good" averages a warm opening with a shaky interpretation and grades neither. The key
    is what the library is built from, so the key is what has to be judged."""
    db = get_db()
    row = db.execute(
        "SELECT i.id, a.token FROM free_interpretations i"
        " JOIN free_analyses a ON a.id = i.analysis_id WHERE i.id = ?",
        (interp_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not_found"}), 404
    if not _owns(row["token"]):
        abort(403)
    v = (request.form.get("vote") or "").strip().lower()
    if v not in ("yes", "no"):
        return jsonify({"error": "bad_vote"}), 400
    db.execute("UPDATE free_interpretations SET parent_vote = ?, voted_at = ?"
               " WHERE id = ?", (v, now(), interp_id))
    db.commit()
    track_event("free_vote", {"vote": v})
    return jsonify({"ok": True})


@bp_free.post("/to-order/<token>")
def to_order(token: str):
    """Move from the free reading into the paid order form, carrying the token so the
    purchase can be attributed to the analysis it came from. The indirect joins (email,
    visitor_id) stay, but they are guesswork; this is the only exact link.

    The token travels in a first-party httponly cookie, NOT in the query string. It used
    to be /en/order?free=<token>, and that URL went to GA4 and the Meta Pixel as the page
    location: the token is the only key to the page showing the child's drawing."""
    track_event("free_to_order")
    resp = redirect(url_for("main.order"))
    if get_db().execute("SELECT 1 FROM free_analyses WHERE token = ?",
                        (token,)).fetchone():
        set_order_free_cookie(resp, token)
    return resp


# --- Free -> paid handoff ----------------------------------------------------------

ORDER_FREE_COOKIE = "dr_order_free"     # which free reading the order form continues
ORDER_FREE_MAX_AGE = 6 * 3600
_TOKEN_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def valid_token_shape(token: str | None) -> bool:
    return bool(token) and len(token) <= 64 and set(token) <= _TOKEN_CHARS


def set_order_free_cookie(resp, token: str):
    resp.set_cookie(ORDER_FREE_COOKIE, token, max_age=ORDER_FREE_MAX_AGE,
                    httponly=True, samesite="Lax", secure=request.is_secure)
    return resp


def clear_order_free_cookie(resp):
    resp.delete_cookie(ORDER_FREE_COOKIE)
    return resp


def order_free_token() -> str | None:
    """The free-reading token the order form continues, from the cookie only. Only its
    SHAPE is checked here; what it may unlock is decided by order_handoff()."""
    t = request.cookies.get(ORDER_FREE_COOKIE)
    return t if valid_token_shape(t) else None


def order_handoff(token: str | None) -> dict | None:
    """What the paid order form may reuse from a free reading, or None.

    Gated exactly like the drawing itself (free.image): only the browser that uploaded it
    (_owns), because the prefill shows the drawing and the parent's email. A token alone -
    say a forwarded result link on another device - still attributes the order, but
    reuses nothing. Only a finished reading qualifies: an image rejected as 'not a
    drawing' must not become the basis of a paid report.

    The file path comes from our own DB row and must resolve inside FREE_DIR; nothing
    from the request ever names a file."""
    if not valid_token_shape(token) or not _owns(token):
        return None
    row = get_db().execute(
        "SELECT child_name, address_form, email, image_path, status FROM free_analyses"
        " WHERE token = ?", (token,)).fetchone()
    if row is None or row["status"] != "done" or not row["image_path"]:
        return None
    p = Path(row["image_path"]).resolve()
    try:
        p.relative_to(Path(settings.FREE_DIR).resolve())
    except ValueError:
        return None
    if not p.is_file() or p.suffix.lower() not in ALLOWED_EXT:
        return None
    gender = {"she": "f", "he": "m"}.get(row["address_form"] or "")
    return {"token": token, "name": row["child_name"], "gender": gender,
            "email": row["email"] or "", "path": p}


def handoff_thumb(handoff: dict) -> str | None:
    """A small inline JPEG of the reused drawing. Inline on purpose: a /free/img/<token>
    src would put the token back into the order page's markup."""
    import base64
    from pipeline.images import prepare_image
    try:
        jpeg = prepare_image(handoff["path"], max_side=480)
    except Exception:          # HEIC without a decoder, a damaged file: say so in text
        return None
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")


def materialize_free_drawing(handoff: dict):
    """The saved free drawing as an upload, so validate_and_create_order() treats it
    exactly like a file the parent chose (same size and format checks, same save path).
    Ported from Golos app/free.py: orders.py needs no change."""
    import io
    from werkzeug.datastructures import FileStorage
    p: Path = handoff["path"]
    return FileStorage(stream=io.BytesIO(p.read_bytes()), name="d1_file",
                       filename=f"drawing{p.suffix.lower()}")


@bp_free.after_request
def _no_referrer_from_private(resp):
    """A reading's URL is its only key. Without this, the next page's document.referrer
    (sent to GA4 as `dr` and to Meta as `rl`) would be /free/r/<token>."""
    if request.path.startswith(("/free/r/", "/free/to-order/", "/free/img/",
                                "/free/status/")):
        resp.headers["Referrer-Policy"] = "no-referrer"
    return resp
