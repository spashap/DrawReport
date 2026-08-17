"""Authored text for the free funnel: the questions, the summary, the selling close.

⚠️ ALL VISIBLE COPY HERE IS **DRAFT** and is for the owner to review and rewrite. It
adapts the intent of the Russian original rather than translating it literally, per the
project rule for marketing copy. The STRUCTURE, however, is not draft - each piece exists
for a stated reason recorded in the comments, and those reasons should survive a rewrite.

Two things this module does NOT do, on purpose:
  * it never interprets a drawing - at the point the summary is composed there is no
    drawing yet, so anything resembling a reading of the child would be invention;
  * it never lets the model author fixed text. Everything here is written by the server,
    because fixed wording in the model's mouth drifts from run to run.

English needs far less machinery than the Russian original (no case declension), but it
does need pronoun and verb agreement, including singular "they" which takes plural verbs.
That is what g() below is for.
"""
from __future__ import annotations

# --- Pronoun and verb agreement --------------------------------------------------
# Slots: {sub} {obj} {poss} {refl}; {s} is the third-person -s on a verb ("draw{s}"),
# and {is}/{was}/{has}/{does} cover the irregulars. Singular "they" takes plural verbs,
# which is exactly the case a naive .replace("he", "they") gets wrong.
_FORMS: dict[str, dict[str, str]] = {
    "she": {"sub": "she", "obj": "her", "poss": "her", "refl": "herself",
            "s": "s", "is": "is", "was": "was", "has": "has", "does": "does"},
    "he": {"sub": "he", "obj": "him", "poss": "his", "refl": "himself",
           "s": "s", "is": "is", "was": "was", "has": "has", "does": "does"},
    "they": {"sub": "they", "obj": "them", "poss": "their", "refl": "themselves",
             "s": "", "is": "are", "was": "were", "has": "have", "does": "do"},
}
ADDRESS_FORMS = list(_FORMS)


def g(text: str, address_form: str = "they") -> str:
    """Fill the pronoun/verb slots. Unknown form -> they (never guess from a name)."""
    f = _FORMS.get(address_form, _FORMS["they"])
    for k, v in f.items():
        text = text.replace("{" + k + "}", v)
    return text


def possessive(name: str) -> str:
    """Sophie -> Sophie's; Chris -> Chris'."""
    name = (name or "").strip()
    if not name:
        return ""
    return name + ("'" if name.endswith("s") else "'s")


# --- Age bands --------------------------------------------------------------------
# The age is asked as a BAND, not an exact number: one tap instead of a spinner, on a
# phone, late in the evening. The band is also what the age anchor speaks about.
AGE_BANDS: list[dict] = [
    {"key": "3-4", "label": "3-4", "age": 4},
    {"key": "5-6", "label": "5-6", "age": 6},
    {"key": "7-9", "label": "7-9", "age": 8},
    {"key": "10-12", "label": "10-12", "age": 11},
]
BAND_BY_KEY = {b["key"]: b for b in AGE_BANDS}
BAND_LABELS = {b["key"]: f"{b['label']} years old" for b in AGE_BANDS}


def age_band(age: int) -> str:
    if age <= 4:
        return "3-4"
    if age <= 6:
        return "5-6"
    if age <= 9:
        return "7-9"
    return "10-12"


def band_age(key: str) -> int:
    return BAND_BY_KEY.get(key, AGE_BANDS[1])["age"]


# --- Step 1: what caught your eye. Button labels, verbatim. -----------------------
CONCERNS: list[dict] = [
    {"key": "black", "label": "Draws only in black or very dark colors"},
    {"key": "monsters", "label": "Draws monsters, weapons, fights, frightening scenes"},
    {"key": "alone", "label": "Draws themselves alone, with no other people"},
    # Every label starts with a present-tense verb about the CHILD, so the list scans as
    # one grammatical shape on the home page. "very schematic" was also a word no US
    # parent uses about a drawing - it is the reviewer's term, not the customer's.
    {"key": "faceless", "label": "Draws people with no faces or hands, just outlines"},
    {"key": "repeat", "label": "Draws the same thing over and over"},
    {"key": "pressure", "label": "Presses hard, scribbles over, tears the paper"},
    {"key": "stopped", "label": "Has stopped drawing, or gives up when it doesn’t come out right"},
    {"key": "neutral", "label": "Nothing worries me — I’m just curious what the "
                                "drawing says about my child"},
]
CONCERN_KEYS = [c["key"] for c in CONCERNS]

