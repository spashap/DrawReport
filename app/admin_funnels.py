"""Funnels by VISIT: the doors of the site.

What was wrong before. The old funnel (`FUNNEL_STEPS` in admin.py) counted nine
INDEPENDENT sets of unique visitors over a period and divided one by another. Three
problems followed: a step could come out larger than the one before it; a person who
came five times in a month counted as one; and the last steps (payment, report
delivery) arrive from the worker with no visitor_id at all and ended up in the same
table through a COALESCE trick.

Here the unit is the VISIT (web_visits, a 30-minute window), and there are steps of
two DIFFERENT kinds:

  * OBSERVATION step (`path`) - "scrolled as far as the pricing". Skipping one is
    MEANINGFUL: a person may have arrived on a direct link straight to the order form,
    and crediting them with "saw the pricing" just to get a tidy decreasing table would
    be a lie. These are counted as they are, with no filling-in.
  * GATE step (`gate`) - "opened the form", "reached checkout", "paid". You cannot pass
    one without the previous ones, so here we fill in from the deepest gate reached: a
    beacon that never arrived must not tear the funnel apart. Within the gate block
    nesting is guaranteed by construction.

Because of this the observation block and the gate block are counted separately, and
the transition between them can exceed 100% - not an error but a finding: that many
people arrived at the order form without ever seeing the landing.

"Paid" is taken from the ORDER (orders.visit_id + paid_at), not from an event: payment
is confirmed by a PayPal webhook, in which there is no browser and no visit at all.
"""
from __future__ import annotations

NOT_BOT = "(v.device IS NULL OR v.device <> 'bot')"

PATH, GATE = "path", "gate"

# (label, marker, kind). The marker is an event name, or a prefix ending in '*'.
PAID_STEPS: list[tuple[str, str, str]] = [
    ("Opened the product page", "landing_view", PATH),
    ("Stayed (scroll / 15s)", "engaged", PATH),
    ("Scrolled halfway", "click:scroll_50", PATH),
    ("Reached the pricing", "click:sec_pricing", PATH),
    ("Opened the order form", "order_form_view", GATE),
    ("Started filling it in", "form_started", GATE),
    ("Created an order", "order_created", GATE),
    ("Reached checkout", "checkout_view", GATE),
]

# The free door: the home page wizard. Its steps land in phase 4; the door is defined
# here so that shipping the wizard lights it up without touching this module.
FREE_STEPS: list[tuple[str, str, str]] = [
    ("Opened the home page", "home_view", PATH),
    ("Stayed (scroll / 15s)", "engaged", PATH),
    ("Reached the wizard", "free_view", GATE),
    ("Entered name and age", "click:free_step1", GATE),
    ("Chose what worries them", "click:free_concern_*", GATE),
    ("Reached the summary", "free_summary", GATE),
    ("Sent a drawing", "free_upload", GATE),
    ("Opened the finished analysis", "free_result_view", GATE),
    ("Clicked “get the full report”", "click:free_to_order", GATE),
    ("Created an order", "order_created", GATE),
]

DOORS = [
    ("paid", "Paid door - the product page", PAID_STEPS, "landing_view"),
    ("free", "Free door - the home page wizard", FREE_STEPS, "home_view"),
]


def _visit_types(db, since: str) -> dict[str, dict]:
    """{visit_id: {types, device, channel, screen_w}} for the period, bots excluded."""
    out: dict[str, dict] = {}
    for r in db.execute(
            "SELECT v.visit_id, v.device, v.channel, v.screen_w FROM web_visits v"
            f" WHERE v.started_at >= ? AND {NOT_BOT}", (since,)):
        out[r["visit_id"]] = {"types": set(), "device": r["device"] or "-",
                              "channel": r["channel"] or "direct",
                              "screen_w": r["screen_w"]}
    if not out:
        return out
    for r in db.execute(
            "SELECT DISTINCT visit_id, type FROM events"
            " WHERE visit_id IS NOT NULL AND created_at >= ?", (since,)):
        v = out.get(r["visit_id"])
        if v is not None:
            v["types"].add(r["type"])
    return out


