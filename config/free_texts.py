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

TYPOGRAPHY: visible strings use curly apostrophes and quotes and a real em dash, matching
the rest of the site. A spaced ASCII hyphen standing in for a dash reads as a typo.
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
    """Sophie -> Sophie's; Chris -> Chris's.

    Always -'s, including after a final s. That is Chicago style and what US consumer
    writing does with a first name; the bare apostrophe (Chris') is a newsroom
    convention and reads as a typo to a parent.
    """
    name = (name or "").strip()
    if not name:
        return ""
    return name + "’s"


# --- Age bands --------------------------------------------------------------------
# The age is asked as a BAND, not an exact number: one tap instead of a spinner, on a
# phone, late in the evening. The band is also what the age anchor speaks about.
AGE_BANDS: list[dict] = [
    {"key": "3-4", "label": "3–4", "age": 4},
    {"key": "5-6", "label": "5–6", "age": 6},
    {"key": "7-9", "label": "7–9", "age": 8},
    {"key": "10-12", "label": "10–12", "age": 11},
]
BAND_BY_KEY = {b["key"]: b for b in AGE_BANDS}
# "ages 3-4" and not "3-4 years old": this label is substituted into a sentence about the
# DRAWINGS ("At {band} the drawings..."), where "years old" attaches to the wrong noun.
BAND_LABELS = {b["key"]: f"ages {b['label']}" for b in AGE_BANDS}


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
    {"key": "monsters", "label": "Draws monsters, weapons, fights, scary scenes"},
    {"key": "alone", "label": "Draws themselves alone, with no other people"},
    # Every label starts with a present-tense verb about the CHILD, so the list scans as
    # one grammatical shape on the home page. "very schematic" was also a word no US
    # parent uses about a drawing - it is the reviewer's term, not the customer's.
    {"key": "faceless", "label": "Draws people with no faces or hands, just outlines"},
    {"key": "repeat", "label": "Draws the same thing over and over"},
    {"key": "pressure", "label": "Presses hard, scribbles over the drawing, tears the paper"},
    {"key": "stopped", "label": "Has stopped drawing, or gives up when it doesn’t come out right"},
    {"key": "neutral", "label": "Nothing worries me — I’m just curious what the "
                                "drawing says about my child"},
]
CONCERN_KEYS = [c["key"] for c in CONCERNS]

# --- Step 2: how long ------------------------------------------------------------
DURATION_QUESTION = "How long has this been going on?"
DURATION_QUESTION_STOPPED = "How long has it been since {sub} drew much?"

DURATIONS: list[dict] = [
    {"key": "days", "label": "A few days"},
    {"key": "weeks", "label": "A few weeks"},
    {"key": "months", "label": "A few months"},
    {"key": "always", "label": "A long time — it’s just how {sub} draw{s}"},
]
# For "stopped drawing" the fourth option has to read differently: "it's just how they
# draw" about NOT drawing is nonsense.
DURATION_LABEL_OVERRIDES: dict[tuple[str, str], str] = {
    ("stopped", "always"): "{sub} never drew much to begin with",
}

# --- Step 3: the parent's own words -----------------------------------------------
FREE_TEXT_QUESTION = "What have you noticed in {poss} drawings? A line or two, or skip it."
FREE_TEXT_PLACEHOLDER = "For example: three weeks of nothing but a black marker"

ADDRESS_QUESTION = "Which pronoun should we use for your child?"
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
# "scary scenes" in #2 - monsters, weapons and fights are visible on the page, whereas
# "scary" is already a judgment.
MIRROR: dict[str, str] = {
    "black": "your child draws mostly in black",
    "monsters": "your child draws monsters, weapons, and fights",
    "alone": "your child draws themselves alone, with no one else in the picture",
    "faceless": "the people in the drawings don’t have faces or hands, "
                "just outlines",
    "repeat": "your child draws the same thing over and over",
    "pressure": "your child presses down hard, scribbles over the drawing "
                "or tears it",
    "stopped": "your child has stopped drawing, or gives up when it doesn’t come "
               "out right",
}