# --- Step 2: how long ------------------------------------------------------------
DURATION_QUESTION = "How long have you been noticing this?"
DURATION_QUESTION_STOPPED = "How long has {sub} barely been drawing?"

DURATIONS: list[dict] = [
    {"key": "days", "label": "a few days"},
    {"key": "weeks", "label": "a few weeks"},
    {"key": "months", "label": "a few months"},
    {"key": "always", "label": "a long time - it's just how {sub} draw{s}"},
]
# For "stopped drawing" the fourth option has to read differently: "it's just how they
# draw" about NOT drawing is nonsense.
DURATION_LABEL_OVERRIDES: dict[tuple[str, str], str] = {
    ("stopped", "always"): "{sub} never drew much to begin with",
}

# --- Step 3: the parent's own words -----------------------------------------------
FREE_TEXT_QUESTION = "What have you noticed in {poss} drawings? One line - or skip it."
FREE_TEXT_PLACEHOLDER = "For example: three weeks of drawing only with a black pen"

ADDRESS_QUESTION = "How should we refer to your child?"
ADDRESS_LABELS = {"she": "she", "he": "he", "they": "they"}

# --- The mirror -------------------------------------------------------------------
# The formula is: "You've noticed that {the concern in plain words}. {the duration line}"
#
# ⚠️ CRITICAL IF THIS IS EVER EDITED: the button labels are a LIST OF ALTERNATIVES, not a
# set of simultaneous facts. "Presses hard, scribbles over, tears the paper" must stay as
# "scribbles over OR tears" in the mirror: a parent whose child only presses hard must not
# read back that their child tears the paper. Turning "or" into "and" converts a
# paraphrase into a claim about the child that the parent never made.
# The mirror also paraphrases the OBSERVATION without amplifying the worry: there are no
# "frightening scenes" in #2 - monsters, weapons and fights are visible on the page,
# whereas "frightening" is already a judgment.
MIRROR: dict[str, str] = {
    "black": "your child draws mostly in black",
    "monsters": "your child draws monsters, weapons, fights",
    "alone": "your child draws themselves alone, without other people",
    "faceless": "people in the drawings come out without faces or without hands, "
                "just outlines",
    "repeat": "your child draws the same thing over and over",
    "pressure": "your child presses hard on the pencil, scribbles over the drawing "
                "or tears it",
    "stopped": "your child has stopped drawing, or gives up when it doesn’t come "
               "out right",
}

# --- Age anchors: a fact about the developmental stage. The ONLY thing allowed in the
# summary that is not a paraphrase of what the parent said. -------------------------
AGE_ANCHORS: dict[str, str] = {
    "3-4": "At three and four the hand is still learning to steer the tool, and drawing "
           "is largely an exploration of the mark rather than a picture of something. A "
           "closed shape, a change of direction, coming back to something already drawn - "
           "at this age those are notable events.",
    "5-6": "At five and six the same child can use color, line and the ways of drawing "
           "{sub} already know{s} very differently from one drawing to the next. What is "
           "settled and what is incidental are still easy to mix up here.",
    "7-9": "At seven to nine a child builds a system of their own: how to set up a scene, "
           "where the ground goes, how to show what is happening. The choices get more "
           "deliberate and show more - but so do the demands the child makes of themselves.",
    "10-12": "At ten to twelve a child starts seeing the world realistically and comparing "
             "the drawing with what they intended. This is often the age when an inner "
             "critic appears, and \"it won't come out the way I want\" starts to outweigh "
             "the wish to draw.",
}

