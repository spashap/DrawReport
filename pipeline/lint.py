"""Report linter: a programmatic backstop for the delivery rules (philosophy 2.3).

The prompt alone isn't 100% - sampling drifts. After the JSON validates, the report
is scanned; violations are fixed by a repair call (pipeline/llm.py).

PIVOT (2.3): the linter NO LONGER word-bans terms about states/emotions/character -
those are now legitimate product depth (zone 2/3). Instead it checks for the SAFE
FRAME around such interpretation, and catches only what's forbidden ALWAYS.

Two rule classes:
  A. HARD_BANNED - always a violation, the frame does NOT rescue (bare diagnosis-as-fact,
     command tone, catastrophizing, fate-as-fact, hidden-trauma, brand-banned verbatim).
  B. REQUIRES_FRAME - sensitive terms (anxiety/character/mood…) are NOT a violation by
     themselves; a violation only if they appear WITHOUT a safe frame nearby:
       - HEAVY (clinical) terms need BOTH a hypothesis hedge AND an attribution;
       - LIGHT traits/states need a hypothesis hedge, OR the term is about the ARTWORK
         (the character OF THE LINE, the mood OF THE DRAWING - an artifact, not the child).

Conditions 3 (visible detail) and 4 (return-to-the-child) aren't reliably regex-detectable -
the prompt carries them; the linter checks the detectable 1-2 (hedge + attribution).
Repair (pipeline/llm.py) is written as "ADD the frame / soften", never "delete".
US calibration: HARD ban set is wider and the frame-check is strict.
Per-locale dicts; adding a language = add its lists, no logic change.
"""
from __future__ import annotations

import re

from config import settings

# --- A. ALWAYS forbidden (the frame does not help) ------------------------------
HARD_BANNED = {
    "en": [
        # brand-banned verbatim
        (r"emotional\s+intelligence", "forbidden: 'emotional intelligence'"),
        (r"\bgood\s+taste\b", "forbidden: 'good taste'"),
        (r"bas[ie]s?\s+for\s+(?:a\s+)?(?:beautiful|neat|good)\s+handwriting",
         "forbidden: 'a basis for beautiful handwriting'"),
        # command / pressuring tone
        (r"\byou\s+must\b", "command tone - write 'you could offer / you might try'"),
        (r"\b(?:be|make)\s+sure\s+to\b", "command tone - soften to 'you could'"),
        (r"\byou\s+have\s+to\b", "command tone - soften"),
        (r"\bdefinitely\b", "pressuring tone - soften"),
        # fate / talent as fact
        (r"(?:will|going\s+to|destined\s+to)\s+(?:be|become)\s+(?:an?\s+)?"
         r"(?:artist|designer|painter|illustrator|writer|author)",
         "prediction of future talent is forbidden"),
        (r"has\s+the\s+makings\s+of", "fate-as-fact ('has the makings of') is forbidden"),
        (r"(?:profession|career)\s+\w+\s+(?:suits|fits|is\s+right\s+for)\s+(?:her|him|them|the\s+child)",
         "fate-as-fact career prediction is forbidden"),
        # bare diagnosis / state-as-fact (not a hypothesis)
        (r"(?:the\s+)?(?:child|she|he|they)\s+(?:has|have)\s+"
         r"(?:anxiety|depression|a\s+neurosis|low\s+self[-\s]?esteem|high\s+self[-\s]?esteem)",
         "bare diagnosis/state-as-fact - forbidden even with a frame"),
        (r"(?:the\s+drawing|this|it)\s+shows\s+(?:that\s+)?(?:the\s+)?child\s+is\s+"
         r"(?:unhappy|sad|depressed|anxious|aggressive|lonely|withdrawn|troubled)",
         "state-as-fact - forbidden; only a framed hypothesis"),
        (r"this\s+means\s+(?:that\s+)?(?:the\s+)?child", "'this means the child…' - verdict-as-fact forbidden"),
        # detecting hidden problems / clinical assessment
        (r"hidden\s+(?:trauma|problem|disorder|issue)", "scary reading 'hidden trauma/problem' is forbidden"),
        (r"(?:detect|uncover|diagnose)\s+(?:a\s+)?(?:hidden\s+)?(?:trauma|disorder|problem)",
         "we reveal what the child expresses; we never detect hidden problems"),
        # catastrophizing
        (r"serious\s+problem", "catastrophizing is forbidden"),
        (r"(?:see|consult|visit)\s+a\s+(?:doctor|specialist|psychologist)\s+(?:urgently|immediately|right\s+away)",
         "catastrophizing/panic is forbidden"),
        # fix/cure framing
        (r"\b(?:fix|cure|treat|heal)\s+(?:the\s+)?(?:problem|child|issue)\b",
         "we help understand and support, never treat/fix"),
        # color/symbol fortune-telling
        (r"(?:black|dark\s+colou?rs?|red)\s+(?:means?|=|indicates?|signals?|represents?)\s+"
         r"(?:depression|sadness|anger|aggression|fear)",
         "color/symbol fortune-telling is forbidden"),
    ],
}

