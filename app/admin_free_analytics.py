"""Freemium analytics: how far people get, what they pick, and who buys afterwards.

A separate module rather than another two hundred lines in admin.py: only COUNTING lives
here (SQL + aggregation), so the route stays thin.

TWO UNITS OF MEASURE, AND THEY MUST NOT BE MIXED IN ONE COLUMN:
  * visitors - wizard steps that leave no row in the database (button clicks arrive by
    the /t/e beacon and live in events as 'click:<goal>');
  * questionnaires - rows in free_analyses (one row = one completed set of questions; one
    person can complete it twice).
That is why the funnel is split into two tables rather than glued into one tidy-looking
one that would answer neither question.

The period is the date of the QUESTIONNAIRE (a cohort). Purchases by that cohort are
counted with NO date limit: the question is "did they buy at all", not "did they buy the
same day".
"""
from __future__ import annotations

import datetime
import json

from config import free_texts as T

CLICK = "click:"
NOT_BOT = "(device IS NULL OR device <> 'bot')"

# Statuses meaning "a drawing was uploaded" (the questionnaire reached the model).
UPLOADED = ("queued", "generating", "done", "insufficient", "failed")


def _visitors(db, type_sql: str, params: tuple, since: str) -> int:
    """Unique PEOPLE with such an event in the period."""
    return db.execute(
        "SELECT COUNT(DISTINCT visitor_id) c FROM events"
        f" WHERE visitor_id IS NOT NULL AND {NOT_BOT} AND {type_sql}"
        " AND created_at >= ?", (*params, since)).fetchone()["c"]


def dashboard_counters(db, since: str) -> dict:
    """The freemium block on the main Analytics tab.

    The split that matters: N completed the questions, of whom some left ONLY an email
    ("no drawing to hand") and some actually brought a drawing. Merging those two hides
    the single most actionable number in the funnel.
    """
    row = db.execute(
        "SELECT COUNT(*) total,"
        " SUM(CASE WHEN status = 'draft' AND email IS NOT NULL THEN 1 ELSE 0 END) email_only,"
        " SUM(CASE WHEN status <> 'draft' THEN 1 ELSE 0 END) requested,"
        " SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) done,"
        " SUM(CASE WHEN status = 'draft' AND email IS NULL THEN 1 ELSE 0 END) dropped"
        " FROM free_analyses WHERE created_at >= ?", (since,)).fetchone()
    return {
        "total": row["total"] or 0,
        "email_only": row["email_only"] or 0,
        "requested": row["requested"] or 0,
        "done": row["done"] or 0,
        "dropped": row["dropped"] or 0,
        "openers": _visitors(db, "type = ?", ("free_view",), since),
    }


# --- Attribution: free reading -> purchase -----------------------------------------
# In descending order of precision: a direct move from the reading (orders.free_token,
# written in routes.order_submit) is exact; email and visitor_id are matches by
# coincidence and can be wrong (a shared computer, someone else's address), so they are
# shown separately rather than folded into one number.
ATTR_LABELS = {"direct": "came from the reading",
               "email": "same email",
               "visitor": "same visitor"}


