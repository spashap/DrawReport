r"""Linter for the FREE analysis. Separate from pipeline/lint.py.

Why the paid find_violations() cannot simply be called - three reasons, each of which
breaks the product silently:

1. THE PAID REPAIR MAKES REASSURANCE WORSE. "This is no cause for concern" is caught by
   HEAVY_TERMS (\banxiet\w*), there is no hedge or attribution nearby -> the paid
   _frame_scan demands "ADD the frame" and the repair instruction says to add an
   attribution. The output is "in the projective tradition this is considered no cause
   for concern" - a worse violation than the original, and one that PASSES the linter.
   Here reassurance has HARD semantics: delete.
2. ALLOWED_CONTEXTS IS CALIBRATED FOR A 3000-WORD REPORT. The frame-check window is
   +/-220 characters and the whole free analysis is ~1400. Block 5 is REQUIRED to contain
   boundary language, and "not a diagnosis" is on the allow-list - at that length block 5
   falls inside block 2's window and amnesties a real violation. So we scan FIELD BY FIELD
   and with a narrow allow-list.
3. "EXACTLY ONE HYPOTHESIS" is a structural check, not a matter of style. Since the schema
   already requires the phrase/attribution/key to be returned separately, we check them
   against the prose: the phrase must NOT be duplicated in detail, and there must be no
   attribution in detail. That is also what makes the accumulated library of
   interpretations trustworthy rather than a parallel invention.

The general-purpose regexes come from pipeline/lint.py, which is NOT changed by a line.
Its dicts are keyed by locale, so everything here indexes with the report's locale.
"""
from __future__ import annotations

import re

from config import settings
from pipeline.free_schema import FREE_MAX_WORDS, FreeAnalysis
from pipeline.lint import (ATTRIBUTION, HARD_BANNED, HEAVY_TERMS, HEDGE,
                           LIGHT_TERMS, WORK_REF)

FREE_LINT_VERSION = "1.0"

# --- A. REASSURANCE. Forbidden EVERYWHERE, including block 5. --------------------
# "Reassurance is also a conclusion": a diagnosis in the comforting direction, made
# without a single piece of evidence.
FREE_HARD_ALWAYS: dict[str, list[tuple[str, str]]] = {
    "en": [
        (r"\b(?:no|not\s+a)\s+(?:cause|reason|need)\s+(?:for|to)\s+"
         r"(?:concern|worry|alarm|worrying)",
         "reassurance is a conclusion without evidence; DELETE the phrase"),
        (r"\b(?:nothing|no\s+need)\s+to\s+(?:worry|be\s+concerned|be\s+alarmed)\b",
         "reassurance is a conclusion without evidence; DELETE the phrase"),
        (r"\b(?:this|that|it)(?:'s|\s+is)\s+(?:completely\s+|perfectly\s+|entirely\s+|quite\s+)?normal\b",
         "\"this is normal\" is a diagnosis in the reassuring direction; DELETE the phrase"),
        (r"\b(?:usually|most\s+often|as\s+a\s+rule|typically),?\s+(?:this|that|it)(?:'s|\s+is)\s+normal",
         "\"usually this is normal\" is a conclusion without evidence; DELETE the phrase"),
        (r"\bwithin\s+(?:the\s+)?(?:age[-\s]?appropriate\s+|normal\s+|typical\s+)?(?:norms?|range)\b",
         "\"within the norm\" is an evaluative conclusion; DELETE the phrase"),
        (r"\bnothing\s+(?:to\s+worry\s+about|alarming|unusual|wrong|bad)\b",
         "reassurance; DELETE the phrase"),
        (r"\beverything\s+is\s+(?:fine|okay|ok|all\s+right)\b",
         "reassurance; DELETE the phrase"),
        (r"\b(?:many|most|lots\s+of|plenty\s+of)\s+(?:children|kids)\s+(?:do|draw|make)\b",
         "\"many children do this\" is reassurance via statistics we do not have; DELETE"),
        (r"\ball\s+(?:children|kids)\s+(?:do|draw|go\s+through)\b",
         "reassurance via statistics we do not have; DELETE"),
        (r"\b(?:perfectly|completely)\s+(?:healthy|fine|natural)\b",
         "reassurance; DELETE the phrase"),
    ],
}