# --- B. Sensitive terms: a violation only WITHOUT a frame -----------------------
# HEAVY (clinical) - need BOTH a hedge AND an attribution when about the child.
HEAVY_TERMS = {
    "en": re.compile(
        r"\banxiet\w*|\banxious\b|\bdepress\w*|\bneuros\w*|\btrauma\w*|\baggress\w*|"
        r"\bphobi\w*|\bsuicid\w*", re.IGNORECASE),
}
# LIGHT traits/states - need a hedge, OR the term is about the artwork itself.
LIGHT_TERMS = {
    "en": re.compile(
        r"self[-\s]?esteem|temperament|\bcharacter\b|\bmood\b|\bshy\b|\binsecur\w*|"
        r"\blonel\w*|\bsad\b|\bsadness\b|\banger\b|\bangry\b|\bfear\b|\bpersonality\b|"
        r"withdrawn|inner\s+(?:world|strength|state|life)", re.IGNORECASE),
}
# hypothesis hedge (frame condition 2) - broad, so already-correct hypotheses don't false-positive.
HEDGE = {
    "en": re.compile(
        r"\bmay\s+(?:suggest|indicate|reflect|be|mean|hint|point|speak)|"
        r"\bmight\s+(?:suggest|indicate|reflect|be|mean|hint)|"
        r"\bcan\s+be\s+read\s+as|\bcould\s+(?:suggest|be|reflect|mean)|"
        r"\bis\s+sometimes\s+(?:associated|read|linked)|\boften\s+(?:associated|read|linked)|"
        r"\blooks?\s+like|\bgives?\s+(?:the\s+)?impression|\bseems?\s+to|\bappears?\s+to|"
        r"\bone\s+reading|read\s+this\s+way|a\s+hypothesis|not\s+a\s+conclusion|"
        r"\bas\s+if\b|\bperhaps\b|\bmaybe\b", re.IGNORECASE),
}
# attribution to a tradition/author (frame condition 1)
ATTRIBUTION = {
    "en": re.compile(
        r"projective|tradition|approach|Machover|Lowenfeld|Vygotsky|Piaget|Kellogg|"
        r"Goodnow|Burkitt|according\s+to|in\s+the\s+\w+\s+tradition|developmental\s+tradition",
        re.IGNORECASE),
}
# the term refers to the ARTWORK (character OF THE LINE, mood OF THE DRAWING), not the child:
# look for an artifact-noun right after the term (narrow window), not anywhere in context.
WORK_REF = {
    "en": re.compile(
        r"\b(?:of\s+(?:the\s+)?)?(?:work|drawing|picture|scene|story|plot|composition|"
        r"line|stroke|brush|colou?r|landscape|character|hero|figure|image|sky|"
        r"background|atmosphere|palette|weather)\b", re.IGNORECASE),
}
_WORK_LOOKAHEAD = 40  # chars after the term where an artifact-noun clears the claim

# global contexts in which a match is NOT a violation
ALLOWED_CONTEXTS = {
    "en": [
        "not a diagnosis", "isn't a diagnosis", "is not a diagnosis", "without diagnos",
        "not a psychological", "not a medical", "we don't diagnose", "do not diagnose",
        "not an assessment", "educational observation",
    ],
}

_WINDOW = 220  # chars each side of the term - the frame-check window