# --- Age anchors: a fact about the developmental stage. The ONLY thing allowed in the
# summary that is not a paraphrase of what the parent said. -------------------------
AGE_ANCHORS: dict[str, str] = {
    "3-4": "At three and four, a child’s hand is still learning to steer the crayon, and "
           "drawing is mostly about making marks rather than making a picture of "
           "something. Closing a shape, changing direction, going back to something "
           "already drawn — at this age, those are a big deal.",
    "5-6": "At five and six, the same child can use color, line, and the tricks {sub} "
           "already know{s} completely differently from one drawing to the next. At this "
           "age it’s still easy to mistake a one-off for a habit.",
    "7-9": "Between seven and nine, a child works out a system of their own: how to set "
           "up a scene, where the ground line goes, how to show what’s happening. The "
           "choices get more deliberate — and so does how hard they are on themselves.",
    "10-12": "Between ten and twelve, a child starts drawing for realism and measuring "
             "the drawing against what they had in mind. This is often when the inner "
             "critic shows up, and “it never looks the way I want” starts to outweigh "
             "the urge to draw.",
}

# --- Duration modifiers -----------------------------------------------------------
DURATION_MODIFIERS: dict[str, str] = {
    "days": "A few days isn’t long enough to call it a pattern. For now it may just be "
            "what the last few evenings happened to be about.",
    "weeks": "A few weeks is long enough to be a pattern. What the pattern means is a "
             "separate question, and one drawing won’t settle it.",
    "months": "A few months means this is a settled way of drawing by now. How long it "
              "has gone on doesn’t tell you why — the same habit shows up in different "
              "children for completely different reasons.",
    "always": "If it has always been this way, it’s more likely to be {poss} way of "
              "drawing than a change. The question worth asking is what {sub} get{s} out "
              "of drawing like this.",
}

# ⚠️ OVERRIDES for incompatible concern x duration pairs.
# The generic modifier produces REASSURANCE BY DEFAULT on some pairs - exactly the standing
# risk. The example the mechanism exists for: "presses hard, scribbles over, tears" plus
# "a long time, it's just how they draw" becomes "look at what this way of drawing gives
# them", i.e. it normalizes tearing up the paper.
DURATION_OVERRIDES: dict[tuple[str, str], str] = {
    ("pressure", "always"):
        "If it has always been this way, it’s a settled way of drawing rather than a "
        "recent change. How long it has gone on can’t tell you why {sub} draw{s} like "
        "this.",
    ("stopped", "always"):
        "If {sub} never drew much to begin with, this isn’t a change. One drawing "
        "certainly can’t explain why — but it’s still worth looking at.",
}

# --- The lens: exactly ONE thing to look at, not three ----------------------------
LENS_PREFIX = "If the drawing is handy, look at just one thing:"
LENSES: dict[str, str] = {
    "black": "is the black all over the page, or just on certain characters, outlines, "
             "and details?",
    "monsters": "is the monster alone on the page, or is there someone else beside it?",
    "alone": "is there empty space where someone else could have gone, or does the one "
             "character fill the whole page?",
    "faceless": "are the faces and hands missing from every figure, or only from some?",
    "repeat": "does the whole scene repeat, or does one thing change — the character, "
              "the place, a detail?",
    "pressure": "is the pressure the same across the page, or heavier in one spot?",
    "stopped": "in the last thing {sub} drew, what did {sub} finish, and what did {sub} "
               "leave unfinished?",
}

# The same question on the waiting screen, framed as "while we read it, look for this
# yourself". You can ask someone to LOOK FOR something; you cannot order them to notice it.
WAIT_PREFIX = "While we read it, look for one thing yourself:"
WAIT_NEUTRAL = "what did {sub} give the most room to on this page?"

# --- The transition and the ask ---------------------------------------------------
# The last sentence of ASK_STANDARD is NOT cosmetic: without it the parent brings the
# blackest, strangest drawing in the house, and we create a bias in our own data before
# the model has seen anything.
TRANSITION = ("What you’ve told us is enough to know where to look. Only the drawing "
              "can show what’s actually there.")
ASK_ANY = ("Any recent drawing will do. Take a photo of the whole sheet in daylight if "
           "you can.")