# --- B. Negative conclusions. Forbidden in blocks 1-2 and the question, but LEGITIMATE
# in block 5. THE ASYMMETRY IS THE POINT, DO NOT LOSE IT IN EDITS: "this is not connected
# to mood" in block 2 is a reassuring diagnosis; "other drawings will not say whether this
# is connected to mood" in block 5 is the honest language of the boundary the block exists
# for.
FREE_HARD_OUTSIDE_BOUNDARY: dict[str, list[tuple[str, str]]] = {
    "en": [
        (r"\b(?:is|are|has|have)\s+(?:not|n't)\s+(?:connected|related|linked)\s+(?:to|with)\s+"
         r"(?:mood|state|character|emotion|feelings)",
         "asserting the ABSENCE of a connection is as much a conclusion as asserting one; DELETE"),
        (r"\bdoes\s+(?:not|n't)\s+(?:mean|indicate|suggest|point\s+to)\s+"
         r"(?:a\s+)?(?:problem|trouble|disorder|anything\s+wrong)",
         "asserting the absence of a problem is a conclusion without evidence; DELETE"),
    ],
}

# --- C. Product and slogan language. Forbidden everywhere. ------------------------
FREE_HARD_PRODUCT: dict[str, list[tuple[str, str]]] = {
    "en": [
        (r"\b(?:in\s+the\s+)?full\s+report\b",
         "you may not promise \"in the full report you'll learn\"; DELETE"),
        (r"\b(?:find\s+out|learn|discover)\s+what\s+(?:this|it)\s+means\b",
         "you may not promise an explanation of the meaning; DELETE"),
        (r"\bunlock\b|\bget\s+access\b|\bupgrade\s+to\b",
         "product jargon is forbidden; DELETE"),
        (r"\b(?:minimal|basic|trial|sample|preview|starter)\s+"
         r"(?:analysis|report|version|reading)\b",
         "the words \"minimal/basic/trial\" in text for the parent are forbidden - this is "
         "a reading of one drawing, one thing done properly; DELETE"),
        (r"\brich\s+inner\s+world\b|\b(?:amazing|wonderful|incredible)\s+"
         r"(?:imagination|fantasy|creativity)\b",
         "general praise is the surest sign of a template; DELETE or replace with a visible detail"),
        (r"\b(?:amazing|astonishing|incredible|remarkable|stunning|extraordinary)\b",
         "a superlative in a short analysis reads as advertising; DELETE"),
    ],
}

# --- D. "Repetition proves character". Forbidden everywhere (matters most in block 5).
FREE_HARD_REPEATABILITY: dict[str, list[tuple[str, str]]] = {
    "en": [
        # "that's who she is" and "that is who she is" are the same claim; the contraction
        # must not be the thing that decides whether the rule fires.
        (r"\b(?:over\s+and\s+over|again\s+and\s+again|time\s+(?:and|after)\s+time|"
         r"every\s+time)\b[^.;]{0,60}?"
         r"\b(?:that(?:'s|\s+is)\s+(?:who|what)|character|personality|"
         r"tells\s+you\s+(?:who|about)|says\s+something\s+about\s+(?:who|her|him))",
         "repetition proves repetition, not character; REWRITE as \"whether this way of "
         "building an image comes back or appeared only here\""),
        (r"\b(?:if|when|because)\b[^.;]{0,50}?"
         r"\b(?:keeps|repeat\w*|does\s+(?:it|this)\s+(?:again|over))\b[^.;]{0,60}?"
         r"\b(?:then|means|that(?:'s|\s+is)\s+(?:who|what)|character|trait|personality)",
         "repetition proves repetition, not character; REWRITE"),
        (r"\brepetition\b[^.;]{0,40}?\b(?:character|trait|personality)\b",
         "repetition must not be turned into a character trait; REWRITE"),
    ],
}

# A narrow allow-list: in a short text a wide one (as in the paid linter) amnesties real
# violations through a neighbouring paragraph.
FREE_ALLOWED_CONTEXTS = ["not a diagnosis", "isn't a diagnosis", "is not a diagnosis"]