def _attribute_orders(db, rows) -> tuple[dict, list]:
    """Who in the cohort went on to a paid order.

    An order belongs to exactly ONE questionnaire - the latest one created no later than
    the order. Otherwise one person with two readings would produce two "purchases" out
    of a single sale.
    """
    if not rows:
        return {}, []
    by_token = {r["token"]: r for r in rows}
    by_email: dict[str, list] = {}
    by_visitor: dict[str, list] = {}
    for r in rows:
        if r["email"]:
            by_email.setdefault(r["email"].strip().lower(), []).append(r)
        if r["visitor_id"]:
            by_visitor.setdefault(r["visitor_id"], []).append(r)

    orders = db.execute(
        "SELECT id, email, visitor_id, free_token, product_code, price_cents,"
        " status, created_at, paid_at FROM orders ORDER BY id").fetchall()

    def _latest_before(candidates, when):
        pick = None
        for c in candidates:
            if c["created_at"] <= when and (pick is None
                                            or c["created_at"] > pick["created_at"]):
                pick = c
        return pick

    per_analysis: dict[int, list] = {}
    pairs: list[dict] = []
    for o in orders:
        analysis, kind = None, ""
        if o["free_token"] and o["free_token"] in by_token:
            analysis, kind = by_token[o["free_token"]], "direct"
        elif o["email"] and o["email"].strip().lower() in by_email:
            analysis = _latest_before(by_email[o["email"].strip().lower()], o["created_at"])
            kind = "email"
        elif o["visitor_id"] and o["visitor_id"] in by_visitor:
            analysis = _latest_before(by_visitor[o["visitor_id"]], o["created_at"])
            kind = "visitor"
        if analysis is None:
            continue
        per_analysis.setdefault(analysis["id"], []).append(o)
        pairs.append({
            "analysis_id": analysis["id"],
            "child": analysis["child_name"],
            "concern": concern_label(analysis["concern_key"]),
            "free_at": (analysis["created_at"] or "")[:16].replace("T", " "),
            "kind": kind, "kind_label": ATTR_LABELS[kind],
            "order_id": o["id"], "product": o["product_code"],
            "order_at": (o["created_at"] or "")[:16].replace("T", " "),
            "status": o["status"], "paid": bool(o["paid_at"]),
            "usd": (o["price_cents"] or 0) // 100,
            "lag_days": _lag_days(analysis["created_at"], o["created_at"]),
        })
    pairs.sort(key=lambda p: p["order_id"], reverse=True)
    return per_analysis, pairs


def _lag_days(a: str | None, b: str | None) -> str:
    if not a or not b:
        return ""
    try:
        d = (datetime.date.fromisoformat(b[:10])
             - datetime.date.fromisoformat(a[:10])).days
    except ValueError:
        return ""
    return "same day" if d <= 0 else f"+{d}d"


def _label(options: list[dict], key: str | None) -> str:
    for o in options:
        if o["key"] == key:
            return T.g(o["label"], "they")
    return key or "-"


def concern_label(key: str | None) -> str:
    """The concern's label for admin lists, where `black` says nothing on its own."""
    return _label(T.CONCERNS, key)


def purchases_index(db, rows) -> dict:
    """{analysis id: [purchases]} for admin lists. The SAME attribution as the Freemium
    page - two different answers to "did this person buy" must not exist in one admin."""
    per: dict[int, list] = {}
    for p in _attribute_orders(db, rows)[1]:
        per.setdefault(p["analysis_id"], []).append(p)
    return per


def _breakdown(rows, key_fn, order: list[tuple[str, str]], buyers: dict,
               paid_ids: set) -> list[dict]:
    """One "option -> how many chose it and how far they got" table.

    `order` fixes the ORDER and the labels (as on the wizard screen), not just the wording:
    options nobody chose must stay visible - a zero is an answer too.
    """
    buckets = {k: {"key": k, "label": lbl, "n": 0, "uploaded": 0, "done": 0,
                   "orders": 0, "paid": 0} for k, lbl in order}
    for r in rows:
        k = key_fn(r)
        if k is None:
            continue
        b = buckets.get(k)
        if b is None:
            b = buckets[k] = {"key": k, "label": k, "n": 0, "uploaded": 0,
                              "done": 0, "orders": 0, "paid": 0}
        b["n"] += 1
        if r["status"] in UPLOADED:
            b["uploaded"] += 1
        if r["status"] == "done":
            b["done"] += 1
        got = buyers.get(r["id"]) or []
        if got:
            b["orders"] += 1
            if any(o["id"] in paid_ids for o in got):
                b["paid"] += 1
    total = sum(b["n"] for b in buckets.values()) or 1
    return [{**b, "share": f"{b['n'] / total * 100:.0f}%",
             "to_upload": f"{b['uploaded'] / b['n'] * 100:.0f}%" if b["n"] else "-"}
            for b in buckets.values()]


