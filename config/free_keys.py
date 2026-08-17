"""Closed dictionary of interpretation keys for the free analysis.

WHY CLOSED. Across ten live analyses the model invented almost one key per
interpretation even though there were only a handful of distinct interpretations:
size_as_significance / figure_size_as_significance / size_and_detail_as_significance
are one interpretation under three keys. The `free_interpretation_keys` table is keyed
by the key, so that spread produces forty keys for six interpretations, the labelling
never converges, and the main result of the beta - a labelled library of what the model
actually says about real drawings - is never assembled at all.

THE DICTIONARY'S ONE RULE: ONE VISIBLE FEATURE - ONE MEANING.
`large_eyes_as_social_contact` next to `large_eyes_as_curiosity` is one feature with two
meanings, i.e. a "tradition" invented on the spot for one drawing. The linter cannot see
this: the frame is formally intact. Only the dictionary catches it. So every entry has
exactly one `meaning`, and if a feature admits two readings then there is no
interpretation and the correct answer is hypothesis=null.

Only the owner extends the dictionary: on meeting an interpretation outside it the model
must return key="new" with a description, and that row is logged flagged. Silently
minting a new key is not allowed.

SOURCES ARE RENDERED BY THE SERVER from the key (see source_for) - the model never names
a source and therefore cannot fabricate one. It is also what makes the library checkable:
every analysis carrying a given key cites the same source.
"""
from __future__ import annotations

# key -> feature (what is visible) / meaning (what it is associated with) /
#        age_scope (where it is meaningful)
INTERPRETATION_KEYS: dict[str, dict[str, str]] = {
    "size_as_significance": {
        "feature": "the relative size of a figure or object on the page",
        "meaning": "how significant that object is in the child's own view",
        # NOT for the pre-schematic ages: at 3-4 size is governed by hand control and
        # planning the page, not by significance.
        "age_scope": "5-12",
        "source": "K. Machover, “Personality Projection in the Drawing of the Human Figure” (1949)",
        "source_note": "from the projective tradition — widely described, though as a hypothesis rather than a measurement",
    },
    "detail_as_interest": {
        "feature": "how much more worked-out one object is than the others on the page",
        "meaning": "the child's interest in that particular object",
        "age_scope": "4-12",
        "source": "J. Goodnow, “Children Drawing” (1977)",
        "source_note": "on how children distribute effort and attention within a drawing",
    },
    "symbol_emerging_from_scribble": {
        "feature": "the first recognizable shape (a face, a sun) among scribbles and marks",
        "meaning": "the move from drawing-as-movement to drawing-as-naming",
        "age_scope": "2-5",
        "source": "R. Kellogg, “Analyzing Children’s Art” (1969)",
        "source_note": "on the transition from scribbles to the first recognizable symbols",
    },
    "spatial_organization_as_narrative": {
        "feature": "the page divided into zones or planes, several centers of attention",
        "meaning": "a growing ability to build a connected scene and tell a story",
        "age_scope": "5-12",
        "source": "V. Lowenfeld and W. Brittain, “Creative and Mental Growth”",
        "source_note": "on the appearance of a ground line, planes, and a connected scene at the schematic stage",
    },
    "schematic_repetition_as_vocabulary": {
        "feature": "repeated, practiced schemas used for objects of the same kind",
        "meaning": "the child building a graphic vocabulary of their own",
        "age_scope": "4-12",
        "source": "R. Kellogg, “Analyzing Children’s Art” (1969)",
        "source_note": "on how children form stable graphic schemas",
    },
    "facial_asymmetry": {
        # NOTE: the meaning here is TECHNICAL, and that is not an accident. Half a face in
        # shadow with one eye closed is a common teenage manner copied from other kids and
        # from the internet by the hundred. Reading "a split personality" into it is
        # forbidden: a parent whose child draws in that style will spot it instantly.
        "feature": "a face or image divided into two unlike halves",
        "meaning": "working out shading and asymmetry as a picture-making problem",
        "age_scope": "7-12",
        "source": "V. Lowenfeld and W. Brittain, “Creative and Mental Growth”",
        "source_note": "on the move toward realistic depiction and learning to render light and shade",
    },
}

NEW_KEY = "new"          # an interpretation outside the dictionary - description required, logged only
ALLOWED_KEYS = set(INTERPRETATION_KEYS) | {NEW_KEY}

# Keys whose wording the owner has not finally fixed: they were consolidated from what
# was observed, and the owner confirms the phrasing on first reading.
KEYS_PENDING_CONFIRMATION = ["facial_asymmetry"]


def prompt_block() -> str:
    """The dictionary in a form that can be pasted into the system prompt."""
    lines = []
    for key, v in INTERPRETATION_KEYS.items():
        lines.append(f"- {key}: {v['feature']} -> {v['meaning']} "
                     f"(appropriate at ages {v['age_scope']})")
    return "\n".join(lines)


def source_for(key: str) -> dict | None:
    """The source for an interpretation. The SERVER renders this from the key - the model
    never names sources and therefore cannot invent them. It is also what makes the
    library checkable: one key always carries the same source."""
    v = INTERPRETATION_KEYS.get(key)
    if not v or not v.get("source"):
        return None
    return {"source": v["source"], "note": v.get("source_note", "")}