# --- Duration modifiers -----------------------------------------------------------
DURATION_MODIFIERS: dict[str, str] = {
    "days": "A few days is too short a stretch to talk about a pattern: for now this may "
            "simply be what the last few evenings have been about.",
    "weeks": "A few weeks is long enough to notice a pattern, but the pattern on its own "
             "is not yet enough to explain what is behind it.",
    "months": "A few months means this is a settled way of drawing by now. What stands "
              "behind it cannot be read from the duration alone: the same habit forms in "
              "different children for different reasons.",
    "always": "If it has always been this way, it is more likely {poss} way of drawing "
              "than a change. Then the interesting question is not what changed, but what "
              "this way of drawing gives {obj}.",
}

# ⚠️ OVERRIDES for incompatible concern x duration pairs.
# The generic modifier produces REASSURANCE BY DEFAULT on some pairs - exactly the standing
# risk. The example the mechanism exists for: "presses hard, scribbles over, tears" plus
# "a long time, it's just how they draw" becomes "look at what this way of drawing gives
# them", i.e. it normalizes tearing up the paper.
DURATION_OVERRIDES: dict[tuple[str, str], str] = {
    ("pressure", "always"):
        "If it has always been this way, then it is a settled way of drawing rather than "
        "a recent change. Why {sub} draw{s} like this is not something the duration alone "
        "can show.",
    ("stopped", "always"):
        "If {sub} never drew much to begin with, this is not a change. Then one drawing "
        "certainly cannot settle the reasons - but the drawing itself is still worth "
        "looking at.",
}

# --- The lens: exactly ONE thing to look at, not three ----------------------------
LENS_PREFIX = "If the drawing is nearby, look at just one thing:"
LENSES: dict[str, str] = {
    "black": "is the black used almost everywhere, or only for particular characters, "
             "outlines and details?",
    "monsters": "is the monster alone on the page, or is there someone else beside it?",
    "alone": "is there space left on the page where others could have been, or is the "
             "whole page taken up by one character?",
    "faceless": "are the faces and hands missing on every figure, or only on some?",
    "repeat": "does the whole scene repeat, or does one thing change - the character, "
              "the place, a detail?",
    "pressure": "is the pressure the same across the page, or heavier in one particular "
                "place?",
    "stopped": "in {poss} last piece, what did {sub} carry through to the end, and what "
               "did {sub} leave unfinished?",
}

# The same question on the waiting screen, framed as "while we look, notice this yourself".
WAIT_PREFIX = "While we look, notice one thing yourself:"
WAIT_NEUTRAL = "what did {sub} give the most room to on this page?"

# --- The transition and the ask ---------------------------------------------------
# The last sentence of ASK_STANDARD is NOT cosmetic: without it the parent brings the
# blackest, strangest drawing in the house, and we create a bias in our own data before
# the model has seen anything.
TRANSITION = ("A description is enough to choose where to look. But only the drawing "
              "itself will show what is actually there.")
ASK_ANY = ("Any recent drawing will do. Photograph the whole sheet in ordinary light.")
ASK_NOTES = {
    "standard": "If there are several like this, pick an ordinary example - not the most "
                "frightening and not the most unusual one. A typical piece is more useful "
                "to us than an extreme case.",
    "neutral": "For a first reading, don't pick the prettiest or the most \"correct\" "
               "drawing. Take an ordinary recent piece your child made on their own.",
    "stopped": "If you still have a drawing from around the time {sub} {was} still drawing "
               "on {poss} own initiative, use that one - not a school assignment and not a "
               "copy of a model.",
}

# --- Special path: nothing worries me ---------------------------------------------
NEUTRAL_PATH = [
    "Then there is no need to go looking for a problem.",
    "What is more interesting is what your child chose for themselves: what they decided "
    "to draw, what they gave the most room to, which details they added, and the story "
    "they tell about their own work.",
    "At {band} the drawings can already be looked at against what usually appears and "
    "changes at this stage of development - but the interesting part starts where the age "
    "patterns end and this particular drawing by this particular child begins.",
]

# --- Special path: stopped drawing ------------------------------------------------
# The hard boundary: we do NOT promise to explain why they stopped. Not here and not in
# the analysis. And no grading of the skill - neither "they used to draw well" nor "we'll
# bring the interest back".
STOPPED_PATH = [
    "From one drawing there is no honest way to establish why this happened. And judging "
    "whether {sub} drew well or badly would not give much here either.",
    "What helps more is looking at the last piece {sub} chose to make on {poss} own: what "
    "{sub} wanted to draw, how hard a task {sub} set {refl}, what {sub} carried through "
    "and what {sub} left unfinished.",
]