# The hypothesis hedge, widened for the living tone of the portrait block: the paid HEDGE
# expects "looks like", while warm prose naturally says "it looks like the theme holding
# her right now is...".
FREE_HEDGE = {
    "en": re.compile(
        HEDGE["en"].pattern + r"|\bit\s+looks\s+like\b|\bseems\b|\bjudging\s+by\b|"
        r"\bapparently\b|\bmost\s+likely\b|\bgives?\s+the\s+sense\b|"
        r"\breads?\s+(?:like|as)\b|\bas\s+though\b|\bmight\b|\bmay\b",
        re.IGNORECASE),
}

# Attribution: the paid ATTRIBUTION does not know the generic forms the prompt itself
# offers ("in the analysis of children's drawings", "in the reading of children's drawings").
FREE_ATTRIBUTION = {
    "en": re.compile(
        ATTRIBUTION["en"].pattern + r"|in\s+the\s+(?:analysis|reading|study)\s+of\s+"
        r"children'?s?\s+draw\w+|in\s+(?:child\s+)?developmental\s+psychology",
        re.IGNORECASE),
}

# "The artist"/"the author" about the child. ONE occurrence is allowed - in the generic
# formula of a tradition ("associated with significance for the artist"); more than that
# means the child is being called that.
MAX_AUTHOR_MENTIONS = 1

# The negation construction: "not as a reflection of a state, but as learning a task".
# To reject the state you have to name it - and what stays in the parent's head is exactly
# that. Write WHAT IT IS, never what it is not.
FREE_HARD_NEGATION: dict[str, list[tuple[str, str]]] = {
    "en": [
        (r"\bnot\s+as\s+[^.;]{0,80}?,?\s*but\s+as\s",
         "the \"not as X but as Y\" construction names X in order to reject it. Write "
         "directly WHAT it is, without the first half"),
        (r"\bnot\s+(?:a\s+)?(?:reflection|sign|indication|evidence|symptom|marker)\s+"
         r"(?:of\s+)?[^.;]{0,60}?,\s*but\s",
         "a claim made through negation names what it rejects. Write directly what it is"),
        (r"\b(?:this|it|that)(?:'s|\s+is)\s+not\s+about\s+[^.;]{0,50}?,\s*but\s+about\s",
         "\"this is not about X but about Y\" names X. Write about Y straight away"),
    ],
}

FREE_HARD_PROTOCOL: dict[str, list[tuple[str, str]]] = {
    "en": [
        (r"\bhumanoid\s+figures?\b|\banthropomorphic\s+figures?\b",
         "\"humanoid figures\" is an examination protocol, not text for a parent; name who is drawn"),
        (r"\bthe\s+subject\s+(?:of\s+(?:the\s+)?(?:study|analysis)|depicted)\b",
         "bureaucratic language; write like a human being"),
        (r"\bthe\s+(?:artist|author)\s+(?:has|is|was|appears)\b",
         "do not call the child \"the artist\"/\"the author\" - use the name"),
    ],
}


def _loc(locale: str | None) -> str:
    return locale if locale in FREE_HARD_ALWAYS else settings.DEFAULT_LOCALE


def _scan_list(text: str, rules: list[tuple[str, str]], where: str,
               kind: str) -> list[dict]:
    hits: list[dict] = []
    for pattern, why in rules:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            s, e = max(0, m.start() - 70), min(len(text), m.end() + 70)
            ctx = text[s:e]
            if any(a in ctx.lower() for a in FREE_ALLOWED_CONTEXTS):
                continue
            hits.append({"where": where, "match": m.group(0), "why": why,
                         "context": ctx, "kind": kind})
    return hits


# Words about a state with which a question for the child has ALREADY decided what the
# drawing means. The counter-example is "Why is the monster so angry?"; note that "angry"
# is not covered by the paid LIGHT_TERMS in that form, so a dedicated list is needed.
QUESTION_STATE_WORDS = {
    "en": re.compile(
        r"\b(?:angry|mad|cross|sad|unhappy|miserable|scary|scared|frightened|afraid|"
        r"lonely|alone|upset|hurt|aggressive|anxious|worried|depressed|guilty|"
        r"jealous|ashamed)\b", re.IGNORECASE),
}
# The leading construction "why is X so Y" is a ready answer, not a question.
QUESTION_LEADING = {
    "en": re.compile(r"\bwhy\s+(?:is|are|was|were|does|do|did)\s+[\w\s]{0,20}?\bso\b",
                     re.IGNORECASE),
}