ASK_NOTES = {
    "standard": "If there are several like this, pick an ordinary one — not the scariest "
                "and not the strangest. A typical drawing tells us more than an extreme "
                "one.",
    "neutral": "For a first reading, don’t pick the prettiest one or the most “correct” "
               "one. Take an ordinary recent drawing your child made on their own.",
    "stopped": "If you still have something from back when {sub} {was} drawing without "
               "being asked, use that — not a school assignment, and not a copy of a "
               "picture.",
}

# --- Special path: nothing worries me ---------------------------------------------
NEUTRAL_PATH = [
    "Good — then there’s no need to go looking for a problem.",
    "What’s more interesting is what your child picked out for themselves: what they "
    "decided to draw, what they gave the most room to, which details they added, and the "
    "story they tell about it.",
    "At {band}, you can already read a drawing against what usually shows up and changes "
    "at this stage. The interesting part starts where the age patterns run out and this "
    "one drawing by this one child begins.",
]

# --- Special path: stopped drawing ------------------------------------------------
# The hard boundary: we do NOT promise to explain why they stopped. Not here and not in
# the analysis. And no grading of the skill - neither "they used to draw well" nor "we'll
# bring the interest back".
STOPPED_PATH = [
    "One drawing can’t honestly tell you why this happened. And deciding whether {sub} "
    "drew well or badly wouldn’t get you very far either.",
    "What helps more is looking at the last drawing {sub} made without being asked: what "
    "{sub} wanted to draw, how much {sub} took on, what {sub} finished and what {sub} "
    "left unfinished.",
]

# --- The "no drawing handy" branch ------------------------------------------------
# The summary after the questions is NOT hidden behind an email: the email buys saving
# your place and a short note, nothing else. That is honest precisely because it matches
# what actually happened to the parent.
NO_DRAWING_TITLE = "No drawing handy?"
NO_DRAWING_BODY = ("We’ll save your place and email you a link — add a photo whenever you "
                   "find one. You won’t have to answer the questions again.")

# --- The limit: a second upload for the same child. A redirect, not a refusal. -----
LIMIT_TITLE = "We’ve already read one of {name_poss} drawings."
LIMIT_BODY = ("The next step is to look at what repeats from one drawing to the next, and "
              "what changes. The first drawing is saved — you won’t need to add it again.")
LIMIT_CTA = "Compare {name_poss} drawings side by side"

# --- The selling close. It has the last word in the document. ---------------------
# A table of contents sells better than any "unlock", because it is not a promise - it is
# a list of what exists. The dimension names are exactly the ones in the paid report,
# otherwise the list becomes a lie.
# ⚠️ SOURCE OF TRUTH: pipeline/prompt.py DIMENSIONS["en"] - those labels are what the model
# is told to score and what render.py prints in the PDF. This list drifted away from them
# once already ("Mood and expressiveness" for "Mood & expression", "Technique and handling
# of materials" for "Technique & materials"), which made the sales list quietly false. If
# you change one, change both.
# THE PRICE IS NEVER HARDCODED: it comes from the admin through settings.get_products().
SEVEN_DIRECTIONS = [
    "World & themes", "Character in line & color",
    "Mood & expression", "Story & characters",
    "Creativity & imagination", "Technique & materials",
    "Fine motor & detail",
]
SELLING_TITLE = "That was a reading of one drawing. The full report is a portrait of {name}."
# "That won't last forever" is true rather than manufactured urgency: the service really
# is launching. There must be no timers or countdowns here.
SELLING_LAUNCH = ("Right now a reading of one drawing is free — we just launched, and we "
                  "want as many parents as possible to try it. That won’t last forever.")
SELLING_BODY = ("The full report is built differently. We look at 1–3 drawings together "
                "and read them across seven areas — {directions} — with a score and a "
                "plain-language explanation for each.")
SELLING_MAIN = ("Above all, it has a chapter of its own about who {name} is: what pulls "
                "{obj} in, what {poss} temperament is like, what matters to {obj}, and "
                "how to support {obj}. About eight pages, emailed as a PDF within the hour.")