# --- The "no drawing to hand" branch ----------------------------------------------
# The summary after the questions is NOT hidden behind an email: the email buys saving
# your place and a short note, nothing else. That is honest precisely because it matches
# what actually happened to the parent.
NO_DRAWING_TITLE = "No drawing to hand?"
NO_DRAWING_BODY = ("We'll save your place and email you the link - add the photo when you "
                   "find one. You won't have to answer the questions again.")

# --- The limit: a second upload for the same child. A redirect, not a refusal. -----
LIMIT_TITLE = "{name} already has a free reading of one drawing."
LIMIT_BODY = ("The next step isn't reading another single sheet on its own, but looking at "
              "what repeats between pieces and what changes. The first drawing is saved - "
              "you won't need to add it again.")
LIMIT_CTA = "Look at {name_poss} drawings together"

# --- The selling close. It has the last word in the document. ---------------------
# A table of contents sells better than any "unlock", because it is not a promise - it is
# a list of what exists. The dimension names are exactly the ones in the paid report,
# otherwise the list becomes a lie.
# THE PRICE IS NEVER HARDCODED: it comes from the admin through settings.get_products().
SEVEN_DIRECTIONS = [
    "The world and themes of the drawing", "Character in line and color",
    "Mood and expressiveness", "Story and characters",
    "Creativity and imagination", "Technique and handling of materials",
    "Fine motor skills and detail",
]
SELLING_TITLE = "That was a reading of one drawing. The full report is a portrait of {name}."
# "It won't always be this way" is true rather than manufactured urgency: the service
# really is launching. There must be no timers or countdowns here.
SELLING_LAUNCH = ("Right now the reading of one drawing is free: we are only just launching "
                  "and we want as many parents as possible to try it. It won't always be "
                  "this way.")
SELLING_BODY = ("The full report is built differently. We look at 1-3 drawings at once and "
                "read them across seven dimensions: {directions}. With a score and an "
                "explanation for each.")
SELLING_MAIN = ("And above all, with a chapter of its own about who {name} is: what draws "
                "{obj}, what {poss} temperament is like, what matters to {obj} and how to "
                "support {obj}. About eight pages, a PDF by email within the hour.")
SELLING_READY = "The drawing is already uploaded - you won't need to add it again."
SELLING_GUARANTEE = "Not what you hoped for? We refund within 7 days."
RESULT_CTA_BUTTON = "Build {name_poss} portrait - ${price}"

# ⚠️ DRAFT: the close of the COLORING branch. Here we do NOT sell the report - the parent
# is one step away from giving us usable material, and asking for money at that step loses
# both the drawing and the sale. This branch has one job: get a sheet without someone
# else's outline on it.
COLORING_CTA_TITLE = "Show us a drawing on a blank page."
COLORING_CTA_BODY = ("A coloring page shows how {name} handles a ready-made shape. What "
                     "{sub} invent{s} alone, what scale {sub} work{s} at and what stories "
                     "{sub} tell{s} are only visible where the page started empty. Take any "
                     "recent drawing of {poss} own - an ordinary one, not the prettiest - "
                     "and we'll read that.")
COLORING_CTA_BUTTON = "Add a drawing on a blank page"


def coloring_cta(name: str, address_form: str = "they") -> dict:
    """The close of the coloring branch: a redirect, not a sale."""
    return {
        "title": COLORING_CTA_TITLE,
        "body": g(COLORING_CTA_BODY.replace("{name}", name), address_form),
        "button": COLORING_CTA_BUTTON,
    }


def selling_block(name: str, address_form: str = "they") -> dict:
    """The selling close. Price from the admin, dimensions from the paid report."""
    from config import settings
    prod = settings.get_products().get("snapshot", {})
    price = prod.get("price_usd", 0)
    old_price = prod.get("old_price_usd") or None
    return {
        "title": SELLING_TITLE.format(name=name),
        "launch": SELLING_LAUNCH,
        "body": SELLING_BODY.format(directions=" · ".join(SEVEN_DIRECTIONS)),
        "main": g(SELLING_MAIN.replace("{name}", name), address_form),
        "ready": SELLING_READY,
        "guarantee": SELLING_GUARANTEE,
        "button": RESULT_CTA_BUTTON.format(name_poss=possessive(name), price=price),
        "price": price,
        "old_price": old_price,
    }