_CLAUSE_BREAK = re.compile(r"[.,;:!?()\n]|—|–|--")


def _artifact_attached(text: str, end: int, window: int, loc: str) -> bool:
    """Does the term refer to THE WORK ITSELF rather than to the child?

    The paid linter simply looks for an artifact noun within 40 characters after the term.
    In a short analysis that is not enough: "the child is anxious: the lines tremble" got
    an amnesty because of the word "lines" in the next clause. So we cut at the clause
    boundary - the exception only applies to a FUSED phrase ("an anxious sky", "the mood of
    the work"), which is what it was introduced for.
    """
    frag = text[end:end + window]
    br = _CLAUSE_BREAK.search(frag)
    if br:
        frag = frag[:br.start()]
    return bool(WORK_REF[loc].search(frag))


def _sensitive_terms(text: str, loc: str, strict: bool = False) -> list[re.Match]:
    """Sensitive terms THAT REFER TO THE CHILD. The artifact exception ("a dark palette",
    "the mood of the work", "an anxious sky") is preserved."""
    window = 20 if strict else 40
    out = []
    for term_re in (HEAVY_TERMS[loc], LIGHT_TERMS[loc]):
        for m in term_re.finditer(text):
            if _artifact_attached(text, m.end(), window, loc):
                continue
            out.append(m)
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _all_text(a: FreeAnalysis) -> str:
    return "\n".join([a.opening, a.detail, a.portrait_hint,
                      a.question_to_child, a.unknown_next])


def _check_name_usage(a: FreeAnalysis, child_name: str, loc: str) -> list[dict]:
    """The name instead of "the artist" is a tone requirement, but it is checked
    mechanically.

    We count "artist"/"author" across the whole text and require the child's name to appear
    at least twice. That threshold is exactly right because one occurrence of "the artist"
    is legitimate inside the generic formula of a tradition, while a name said once is a
    signature rather than a form of address.
    """
    hits: list[dict] = []
    text = _all_text(a)
    hits += _scan_list(text, FREE_HARD_PROTOCOL[loc], "tone", "text")
    n_author = len(re.findall(r"\b(?:the\s+)?(?:artist|author)s?\b", text, re.IGNORECASE))
    if n_author > MAX_AUTHOR_MENTIONS:
        hits.append({
            "where": "tone", "match": f"\"artist/author\" x{n_author}", "kind": "text",
            "context": text[:160],
            "why": "do not call the child \"the artist\" - it is the coldest word you can "
                   "use for a child. Use the name",
        })
    if child_name:
        first = re.split(r"[\s.,]+", child_name.strip())[0]
        if len(first) >= 3:
            n_name = len(re.findall(re.escape(first), text, re.IGNORECASE))
            if n_name < 2:
                hits.append({
                    "where": "tone", "match": f"the name appears {n_name} time(s)",
                    "kind": "text", "context": text[:160],
                    "why": f"the name \"{first}\" must appear at least twice - this is an "
                           f"analysis for a parent, not an object record",
                })
    return hits


