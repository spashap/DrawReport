"""The JSON contract of the FREE analysis of a single drawing.

A separate contract, not a trimmed-down paid schema: the free analysis has a different
job and different prohibitions. There is no scoring, no seven dimensions, no specialists
and no talents here - there are exactly five blocks: a warm opening -> one detail (and at
most ONE hypothesis) -> a short portrait -> a question for the child -> an honest gap.

The key difference from the paid schema: the hypothesis is returned as a SEPARATE OBJECT
(phrase + attribution + key), not dissolved into the prose. That is what lets the library
of admissible interpretations be assembled from what the model actually writes about real
drawings, so the owner can label the accumulated keys. The side benefit is that the
linter can check the phrase against the text and mechanically hold the "exactly one
hypothesis" rule.

`hypothesis = None` is a LEGITIMATE and respected outcome: "if there is no lawful
interpretation, there isn't one." Block 2 then works as visible detail -> neutral
observation -> question for the child. That is not a generation failure and not a reason
to retry.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from config.free_keys import ALLOWED_KEYS, NEW_KEY

FREE_SCHEMA_VERSION = "1.0"

# Length. The target of ~300-380 words covers the WHOLE document the parent sees, and the
# selling close (~80 words) is written by the server, not the model. So the ceiling and
# floor here apply to the MODEL's part, and they are below 300 deliberately.
# Sum of the per-block targets: 60-90 + 80-120 + 50-70 + 25-40 + ~40 = 255-360.
# CALIBRATED FOR ENGLISH. The Russian original used 370, and porting that number directly
# was a mistake: English needs roughly 10-20% more words for the same content (articles,
# prepositions, auxiliary verbs that Russian does without), so a ported ceiling rejects
# analyses that are the right LENGTH in reading time and only over in word count. Measured
# across live runs the model lands at 340-410 words for this block structure.
FREE_MAX_WORDS = 420  # keep the number quoted in free_prompt.py (the opening line) identical to this
# The SOFT ceiling above is the product target and is enforced by the linter, which can
# repair an over-long analysis by asking for a shorter one. The HARD ceiling here is only
# a runaway guard. Keeping the soft target as a schema error was a mistake: the model
# routinely lands 5-20% over, and a schema error kills the attempt before the analysis
# object exists - so the repair loop, which is built for exactly this, never runs and
# three paid calls produce nothing for the parent.
FREE_HARD_MAX_WORDS = 550
FREE_MIN_WORDS = 190
# A coloring page has no portrait block, so the floor is lower: a short service paragraph,
# one observation, one question, and then the request to bring a drawing from a blank page.
FREE_MIN_WORDS_COLORING = 130
# The honest gap stays two sentences. The selling close after it is written by the SERVER,
# not the model - price and the list of dimensions cannot be trusted to generation.
FREE_UNKNOWN_MAX_WORDS = 60

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_KEY_CLEAN_RE = re.compile(r"[^a-z0-9_]+")


def count_words(*texts: str) -> int:
    return sum(len(_WORD_RE.findall(t or "")) for t in texts)


def _keep_one_question(text: str) -> str:
    """Keeps the FIRST question and every non-question sentence after it.

    "Who is this? What are they doing? Where are they going?" -> "Who is this?"
    The sentence about the child's own answer being better than an adult's guess stays:
    it is not a question.
    """
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    out, seen_q = [], False
    for p in parts:
        if p.rstrip().endswith("?"):
            if seen_q:
                continue
            seen_q = True
        out.append(p)
    return " ".join(out).strip()


class Hypothesis(BaseModel):
    """One interpreting sentence in its full frame - and its "passport" for the library.

    `phrase` is stored VERBATIM as it stands in the analysis: the linter checks for its
    presence, and only that makes the accumulated library trustworthy rather than a
    parallel invention sitting next to the text the parent reads.
    """

    phrase: str = Field(min_length=1)
    attribution: str = Field(min_length=1)   # which tradition/author it is attributed to
    # The key comes ONLY from the closed dictionary in config/free_keys.py, or "new".
    # A free-form name is forbidden: the spread of names destroys the library labelling
    # (see the header of free_keys.py). Normalization below is lenient, membership strict.
    key: str = Field(min_length=1)
    # Filled ONLY when key="new": the interpretation in one sentence, so the owner can
    # decide whether to add it to the dictionary or reject it.
    new_key_description: str = ""
    # The age range in which the model itself judges the interpretation to apply
    # ("5-12", "7+", "any"). The library needs it: the same interpretation can be
    # meaningful at the schematic stage and doubtful pre-schematically (figure size at
    # three is governed by hand control, not by significance).
    age_scope: str = ""

    @field_validator("key")
    @classmethod
    def _slug(cls, v: str) -> str:
        v = _KEY_CLEAN_RE.sub("_", v.strip().lower()).strip("_")
        if not v:
            raise ValueError("hypothesis.key is empty after normalization")
        if v not in ALLOWED_KEYS:
            raise ValueError(
                f"hypothesis.key='{v}' is not from the dictionary. Allowed: "
                f"{', '.join(sorted(ALLOWED_KEYS))}. If no interpretation in the "
                f"dictionary fits, return hypothesis=null OR key='new' with "
                f"new_key_description")
        return v

    @model_validator(mode="after")
    def _new_needs_description(self) -> "Hypothesis":
        if self.key == NEW_KEY and not self.new_key_description.strip():
            raise ValueError("key='new' requires new_key_description - otherwise the row "
                             "cannot be labelled")
        return self


# Special cases. A mismatch with the parent's concern is NOT here and must not be: it
# lives in exactly one field - concern_correlate_visible (below). Do not add 'mismatch'
# here in any form.
FreeFlag = Literal[
    "sparse",     # a sparse scribble at 3-4: a hypothesis is FORBIDDEN
    "coloring",   # a coloring page / tracing: work inside someone else's outlines
    "thin",       # little material: the hypothesis stays but moves to line/placement
]


class FreeAnalysis(BaseModel):
    # Block 1 (60-90 words): a warm, concrete opening - ONE image tied to something
    # visible, not an inventory.
    opening: str = Field(min_length=1)
    detail: str = Field(min_length=1)             # block 2 (80-120): one detail, in frame
    hypothesis: Hypothesis | None = None
    # Block 3 (50-70) - what the parent is actually reading for: what THIS page says
    # about the child. The frame is required and there is no diagnosis, but a cool tone
    # here is a defect. EMPTY on a coloring page (see _contracts).
    portrait_hint: str = ""
    question_to_child: str = Field(min_length=1)  # block 4 (25-40): open question + the answer line
    unknown_next: str = Field(min_length=1)       # block 5 (2 sentences): the honest gap

    flags: list[FreeFlag] = Field(default_factory=list)
    # The ONLY source of truth about a mismatch with the named concern.
    #   False -> the server inserts the authored paragraph; the model does not write it;
    #   None  -> not applicable (the neutral path - there is no concern at all).
    # A 'mismatch' flag is DELIBERATELY absent: two representations of one fact have
    # already drifted apart once (the model returned flags=[] with correlate=false), and
    # it must not come back - readers must look exactly here.
    concern_correlate_visible: bool | None = None
    concern_correlate_note: str = ""

    insufficient_input: bool = False

    @field_validator("flags")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        seen: list[str] = []
        for f in v:
            if f not in seen:
                seen.append(f)
        return seen

    @model_validator(mode="after")
    def _contracts(self) -> "FreeAnalysis":
        # A coloring page is not an analysis but a redirect: its only job is to get a real
        # drawing. A portrait here would contradict the service paragraph ("to see
        # character we need a blank page") and would do two jobs at once.
        #
        # The portrait is CLEARED MECHANICALLY rather than raising, for the same reason
        # extra questions are trimmed below: the model reliably recognizes a coloring page
        # and sets the flag, it just also writes a portrait out of habit. Raising here made
        # every coloring page burn all three attempts and hand the parent a failure - three
        # paid calls to deliver nothing, on the one input whose whole purpose is to ask for
        # a real drawing. The contract still holds (the shipped analysis has no portrait);
        # it is simply enforced instead of merely demanded.
        if "coloring" in self.flags:
            if self.portrait_hint.strip():
                object.__setattr__(self, "portrait_hint", "")
        elif not self.portrait_hint.strip():
            raise ValueError("portrait_hint is required: it is what the parent reads for")

        # Exactly one question for the child - but NOT at the cost of a burned attempt:
        # extra questions are trimmed mechanically. Three or four in a row turn the
        # analysis into homework, and dropping the whole analysis over it (and paying for
        # three attempts) would be silly.
        if self.question_to_child.count("?") != 1:
            object.__setattr__(self, "question_to_child",
                               _keep_one_question(self.question_to_child))
        if "?" not in self.question_to_child:
            raise ValueError("question_to_child must contain a question for the child")

        u = count_words(self.unknown_next)
        if u > FREE_UNKNOWN_MAX_WORDS:
            raise ValueError(
                f"unknown_next is {u} words against a ceiling of {FREE_UNKNOWN_MAX_WORDS}: "
                f"two sentences are needed - which question this page leaves open and what "
                f"other drawings would answer")
        n = self.word_count()
        floor = (FREE_MIN_WORDS_COLORING if "coloring" in self.flags
                 else FREE_MIN_WORDS)
        if n > FREE_HARD_MAX_WORDS:
            raise ValueError(f"the analysis is longer than {FREE_HARD_MAX_WORDS} words ({n}) - "
                             f"far past the target of {FREE_MAX_WORDS}; regenerate")
        if n < floor:
            raise ValueError(
                f"the analysis is shorter than {floor} words ({n}) - add substance, not "
                f"padding: more of what is actually visible on the page, not longer "
                f"sentences about the same thing")
        return self

    def word_count(self) -> int:
        # hypothesis.phrase counts too: since the interpretation lives in its own object
        # and is shown in its own block, it is text for the parent exactly like the rest.
        # Leaving it out would understate the real length of the analysis.
        return count_words(self.opening, self.detail, self.portrait_hint,
                           self.question_to_child, self.unknown_next,
                           self.hypothesis.phrase if self.hypothesis else "")


class FreeInsufficient(BaseModel):
    """Unusable input. reason_key lets the beta count rejections by type and lets the page
    show the parent different text (retake the photo / this is not a child's drawing /
    blank page). Such an analysis does NOT consume the per-child limit."""

    insufficient_input: Literal[True]
    reason_key: Literal["photo_poor", "not_a_drawing", "blank", "other"] = "other"
    insufficient_reason: str = Field(min_length=1)


def validate_free(data: dict) -> FreeAnalysis | FreeInsufficient:
    """Validates the raw JSON from the model. Raises pydantic.ValidationError.
    Discriminated on insufficient_input, as in the paid validate_report()."""
    if data.get("insufficient_input"):
        return FreeInsufficient.model_validate(data)
    return FreeAnalysis.model_validate(data)