# --- The summary block's own heading ----------------------------------------------
# The paragraphs used to run as one undifferentiated wall even though each has its own
# job: the mirror, the age anchor, the lens, the transition. The heading and the
# explainer make visible both WHAT this is and the block's governing rule - we have not
# seen the drawing yet, so we are not guessing.
SUMMARY_LABEL = "Based on what you told us"
SUMMARY_TITLE = "What to look at in {name_poss} drawings"
SUMMARY_EXPLAINER = ("We haven't seen the drawing yet, so there are no guesses here about "
                     "what it means. Only what can be said from your answers and your "
                     "child's age - and where it's worth looking yourself.")
SUMMARY_LENS_LABEL = "One thing worth looking at"

# --- The offer block on the summary screen ----------------------------------------
# The summary screen is the point where the FREE offer is sold. Before this it looked
# like a form: the authored "take one ordinary recent drawing" paragraph hung there with
# no heading and no call to action.
OFFER_TITLE = "Send us that drawing - we'll read it free"
OFFER_LEAD = ("Right now a reading of one drawing is free: we're only just launching. In "
              "about a minute you'll have a reading of this sheet - here on this page and "
              "as a copy by email.")
# Written in human language. "What the tradition of reading children's drawings says about
# a detail" tells a parent nothing - that is our internal vocabulary, not theirs.
OFFER_BULLETS = [
    "what's visible on the page - the medium, the scale, details that are easy to miss",
    "what that detail may mean - and why it's a suggestion, not a diagnosis",
    "what to ask {name} about today",
]
OFFER_HOW = "Which drawing works"
OFFER_FREE_NOTE = "Free, no card, no account."

UPLOAD_TITLE = "Where should we send the reading?"
UPLOAD_BODY = ("The reading appears right here in about a minute, and a copy goes to your "
               "email - so it isn't lost, and so you have something to show. The same "
               "email has your account link: if you ever want the full report, the drawing "
               "is already there and you won't have to upload it again.")
UPLOAD_BUTTON = "Read this drawing"
UPLOAD_NOSPAM = "No newsletter. Only your reading and whatever you order yourself."


def offer_block(name: str, address_form: str = "they") -> dict:
    """The selling block of the summary screen. These strings are interface copy (DRAFT);
    the authored ask for a drawing arrives separately from assemble_summary()['ask'] and
    does not change."""
    return {
        "title": OFFER_TITLE,
        "lead": OFFER_LEAD,
        "bullets": [g(b.replace("{name}", name), address_form) for b in OFFER_BULLETS],
        "how": OFFER_HOW,
        "free_note": OFFER_FREE_NOTE,
    }


# --- Special cases: authored paragraphs. The SERVER emits these on the model's flag,
# not the model itself - fixed wording in the model's mouth drifts between runs. -----
SPARSE_PARAGRAPHS = [
    "In a drawing like this, the interesting thing is not to hunt for a hidden meaning in "
    "every line, but to see how {name} uses drawing itself: whether {sub} repeat{s} a "
    "movement, change{s} direction, come{s} back to something already drawn, and whether "
    "{sub} give{s} {poss} marks names. This, at this age, is where the important thing is "
    "happening.",
]
COLORING_PARAGRAPH = ("We can see this is a coloring page. It is a great way to practice "
                      "fine motor control, but here the child is working inside borders "
                      "someone else set. To see {poss} own character, {poss} sense of "
                      "scale and how {sub} build{s} a story, we need a drawing on a blank "
                      "page.")
# One text for every concern, with NO mirror substituted in. Substituting it read as "you
# were wrong": the parent was not wrong - they were describing other drawings and brought
# this one. This wording does not accuse and invites them to show the right one.
MISMATCH_PARAGRAPH = ("One thing up front: the particular thing you mentioned isn't visible "
                      "in this drawing - there is something else here. We'll read what is "
                      "on this page. If you'd like us to look at the drawings you were "
                      "describing, show us one of those and it will be a different "
                      "conversation.")