def find_free_violations(a: FreeAnalysis, child_name: str = "",
                         locale: str | None = None) -> list[dict]:
    """Violations in a free analysis. kind: 'text' - fixed by rewriting,
    'hypothesis' - can be cleared by a downgrade (dropping the hypothesis)."""
    loc = _loc(locale)
    hits: list[dict] = []
    common = (FREE_HARD_ALWAYS[loc] + FREE_HARD_PRODUCT[loc]
              + FREE_HARD_REPEATABILITY[loc] + FREE_HARD_NEGATION[loc])
    outside = FREE_HARD_OUTSIDE_BOUNDARY[loc]

    # --- block 1: the warm opening. Diagnosis and reassurance are forbidden, but the
    # blanket ban on any warm word is lifted: a cold examination protocol is a defect,
    # not safety.
    hits += _scan_list(a.opening, common + outside, "opening", "text")
    hits += _scan_list(a.opening, HARD_BANNED[loc], "opening", "text")
    # Warmth yes, a bare claim about a state no. "You can see the child is anxious" in the
    # opening is still a diagnosis, however many warm words surround it.
    for m in _sensitive_terms(a.opening, loc, strict=True):
        heavy_here = bool(HEAVY_TERMS[loc].match(m.group(0)))
        if heavy_here or not FREE_HEDGE[loc].search(a.opening):
            hits.append({
                "where": "opening", "match": m.group(0), "kind": "text",
                "context": a.opening[max(0, m.start() - 70):m.end() + 70],
                "why": ("a heavy state of the child in the opening is not acceptable - "
                        "describe what is visible" if heavy_here else
                        "the child's state in the opening only through a hypothesis hedge, "
                        "or describe a visible detail"),
            })

    # --- block 3: the short portrait. Interpretive by definition, so what is needed here
    # is a FRAME (a hypothesis hedge), not a ban.
    hits += _scan_list(a.portrait_hint, common, "portrait_hint", "text")
    hits += _scan_list(a.portrait_hint, HARD_BANNED[loc], "portrait_hint", "text")
    sensitive = _sensitive_terms(a.portrait_hint, loc)
    heavy = [m for m in sensitive if HEAVY_TERMS[loc].match(m.group(0))]
    if sensitive and not FREE_HEDGE[loc].search(a.portrait_hint):
        hits.append({
            "where": "portrait_hint", "match": "(portrait with no hypothesis hedge)",
            "kind": "text", "context": a.portrait_hint,
            "why": "the portrait speaks about the child - it needs a hypothesis hedge "
                   "(\"it looks like\", \"seems\", \"may speak of\"). Do not remove the "
                   "warmth, add the frame",
        })
    if heavy and not ATTRIBUTION[loc].search(a.portrait_hint):
        hits.append({
            "where": "portrait_hint", "match": heavy[0].group(0), "kind": "text",
            "context": a.portrait_hint,
            "why": "a heavy term about the child's state in the portrait also requires an "
                   "attribution to a tradition - or soften the wording",
        })

    # --- "the artist" instead of the name.
    hits += _check_name_usage(a, child_name, loc)

    # --- block 2 ---
    hits += _scan_list(a.detail, common + outside, "detail", "text")
    hits += _scan_list(a.detail, HARD_BANNED[loc], "detail", "text")

    # --- the question for the child ---
    hits += _scan_list(a.question_to_child, common + outside, "question_to_child", "text")
    hits += _scan_list(a.question_to_child, HARD_BANNED[loc], "question_to_child", "text")
    # The question mark must BE there, but need not be the last character: by contract a
    # sentence follows the question saying the child's answer beats an adult's guess.
    if "?" not in a.question_to_child:
        hits.append({"where": "question_to_child", "match": a.question_to_child[-40:],
                     "kind": "text", "context": a.question_to_child,
                     "why": "the block must contain the question for the child, with a \"?\""})
    for m in (list(_sensitive_terms(a.question_to_child, loc, strict=True))
              + list(QUESTION_STATE_WORDS[loc].finditer(a.question_to_child))):
        hits.append({
            "where": "question_to_child", "match": m.group(0), "kind": "text",
            "why": "a question containing a word about a state (\"angry\", \"sad\") has "
                   "already decided what the drawing means. Ask openly: \"tell me who this "
                   "is and what is happening here?\"",
            "context": a.question_to_child,
        })
    if QUESTION_LEADING[loc].search(a.question_to_child):
        hits.append({
            "where": "question_to_child", "match": a.question_to_child[:60],
            "kind": "text", "context": a.question_to_child,
            "why": "\"why is ... so ...\" is a leading construction: it already contains the "
                   "answer. Ask openly, with no suggested options",
        })

    # --- block 5: boundary language is legitimate, reassurance is not ---
    hits += _scan_list(a.unknown_next, common, "unknown_next", "text")
    hits += _scan_list(a.unknown_next, HARD_BANNED[loc], "unknown_next", "text")

    # --- length: a repairable violation, not a fatal one ---
    # The soft target lives here rather than in the schema so that an over-long analysis
    # goes through the repair call ("shorten this") instead of killing the attempt. A
    # short analysis is the product, so the target is still enforced - just recoverably.
    n = a.word_count()
    if n > FREE_MAX_WORDS:
        hits.append({
            "where": "length", "match": f"{n} words", "kind": "text",
            "context": "",
            "why": f"the analysis is {n} words against a target of {FREE_MAX_WORDS}. "
                   f"SHORTEN it by roughly {n - FREE_MAX_WORDS} words, cutting the least "
                   f"load-bearing sentences. Do not drop a whole block and do not change "
                   f"the meaning of what remains",
        })

    # --- the structural "exactly one hypothesis" check ---
    hits += _check_hypothesis(a, loc)
    return hits