# interpretation prose (full scan: HARD + frame-check)
_FRAME_FIELDS = ("introduction", "about_child", "conclusion")
# context paraphrase + idea/task lists get HARD bans ONLY (no frame-check): context_summary
# is a paraphrase of the parent's words; recommendations and development_directions are
# ideas/tasks where "the cat's mood", "the character's character" are legitimate.


def _loc(locale: str | None) -> str:
    return locale if locale in HARD_BANNED else settings.DEFAULT_LOCALE


def _hard_scan(text: str, where: str, loc: str) -> list[dict]:
    hits = []
    allowed = ALLOWED_CONTEXTS.get(loc, [])
    for pattern, why in HARD_BANNED[loc]:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            s, e = max(0, m.start() - 80), min(len(text), m.end() + 80)
            ctx = text[s:e]
            if any(a in ctx.lower() for a in allowed):
                continue
            hits.append({"where": where, "match": m.group(0), "why": why, "context": ctx})
    return hits


def _frame_scan(text: str, where: str, loc: str) -> list[dict]:
    """Sensitive terms without a safe frame nearby."""
    hits = []
    allowed = ALLOWED_CONTEXTS.get(loc, [])
    hedge_re, attr_re, work_re = HEDGE[loc], ATTRIBUTION[loc], WORK_REF[loc]
    for term_re, heavy in ((HEAVY_TERMS[loc], True), (LIGHT_TERMS[loc], False)):
        for m in re.finditer(term_re, text):
            s, e = max(0, m.start() - _WINDOW), min(len(text), m.end() + _WINDOW)
            window = text[s:e]
            wl = window.lower()
            if any(a in wl for a in allowed):
                continue
            # the term describes the artwork itself ("an anxious sky", "the mood of the drawing")
            after = text[m.end():m.end() + _WORK_LOOKAHEAD]
            if work_re.search(after):
                continue
            has_hedge = bool(hedge_re.search(window))
            has_attr = bool(attr_re.search(window))
            if heavy:
                if has_hedge and has_attr:
                    continue
                why = ("interpretation of a heavy/clinical state without the full frame - needs "
                       "BOTH an attribution to a real tradition/author AND a hypothesis hedge; "
                       "ADD the frame or soften, do NOT delete the meaning")
            else:
                if has_hedge:
                    continue
                why = ("interpretation of a child's trait/state without a hypothesis hedge - "
                       "phrase it as a hypothesis ('may suggest…') with a return to the child; "
                       "do NOT delete the meaning")
            ctx = text[max(0, m.start() - 80):min(len(text), m.end() + 80)]
            hits.append({"where": where, "match": m.group(0), "why": why, "context": ctx})
    return hits


def _scan(text: str, where: str, loc: str) -> list[dict]:
    return _hard_scan(text, where, loc) + _frame_scan(text, where, loc)


def find_violations(report_data: dict, locale: str | None = None) -> list[dict]:
    """report_data - dict of a validated report (model_dump)."""
    loc = _loc(locale)
    hits: list[dict] = []
    # --- interpretation fields: HARD + frame-check ---
    for f in _FRAME_FIELDS:
        if report_data.get(f):
            hits.extend(_scan(str(report_data[f]), f, loc))
    for i, d in enumerate(report_data.get("dimensions") or []):
        for f in ("observation", "research_note"):
            if d.get(f):
                hits.extend(_scan(str(d[f]), f"dimensions[{i}].{f} ({d.get('title')})", loc))
    for i, sp in enumerate(report_data.get("specialists") or []):
        if sp.get("reason"):
            hits.extend(_scan(str(sp["reason"]), f"specialists[{i}].reason", loc))
    # --- context paraphrase + idea/task lists: HARD bans only ---
    if report_data.get("context_summary"):
        hits.extend(_hard_scan(str(report_data["context_summary"]), "context_summary", loc))
    for field in ("understanding_recommendations", "art_recommendations"):
        for i, r in enumerate(report_data.get(field) or []):
            hits.extend(_hard_scan(str(r), f"{field}[{i}]", loc))
    for i, dd in enumerate(report_data.get("development_directions") or []):
        hits.extend(_hard_scan(str(dd.get("text", "")), f"development_directions[{i}]", loc))
    return hits