# ⚠️ DRAFT: photo retention. The parent needs this next to the upload.
STORAGE_NOTICE = ("We keep the photo of the drawing for 90 days, then delete it. "
                  "The reading itself stays with you at your link.")

ASK_VARIANTS = ("standard", "neutral", "stopped")


def duration_label(concern_key: str, duration_key: str,
                   address_form: str = "they") -> str:
    for d in DURATIONS:
        if d["key"] == duration_key:
            raw = DURATION_LABEL_OVERRIDES.get((concern_key, duration_key), d["label"])
            return g(raw, address_form)
    return ""


def duration_modifier(concern_key: str, duration_key: str,
                      address_form: str = "they") -> tuple[str, bool]:
    """-> (text, whether_an_override_applied)."""
    override = DURATION_OVERRIDES.get((concern_key, duration_key))
    if override is not None:
        return g(override, address_form), True
    return g(DURATION_MODIFIERS.get(duration_key, ""), address_form), False


def assemble_summary(*, concern_key: str, duration_key: str | None, age: int,
                     address_form: str = "they", name: str = "") -> dict:
    """The summary shown after the questions and BEFORE any drawing exists.

    Returns {'paragraphs': [...], 'kinds': [...], 'lens_question': ..., 'ask': ...}.
    A list of paragraphs rather than one string, so that gluing text together inside a
    sentence is physically impossible.
    There is no interpretation here and there cannot be - there is no drawing yet.
    """
    band = age_band(age)
    paragraphs: list[str] = []
    kinds: list[str] = []
    lens_q = None
    override_used = False

    if concern_key == "neutral":
        for p in NEUTRAL_PATH:
            paragraphs.append(g(p.replace("{band}", BAND_LABELS[band]), address_form))
            kinds.append("path")
        return {"paragraphs": paragraphs, "kinds": kinds,
                "lens_question": None, "ask": ASK_ANY,
                "ask_note": g(ASK_NOTES["neutral"], address_form),
                "ask_variant": "neutral", "override_used": False}

    # 1. The mirror: the concern in plain words + the duration line.
    mirror = MIRROR.get(concern_key, "")
    mod, override_used = duration_modifier(concern_key, duration_key or "", address_form)
    first = f"You've noticed that {mirror}."
    paragraphs.append(f"{first} {mod}".strip() if mod else first)
    kinds.append("mirror")

    # 2. The age anchor - a fact about the stage, the only thing allowed here.
    paragraphs.append(g(AGE_ANCHORS[band], address_form))
    kinds.append("anchor")

    # 3. The lens - exactly ONE question. Three bullets is homework, and late in the
    #    evening nobody will do it.
    lens = LENSES.get(concern_key)
    lens_q = g(lens, address_form) if lens else None
    if lens:
        paragraphs.append(f"{LENS_PREFIX} {lens_q}")
        kinds.append("lens")

    if concern_key == "stopped":
        for p in STOPPED_PATH:
            paragraphs.append(g(p, address_form))
            kinds.append("path")
        return {"paragraphs": paragraphs, "kinds": kinds,
                "lens_question": lens_q, "ask": ASK_ANY,
                "ask_note": g(ASK_NOTES["stopped"], address_form),
                "ask_variant": "stopped", "override_used": override_used}

    paragraphs.append(TRANSITION)
    kinds.append("transition")
    return {"paragraphs": paragraphs, "kinds": kinds, "lens_question": lens_q,
            "ask": ASK_ANY, "ask_note": g(ASK_NOTES["standard"], address_form),
            "ask_variant": "standard", "override_used": override_used}


def wait_hint(concern_key: str, address_form: str = "they") -> str:
    """The waiting screen's own question, rather than a progress indicator."""
    body = g(LENSES.get(concern_key, WAIT_NEUTRAL) if concern_key != "neutral"
             else WAIT_NEUTRAL, address_form)
    return f"{WAIT_PREFIX} {body}"