def _check_hypothesis(a: FreeAnalysis, loc: str) -> list[dict]:
    hits: list[dict] = []
    detail = a.detail

    if a.hypothesis is None:
        # The "there is no lawful hypothesis" contract: then there is none in the prose
        # either - otherwise the model would have handed the interpretation to the parent
        # but not to the library, the worst of both worlds.
        #
        # BUT the marker of a smuggled interpretation is the ATTRIBUTION to a tradition,
        # not the hedge. "It looks like she enjoys filling things in densely" is a cautious
        # observation about behaviour, not a projective interpretation, and banning it
        # would bring the dead tone back. Heavy terms about the child are caught separately.
        if FREE_ATTRIBUTION[loc].search(detail):
            hits.append({
                "where": "detail", "match": "(attribution with hypothesis=null)",
                "kind": "hypothesis", "context": detail,
                "why": "the text references a tradition but no hypothesis is formalized. "
                       "Either FORMALIZE it as a hypothesis with a key from the dictionary, "
                       "or REMOVE the reference to the tradition and keep the observation",
            })
        heavy_free = [m for m in _sensitive_terms(detail, loc)
                      if HEAVY_TERMS[loc].match(m.group(0))]
        if heavy_free:
            hits.append({
                "where": "detail", "match": heavy_free[0].group(0),
                "kind": "hypothesis", "context": detail,
                "why": "a heavy term about the child's state with no formalized hypothesis - "
                       "soften the wording or formalize the interpretation in its full frame",
            })
        return hits

    phrase = a.hypothesis.phrase
    # The interpretation lives ONLY in the hypothesis object: on the page it is shown as
    # its own block with a heading and a source. A duplicate in detail would give the
    # parent the same text twice.
    if _norm(phrase) in _norm(detail):
        hits.append({
            "where": "detail", "match": phrase[:60], "kind": "hypothesis",
            "context": detail,
            "why": "the interpretation is duplicated in detail - leave only the observation "
                   "there, the interpretation is shown as its own block",
        })
    if FREE_ATTRIBUTION[loc].search(detail):
        hits.append({
            "where": "detail", "match": "(reference to a tradition in detail)",
            "kind": "hypothesis", "context": detail,
            "why": "references to traditions and authors are not needed in detail - the "
                   "system inserts the source from the interpretation key",
        })
    if not HEDGE[loc].search(phrase):
        hits.append({
            "where": "hypothesis.phrase", "match": phrase[:80], "kind": "hypothesis",
            "context": phrase,
            "why": "there is no hypothesis hedge - add \"may speak of\", \"is sometimes "
                   "associated with\", \"can be read as\"",
        })
    # The attribution has become DATA: under each interpretation the server prints the
    # source from the dictionary by key. So it is only required inside the phrase itself
    # where there is no source - that is, for key="new". Previously this rule removed
    # perfectly correct hypotheses merely because the model wrote "in the analysis" rather
    # than "in the tradition".
    from config.free_keys import source_for
    if source_for(a.hypothesis.key) is None and not FREE_ATTRIBUTION[loc].search(phrase):
        hits.append({
            "where": "hypothesis.phrase", "match": phrase[:80], "kind": "hypothesis",
            "context": phrase,
            "why": "this interpretation has no source in the dictionary, so it needs an "
                   "attribution in the phrase itself: \"in the tradition of reading "
                   "children's drawings this is sometimes associated with...\". Do not "
                   "invent sources",
        })
    if len(FREE_ATTRIBUTION[loc].findall(phrase)) > 1:
        hits.append({
            "where": "hypothesis.phrase", "match": "(two attributions)",
            "kind": "hypothesis", "context": phrase,
            "why": "a second attribution is a second hypothesis. Keep EXACTLY ONE: several "
                   "competing interpretations read as evasive to a parent",
        })
    hits += _scan_list(phrase, FREE_HARD_ALWAYS[loc] + FREE_HARD_PRODUCT[loc],
                       "hypothesis.phrase", "hypothesis")
    return hits