def _orders_by_visit(db, since: str) -> dict[str, dict]:
    """Orders placed WITHIN a visit. Payment arrives later and outside the visit, so we
    take it from the order itself - "paid" does not depend on a browser being open."""
    out: dict[str, dict] = {}
    for r in db.execute(
            "SELECT visit_id, COUNT(*) n,"
            " SUM(CASE WHEN paid_at IS NOT NULL THEN 1 ELSE 0 END) paid,"
            " COALESCE(SUM(CASE WHEN paid_at IS NOT NULL THEN price_cents ELSE 0 END), 0) c"
            " FROM orders WHERE visit_id IS NOT NULL AND created_at >= ?"
            " GROUP BY visit_id", (since,)):
        out[r["visit_id"]] = {"n": r["n"], "paid": r["paid"] or 0,
                              "usd": (r["c"] or 0) // 100}
    return out


def _has(types: set[str], marker: str) -> bool:
    if marker.endswith("*"):
        return any(t.startswith(marker[:-1]) for t in types)
    return marker in types


def _is_mobile(v: dict) -> bool:
    """By NARROW SCREEN when the client reported one, otherwise by user-agent: layout
    breaks by width, and the UA knows about neither a narrow window nor a tablet held
    in desktop mode."""
    sw = v["screen_w"] or 0
    return (0 < sw < 640) if sw else (v["device"] == "mobile")


def _funnel(visits: dict, orders: dict, steps: list, entry_marker: str) -> dict:
    """One door. entry_marker is what makes a visit part of this funnel."""
    rows = [{"label": label, "kind": kind, "n": 0, "mobile": 0, "desktop": 0}
            for label, _m, kind in steps]
    rows.append({"label": "Paid", "kind": GATE, "n": 0, "mobile": 0, "desktop": 0})
    gate_idx = [i for i, (_l, _m, k) in enumerate(steps) if k == GATE]
    total, revenue = 0, 0

    for vid, v in visits.items():
        if not _has(v["types"], entry_marker):
            continue
        total += 1
        mob = _is_mobile(v)
        o = orders.get(vid)

        def hit(i: int) -> None:
            rows[i]["n"] += 1
            rows[i]["mobile" if mob else "desktop"] += 1

        # 1. Observations - as they are, no filling-in.
        for i, (_l, marker, kind) in enumerate(steps):
            if kind == PATH and _has(v["types"], marker):
                hit(i)
        # 2. Gates - by the deepest one reached; an order by itself proves that every
        #    gate up to and including "created an order" was passed, and a PAID order
        #    proves every gate in the door was passed (you cannot pay without reaching
        #    checkout). Without the paid case, a visit whose checkout_view beacon never
        #    arrived showed up as "paid" but not "reached checkout", so the Paid row
        #    came out larger than the row above it - the exact non-nesting this module
        #    exists to prevent.
        deepest = -1
        for i in gate_idx:
            if _has(v["types"], steps[i][1]):
                deepest = i
        if o:
            created = [i for i in gate_idx if steps[i][1] == "order_created"]
            if created:
                deepest = max(deepest, created[0])
            if o["paid"] and gate_idx:
                deepest = max(deepest, gate_idx[-1])
        for i in gate_idx:
            if i <= deepest:
                hit(i)
        # 3. Payment - from the order only.
        if o and o["paid"]:
            hit(len(rows) - 1)
            revenue += o["usd"]

    out, prev = [], None
    first = rows[0]["n"] if rows else 0
    for r in rows:
        out.append({
            **r,
            "pct_prev": f"{r['n'] / prev * 100:.0f}%" if prev else "",
            "pct_top": f"{r['n'] / first * 100:.1f}%" if first else "",
            "lost": (prev - r["n"]) if prev is not None and prev > r["n"] else 0,
        })
        prev = r["n"] or None
    return {"steps": out, "visits": total, "revenue": revenue}


def build(db, since: str) -> dict:
    """Every door + a summary of visits for the period."""
    visits = _visit_types(db, since)
    orders = _orders_by_visit(db, since)

    devices: dict[str, int] = {}
    channels: dict[str, dict] = {}
    for vid, v in visits.items():
        devices[v["device"]] = devices.get(v["device"], 0) + 1
        ch = channels.setdefault(v["channel"], {"visits": 0, "orders": 0,
                                                "paid": 0, "usd": 0})
        ch["visits"] += 1
        o = orders.get(vid)
        if o:
            ch["orders"] += o["n"]
            ch["paid"] += o["paid"]
            ch["usd"] += o["usd"]
    return {
        "doors": [{"key": key, "title": title,
                   **_funnel(visits, orders, steps, entry)}
                  for key, title, steps, entry in DOORS],
        "visits_total": len(visits),
        "devices": sorted(devices.items(), key=lambda kv: -kv[1]),
        "channels": sorted(channels.items(), key=lambda kv: -kv[1]["visits"]),
    }