SELLING_READY = "The drawing is already uploaded — you won’t need to add it again."
SELLING_GUARANTEE = "Not what you hoped for? Ask within 7 days and we’ll refund you."
RESULT_CTA_BUTTON = "Get {name_poss} full report — ${price}"

# ⚠️ DRAFT: the close of the COLORING branch. Here we do NOT sell the report - the parent
# is one step away from giving us usable material, and asking for money at that step loses
# both the drawing and the sale. This branch has one job: get a sheet without someone
# else's outline on it.
COLORING_CTA_TITLE = "Show us a drawing on a blank page."
COLORING_CTA_BODY = ("A coloring page shows how {name} handles a shape someone else drew. "
                     "What {sub} come{s} up with, how big {sub} draw{s}, the stories "
                     "{sub} tell{s} — those only show up on a page that started out "
                     "empty. Send any recent drawing of {poss} own, an ordinary one "
                     "rather than the prettiest, and we’ll read that.")
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
SUMMARY_EXPLAINER = ("We haven’t seen the drawing yet, so nothing here is a guess about "
                     "what it means. This is only what your answers and your child’s age "
                     "can tell us, plus one thing worth looking at yourself.")
SUMMARY_LENS_LABEL = "One thing worth looking at"

# --- The offer block on the summary screen ----------------------------------------
# The summary screen is the point where the FREE offer is sold. Before this it looked
# like a form: the authored "take one ordinary recent drawing" paragraph hung there with
# no heading and no call to action.
OFFER_TITLE = "Send us that drawing and we’ll read it free"
OFFER_LEAD = ("Right now a reading of one drawing is free — we just launched. In about a "
              "minute you’ll have a reading of this drawing, here on the page and as a "
              "copy by email.")
# Written in human language. "What the tradition of reading children's drawings says about
# a detail" tells a parent nothing - that is our internal vocabulary, not theirs. Neither
# is "the medium" or "the scale": that is gallery-catalog register.
OFFER_BULLETS = [
    "what’s on the page — what it’s drawn with, how big things are, details that are "
    "easy to miss",
    "what that detail may mean — and why it’s a suggestion, not a diagnosis",
    "what to ask {name} about today",
]
OFFER_HOW = "Which drawing to send"
OFFER_FREE_NOTE = "Free. No credit card, no account."

UPLOAD_TITLE = "Where should we send the reading?"
UPLOAD_BODY = ("The reading shows up right here in about a minute, and a copy goes to "
               "your email so you don’t lose it. That email also has your account link: "
               "if you ever want the full report, the drawing is already there and you "
               "won’t have to upload it again.")
UPLOAD_BUTTON = "Get my reading"
UPLOAD_NOSPAM = "No newsletter — just your reading, and anything you order."


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
    "In a drawing like this, the thing to watch is how {name} uses drawing itself: "
    "whether {sub} repeat{s} a movement, change{s} direction, come{s} back to something "
    "already drawn, whether {sub} give{s} {poss} marks names. At this age, that’s where "
    "the real work is happening — not in the hidden meaning of any one line.",
]
COLORING_PARAGRAPH = ("This looks like a coloring page. Those are great practice for fine "
                      "motor control, but your child is working inside lines someone else "
                      "drew. To see {poss} own character, how big {sub} draw{s}, and how "
                      "{sub} build{s} a story, we need a drawing on a blank page.")
# One text for every concern, with NO mirror substituted in. Substituting it read as "you
# were wrong": the parent was not wrong - they were describing other drawings and brought
# this one. This wording does not accuse and invites them to show the right one.
MISMATCH_PARAGRAPH = ("One thing up front: what you described isn’t in this particular "
                      "drawing — this one is something else. We’ll read what’s on this "
                      "page. If you’d like us to look at the drawings you were "
                      "describing, send us one of those and we’ll read that instead.")

# ⚠️ DRAFT: photo retention. The parent needs this next to the upload.
STORAGE_NOTICE = ("We keep the photo for 90 days, then delete it. Your reading stays at "
                  "your link.")

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
    first = f"You’ve noticed that {mirror}."
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
