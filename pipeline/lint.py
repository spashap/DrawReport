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
# --- en-4.2 -----------------------------------------------------------------------
# Two rule sets with PRODUCT and LEGAL weight, enforced mechanically rather than by prompt
# text alone. The reason is measured: en-4.1's prose rules held on a short report and
# collapsed on a long one (1 em dash vs 58, same prompt, same day - UseCasesData #29). Style
# is NOT policed here by owner decision; only these two are, because they carry real weight.

# A. Skill drills. The mother bought an understanding of her child, not an occupational-
#    therapy handout. Scanned over activities / art_recommendations only.
DRILL_BANNED = {
    "en": [
        (r"\bdrills?\b|\bdot[-\s]?to[-\s]?dot\b|\bbead[-\s]?stringing\b|\bstringing\s+beads\b",
         "a skill drill is not what this report is for; replace it with something the parent "
         "and child DO together"),
        (r"\borigami\b|\bplay[-\s]?dough\b|\bplasticine\b|\btracing\b|\bmazes?\b",
         "a fine-motor exercise belongs in an occupational-therapy handout, not here; make it "
         "a shared activity instead"),
        (r"\bhandwriting\s+practice\b|\bgraphic\s+dictation\b|\bpenmanship\b",
         "handwriting practice is off the point of this report; replace it"),
    ],
}

# B. Normality verdicts ABOUT THIS CHILD. A reassurance verdict is a screening claim, and
#    this report does not screen - the same sentence shape that is benign about earrings
#    becomes a false all-clear the moment the subject is a worry. HARD: delete, do not frame.
#    A general fact about children ("at four, a face with no body is common") is untouched.
NORMALITY_VERDICT = {
    "en": [
        (r"\bnormal\s+and\s+healthy\b",
         "a normality verdict about THIS child is a screening claim; state the general "
         "developmental fact instead, or DELETE"),
        (r"\bdeveloping\s+normally\b|\bdevelopment\s+is\s+normal\b",
         "a normality verdict about THIS child is a screening claim; DELETE"),
        (r"\bwithin\s+the\s+normal\s+range\b|\bperfectly\s+normal\b",
         "a normality verdict about THIS child is a screening claim; DELETE"),
        (r"\bnothing\s+(?:here\s+)?to\s+worry\s+about\b|\bnothing\s+here\s+is\s+a\s+concern\b",
         "reassurance about THIS child is a conclusion this report may not draw; DELETE"),
        (r"\bno\s+cause\s+for\s+concern\b|\bno\s+reason\s+for\s+concern\b",
         "reassurance about THIS child is a conclusion this report may not draw; DELETE"),
    ],
}

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
        # en-4.1 added these to the prompt's rotation list - keep the two in step (UseCase #24)
        r"\boften\s+goes\s+with\b|\breads?\s+like\b|\bmay\s+point\s+to\b|"
        r"\bas\s+if\b|\bperhaps\b|\bmaybe\b", re.IGNORECASE),
}
# attribution to a tradition/author (frame condition 1)
# ⚠️ COUPLED TO pipeline/prompt.py (en-4.1): the prompt now ROTATES the generic, name-free
# attribution wording so that one stock phrase does not open every framed statement in the
# report. EVERY form the prompt offers must match here. If it does not, _frame_scan reads a
# correctly framed zone-3 sentence as unattributed, spends a repair call, and the repair
# rewrites it back into the stock phrase - the fix would silently undo itself and cost a
# paid call per report. See UseCasesData.md #24.
ATTRIBUTION = {
    "en": re.compile(
        r"projective|tradition|approach|Machover|Lowenfeld|Vygotsky|Piaget|Kellogg|"
        r"Goodnow|Burkitt|according\s+to|in\s+the\s+\w+\s+tradition|developmental\s+tradition|"
        r"people\s+who\s+study\s+children'?s?\s+(?:draw\w+|art)|"
        r"research\s+on\s+children'?s?\s+(?:draw\w+|art)|"
        r"in\s+the\s+(?:analysis|reading|study|practice)\s+of\s+(?:reading\s+)?children'?s?\s+draw\w+|"
        r"one\s+common\s+reading",
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


def _scan_rules(text: str, rules: list, where: str, loc: str) -> list[dict]:
    """Scan one field against an explicit rule list. Unlike _hard_scan there is NO
    ALLOWED_CONTEXTS amnesty: "not a diagnosis" sitting nearby does not make a drill or a
    normality verdict acceptable - it is exactly the sentence that would carry one."""
    hits = []
    for pattern, why in rules:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            s, e = max(0, m.start() - 80), min(len(text), m.end() + 80)
            hits.append({"where": where, "match": m.group(0), "why": why,
                         "context": text[s:e]})
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

    # --- en-4.2: drills, scanned wherever an ACTIVITY can be proposed ---
    for i, d in enumerate(report_data.get("dimensions") or []):
        for j, a in enumerate(d.get("activities") or []):
            hits.extend(_scan_rules(str(a), DRILL_BANNED[loc],
                                    f"dimensions[{i}].activities[{j}]", loc))
    for field in ("art_recommendations", "understanding_recommendations"):
        for i, r in enumerate(report_data.get(field) or []):
            hits.extend(_scan_rules(str(r), DRILL_BANNED[loc], f"{field}[{i}]", loc))

    # --- en-4.2: normality verdicts, scanned over EVERY field the parent reads ---
    for where, text in _all_prose(report_data):
        hits.extend(_scan_rules(text, NORMALITY_VERDICT[loc], where, loc))
    return hits


def _all_prose(report_data: dict):
    """Every visitor-facing prose field, flat. Normality verdicts are forbidden in all of
    them - a false all-clear does not become safe by moving to the conclusion."""
    for f in ("introduction", "about_child", "conclusion", "context_summary"):
        if report_data.get(f):
            yield f, str(report_data[f])
    for i, d in enumerate(report_data.get("dimensions") or []):
        for f in ("observation", "research_note"):
            if d.get(f):
                yield f"dimensions[{i}].{f}", str(d[f])
        for j, a in enumerate(d.get("activities") or []):
            yield f"dimensions[{i}].activities[{j}]", str(a)
    for field in ("understanding_recommendations", "art_recommendations"):
        for i, r in enumerate(report_data.get(field) or []):
            yield f"{field}[{i}]", str(r)
    for i, dd in enumerate(report_data.get("development_directions") or []):
        yield f"development_directions[{i}]", str(dd.get("text", ""))
    for i, sp in enumerate(report_data.get("specialists") or []):
        if sp.get("reason"):
            yield f"specialists[{i}].reason", str(sp["reason"])