def can_downgrade(hits: list[dict]) -> bool:
    """Are all the remaining violations cleared by dropping the hypothesis?"""
    return bool(hits) and all(h.get("kind") == "hypothesis" for h in hits)


def drop_hypothesis(a: FreeAnalysis, locale: str | None = None) -> FreeAnalysis | None:
    """A downgrade instead of a failure ("if there is no lawful interpretation there isn't
    one" is a full outcome). We remove the hypothesis object and the sentence carrying it
    from detail. Returns None if nothing is left of block 2 afterwards - then it is more
    honest to regenerate than to ship a stump."""
    if a.hypothesis is None:
        return None
    loc = _loc(locale)
    phrase_n = _norm(a.hypothesis.phrase)
    kept = [s for s in re.split(r"(?<=[.!?])\s+", a.detail.strip())
            if phrase_n not in _norm(s) and not ATTRIBUTION[loc].search(s)]
    detail = " ".join(kept).strip()
    if len(re.findall(r"[^\W\d_]+", detail, re.UNICODE)) < 12:
        return None
    return a.model_copy(update={"detail": detail, "hypothesis": None})


FREE_REPAIR_INSTRUCTION = """\
You are editing a short free analysis of ONE child's drawing. This is not the paid report: \
there are no scores and no dimensions - there are five blocks (a warm opening / one detail \
/ a short portrait / a question for the child / the honest gap). Violations were found. \
Fix ONLY those, leave everything else word for word.

HOW TO FIX - by type of violation:
1. REASSURANCE ("no cause for concern", "this is normal", "within the norm", "nothing to \
worry about", "many children do this") is a diagnosis in the comforting direction, made \
without evidence. It does NOT need to be wrapped in a frame: it needs to be DELETED. Do \
not replace it with different reassurance. Just remove the phrase - the text becomes more \
honest, not poorer.
2. THE OPENING (opening) is observable material only. Any word about the state, character \
or mood OF THE CHILD is removed from it and replaced by a visible detail. About the drawing \
itself ("a dark palette", "the mood of the work") is fine.
3. THE HYPOTHESIS - you have TWO equally valid exits, choose the honest one:
   a) complete the frame: an attribution to a real tradition (the unnamed generic form "in \
the tradition of reading children's drawings this is sometimes associated with..." is fully \
valid), a hypothesis hedge ("may speak of", "can be read as"), a tie to a visible detail, \
and a return to the child. And copy the phrase VERBATIM into the hypothesis object;
   b) DROP the hypothesis entirely: hypothesis=null, and in detail keep the visible detail, \
a neutral observation and the question for the child. This is NOT a failure - an honest "we \
have no lawful interpretation for this detail" is the only version that survives a hostile \
reader. If the frame does not come out naturally, choose (b).
   EXACTLY ONE hypothesis. A second attribution in the text is a second hypothesis - remove it.
4. REPETITION: "over and over - that's who he is" is forbidden. Repetition proves \
repetition, not character. Correct: "other drawings would answer a narrower question: \
whether this way of building an image comes back or appeared only here".
5. PRODUCT LANGUAGE ("in the full report", "unlock", "trial", "a rich inner world", \
superlatives) - delete.
6. "THE ARTIST"/"THE AUTHOR" about the child - replace with the child's name.

Do not increase the length. A calm, warm tone, no exclamations. Return the FULL corrected \
JSON with the same structure, with no markdown wrappers."""
