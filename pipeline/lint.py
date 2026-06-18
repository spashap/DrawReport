"""Report linter: a programmatic backstop for the delivery rules (Golos UseCase #4).

The prompt alone isn't 100% - sampling at temp 0.5 drifts. After the JSON validates,
the report is scanned; violations are fixed by a repair call in gemini.py. The linter
does NOT forbid warm/personal language (that's the product's voice) - it catches
legally sensitive claims (diagnosis / traits / future talent) and brand-forbidden
phrasings. Per-locale: BANNED_PATTERNS[locale] + ALLOWED_CONTEXTS[locale].
"""
from __future__ import annotations

import re

from config import settings

# (pattern, explanation for the repair request). Patterns are conservative
# (word boundaries / multi-word); only report fields are scanned, so false
# positives are rare.
BANNED_PATTERNS = {
    "en": [
        # forbidden verbatim phrasings
        (r"emotional\s+intelligence", "forbidden: 'emotional intelligence'"),
        (r"\bgood\s+taste\b", "forbidden: 'good taste'"),
        (r"bas[ie]s?\s+for\s+(?:a\s+)?(?:beautiful|neat|good)\s+handwriting",
         "forbidden: 'a basis for beautiful handwriting'"),
        # command / pressuring tone
        (r"\byou\s+must\b", "command tone - write 'you could offer / you might try'"),
        (r"\bbe\s+sure\s+to\b", "command tone - soften to 'you could'"),
        (r"\bmake\s+sure\s+to\b", "command tone - soften to 'you could'"),
        (r"\byou\s+have\s+to\b", "command tone - soften"),
        (r"\bdefinitely\b", "pressuring tone - soften"),
        # diagnoses / personality traits / states / future talent
        (r"\banxiet\w*\b", "diagnosis/state is forbidden"),
        (r"\banxious\b", "diagnosis/state is forbidden"),
        (r"self[-\s]?esteem", "judgment about self-esteem is forbidden"),
        (r"\bdiagnos\w+", "this is not a diagnosis"),
        (r"inner\s+strength", "trait-claim 'inner strength' is forbidden"),
        (r"(?:will|going\s+to|destined\s+to)\s+(?:be|become)\s+(?:an?\s+)?"
         r"(?:artist|designer|painter|illustrator)",
         "prediction of future talent is forbidden"),
        # symbolic overreach (assigning meaning instead of mood)
        (r"\bovercom\w+", "symbolic overreach - describe mood, not meaning"),
    ],
}

# contexts in which a match is NOT a violation
ALLOWED_CONTEXTS = {
    "en": [
        "not a diagnosis", "isn't a diagnosis", "is not a diagnosis",
        "not a psychological diagnosis", "not a medical", "psychological diagnosis",
        "medical diagnosis", "we don't diagnose", "do not diagnose",
        "not an assessment", "educational observation",
    ],
}

# fields we scan (activities are NOT scanned: "convey the mood of the scene" etc.
# are legitimate task phrasings, not conclusions about the child)
_CHECK_FIELDS = ("context_summary", "introduction", "conclusion")


def _scan(text: str, where: str, patterns, allowed) -> list[dict]:
    hits = []
    for pattern, why in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            s, e = max(0, m.start() - 80), min(len(text), m.end() + 80)
            ctx = text[s:e]
            if any(a in ctx.lower() for a in allowed):
                continue
            hits.append({"where": where, "match": m.group(0), "why": why, "context": ctx})
    return hits


def find_violations(report_data: dict, locale: str | None = None) -> list[dict]:
    """report_data - dict of a validated report (model_dump)."""
    loc = locale if locale in BANNED_PATTERNS else settings.DEFAULT_LOCALE
    patterns = BANNED_PATTERNS[loc]
    allowed = ALLOWED_CONTEXTS.get(loc, [])
    hits: list[dict] = []
    for f in _CHECK_FIELDS:
        if report_data.get(f):
            hits.extend(_scan(str(report_data[f]), f, patterns, allowed))
    for i, d in enumerate(report_data.get("dimensions") or []):
        for f in ("observation", "research_note"):
            if d.get(f):
                hits.extend(_scan(str(d[f]), f"dimensions[{i}].{f} ({d.get('title')})",
                                  patterns, allowed))
    for i, r in enumerate(report_data.get("recommendations") or []):
        hits.extend(_scan(str(r), f"recommendations[{i}]", patterns, allowed))
    for i, dd in enumerate(report_data.get("development_directions") or []):
        hits.extend(_scan(str(dd.get("text", "")), f"development_directions[{i}]",
                          patterns, allowed))
    return hits