def _steps(items: list[tuple[str, int, str]]) -> list[dict]:
    out, prev, top = [], None, None
    for label, n, note in items:
        if top is None:
            top = n
        out.append({"label": label, "n": n, "note": note,
                    "pct_prev": f"{n / prev * 100:.0f}%" if prev else "",
                    "pct_top": f"{n / top * 100:.0f}%" if top else ""})
        prev = n or None
    return out


def _flags_of(row) -> list[str]:
    """The model's flags live inside result_json, not in a column of their own."""
    try:
        return json.loads(row["result_json"] or "{}").get("flags") or []
    except (ValueError, TypeError):
        return []


def page_data(db, since: str) -> dict:
    """Everything the Freemium page shows."""
    rows = db.execute(
        "SELECT id, token, visitor_id, email, child_name, age, concern_key, duration_key,"
        " address_form, parent_text, status, reason_key, result_json, created_at"
        " FROM free_analyses WHERE created_at >= ? ORDER BY id", (since,)).fetchall()

    voted_ids = {r["analysis_id"] for r in db.execute(
        "SELECT DISTINCT analysis_id FROM free_interpretations"
        " WHERE parent_vote IS NOT NULL")}
    buyers, pairs = _attribute_orders(db, rows)
    paid_ids = {p["order_id"] for p in pairs if p["paid"]}

    n_total = len(rows)
    n_uploaded = sum(1 for r in rows if r["status"] in UPLOADED)
    n_done = sum(1 for r in rows if r["status"] == "done")
    n_voted = sum(1 for r in rows if r["id"] in voted_ids)
    n_ordered = sum(1 for r in rows if buyers.get(r["id"]))
    n_paid = sum(1 for r in rows
                 if any(o["id"] in paid_ids for o in (buyers.get(r["id"]) or [])))

    # By VISITOR: the wizard steps leave no row in the database.
    page_steps = _steps([
        ("Opened the wizard", _visitors(db, "type = ?", ("free_view",), since), "free_view"),
        ("Entered name and age",
         _visitors(db, "type = ?", (CLICK + "free_step1",), since), "the Next button"),
        ("Chose what caught their eye",
         _visitors(db, "type LIKE ?", (CLICK + "free_concern_%",), since), "step 2"),
        ("Asked for the summary",
         _visitors(db, "type = ?", (CLICK + "free_summary",), since), "the Show me button"),
        ("Opened the file picker",
         _visitors(db, "type = ?", (CLICK + "free_add_drawing",), since), "step 4"),
        ("Sent the drawing",
         _visitors(db, "type = ?", (CLICK + "free_upload_submit",), since), "upload button"),
        ("Opened the finished reading",
         _visitors(db, "type = ?", ("free_result_view",), since), "free_result_view"),
        ("Clicked through to the report",
         _visitors(db, "type = ?", (CLICK + "free_to_order",), since), "the selling close"),
    ])

    # By QUESTIONNAIRE: one row = one completed set of questions. The interpretation vote
    # is deliberately NOT a step in this chain: it is optional (a parent can buy without
    # voting) and would produce meaningless "300% of the previous step".
    form_steps = _steps([
        ("Completed the questions", n_total, "a free_analyses row"),
        ("Uploaded a drawing", n_uploaded, "status is not draft"),
        ("Got a reading", n_done, "status done"),
        ("Created a paid order", n_ordered, "attribution below"),
        ("Paid", n_paid, ""),
    ])

    stalled = [r for r in rows if r["status"] == "draft"]
    stalled_view = {"total": len(stalled),
                    "email": sum(1 for r in stalled if r["email"]),
                    "silent": sum(1 for r in stalled if not r["email"])}

    # Rejections and failures are depth too: the person reached the end and got nothing.
    rejects: dict[str, int] = {}
    for r in rows:
        if r["status"] in ("insufficient", "failed"):
            k = r["reason_key"] or r["status"]
            rejects[k] = rejects.get(k, 0) + 1
    flags: dict[str, int] = {}
    for r in rows:
        for f in _flags_of(r):
            flags[f] = flags.get(f, 0) + 1

    dur_order = [(d["key"], T.g(d["label"], "they")) for d in T.DURATIONS]
    surveys = [
        {"title": "What caught their eye (step 2)", "unit": "concern",
         "rows": _breakdown(rows, lambda r: r["concern_key"],
                            [(c["key"], c["label"]) for c in T.CONCERNS],
                            buyers, paid_ids)},
        {"title": "How long they've noticed it (step 3)", "unit": "duration",
         "hint": "Not asked on the \"nothing worries me\" path - a dash there.",
         "rows": _breakdown(rows, lambda r: r["duration_key"], dur_order,
                            buyers, paid_ids)},
        {"title": "Child's age", "unit": "band",
         "rows": _breakdown(rows, lambda r: T.age_band(r["age"] or 6),
                            list(T.BAND_LABELS.items()), buyers, paid_ids)},
        {"title": "Pronoun used in the text", "unit": "form",
         "rows": _breakdown(rows, lambda r: r["address_form"],
                            [("she", "she"), ("he", "he"), ("they", "they")],
                            buyers, paid_ids)},
        {"title": "The free-text \"what have you noticed\"", "unit": "answer",
         "rows": _breakdown(rows,
                            lambda r: "filled" if (r["parent_text"] or "").strip() else "skipped",
                            [("filled", "wrote in their own words"),
                             ("skipped", "skipped it")], buyers, paid_ids)},
    ]

    revenue = sum(p["usd"] for p in pairs if p["paid"])
    by_kind: dict[str, dict] = {}
    for p in pairs:
        b = by_kind.setdefault(p["kind"], {"label": p["kind_label"], "orders": 0,
                                           "paid": 0, "usd": 0})
        b["orders"] += 1
        if p["paid"]:
            b["paid"] += 1
            b["usd"] += p["usd"]

    engagement = {
        "voted": n_voted,
        "voted_pct": f"{n_voted / n_done * 100:.0f}%" if n_done else "-",
        "to_order_clicks": _visitors(db, "type = ?", (CLICK + "free_to_order",), since),
        "retry_clicks": _visitors(db, "type = ?", (CLICK + "free_retry",), since),
        "limit_hits": _visitors(db, "type = ?", (CLICK + "free_limit_open",), since),
        "cap_hits": _visitors(db, "type = ?", ("free_cap_hit",), since),
    }

    # Why uploads were refused. This was the biggest blind spot in the funnel: someone
    # answers everything, presses the button, hits a size or format limit - and without
    # this the step simply never happens with no reason recorded anywhere.
    upload_fails = [(r["type"], r["c"]) for r in db.execute(
        "SELECT payload_json AS type, COUNT(*) c FROM events"
        " WHERE type = 'free_upload_failed' AND created_at >= ?"
        " GROUP BY payload_json ORDER BY c DESC", (since,))]

    return {
        "total": n_total, "uploaded": n_uploaded, "done": n_done,
        "ordered": n_ordered, "paid": n_paid, "revenue": revenue,
        "engagement": engagement, "email_only": stalled_view["email"],
        "conv_done_paid": (f"{n_paid / n_done * 100:.1f}%" if n_done else "-"),
        "conv_total_paid": (f"{n_paid / n_total * 100:.1f}%" if n_total else "-"),
        "page_steps": page_steps, "form_steps": form_steps,
        "stalled": stalled_view,
        "rejects": sorted(rejects.items(), key=lambda kv: -kv[1]),
        "flags": sorted(flags.items(), key=lambda kv: -kv[1]),
        "upload_fails": upload_fails,
        "surveys": surveys, "pairs": pairs,
        "by_kind": [by_kind[k] for k in ("direct", "email", "visitor") if k in by_kind],
    }
