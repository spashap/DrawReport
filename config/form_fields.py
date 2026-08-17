"""Order-form field config (Golos spec §5: render + validation driven by config).

Per-locale (English ships first). type: text | textarea | email | select | ym | combo.
  combo = input + datalist (pick a preset OR free text)
  ym    = two number selects (month + year); input type=month was rejected upstream
years_back = how many years back the year list goes.
"""
from __future__ import annotations

from config import settings

_FIELDS = {
    "en": {
        "child": [
            {"key": "name", "label": "Child’s name", "type": "text", "required": True,
             "hint": "We’ll use this name throughout the report"},
            {"key": "gender", "label": "Gender", "type": "select", "required": True,
             "options": [("f", "Girl"), ("m", "Boy")],
             "hint": "So we get your child’s pronouns right in the report"},
            {"key": "birth_ym", "label": "Month and year of birth", "type": "ym",
             "required": True, "years_back": 18,
             "hint": "Every skill is read against your child’s age, so this one matters"},
        ],
        "drawing": [
            {"key": "drawn_at", "label": "When it was drawn (month and year)", "type": "ym",
             "required": True, "years_back": 8, "default_current_year": True,
             "hint": "Helps track development over time"},
            {"key": "theme", "label": "Subject of the drawing", "type": "combo",
             "required": True, "placeholder": "Choose or write your own",
             "presets": ["Their own idea — drew whatever they wanted", "Draw the family",
                         "Draw a person", "A favorite character from a show, game, or book",
                         "An animal", "A house", "A landscape or nature scene",
                         "A school or daycare assignment", "Copied from a picture, or drawn from life"],
             "hint": "Were they asked to draw it, or did they pick the subject themselves?"},
            {"key": "materials", "label": "What they drew with", "type": "combo", "required": False,
             "placeholder": "Choose or write your own",
             "presets": ["Markers", "Colored pencils", "Pencil", "Crayons",
                         "Paint (gouache, watercolor)", "Pen", "Pastels", "Mixed materials"],
             "hint": "What they drew with changes the line — without it, we might end up describing the marker instead of your child"},
            {"key": "time_spent", "label": "How long they spent drawing", "type": "select",
             "required": False,
             "options": [("under 5 minutes", "Under 5 minutes"),
                         ("about 10 minutes", "About 10 minutes"),
                         ("about 20 minutes", "About 20 minutes"),
                         ("about 30 minutes", "About 30 minutes"),
                         ("about an hour", "About an hour"),
                         ("more than an hour", "More than an hour")],
             "hint": "Five rushed minutes and half an hour of absorbed work tell us different things"},
            {"key": "noticed", "label": "What stood out to you", "type": "textarea",
             "required": False, "placeholder": "e.g. drew eyes with eyelashes for the first time",
             "hint": "\"First time\" is worth a lot — a new detail usually means a new skill"},
            {"key": "extra", "label": "Anything else we should know", "type": "textarea",
             "required": False, "placeholder": "Anything you think is worth sharing",
             "hint": "Small things change the read — drew from life, was in a hurry, left-handed, only just started drawing"},
        ],
        "email": {"key": "email", "label": "Email for the report", "type": "email",
                  "required": True, "placeholder": "you@example.com",
                  "hint": "We’ll send the PDF report here, along with the link to your account"},
        "coupon": {"key": "coupon", "label": "Coupon code", "type": "text",
                   "required": False, "placeholder": "If you have one",
                   "hint": "We’ll take the discount off the total"},
        "gender_labels": {"f": "girl", "m": "boy"},
        "story_labels": {
            "drawn_date": "Drawing date", "age": "Child’s age at the time of the drawing",
            "subject": "Subject", "materials": "Materials", "time": "Time spent",
            "noticed": "What the parent noticed", "extra": "Additional",
        },
        "common_labels": {"name": "Artist’s name", "gender": "Gender", "birth": "Month/year of birth"},
    },
}


def _loc(locale):
    return locale if locale in _FIELDS else settings.DEFAULT_LOCALE


def child_fields(locale=None):
    return _FIELDS[_loc(locale)]["child"]


def drawing_fields(locale=None):
    return _FIELDS[_loc(locale)]["drawing"]


def email_field(locale=None):
    return _FIELDS[_loc(locale)]["email"]


def coupon_field(locale=None):
    return _FIELDS[_loc(locale)]["coupon"]


def child_to_common(child: dict, locale=None) -> str:
    """Child block -> common_context for the prompt (build_user_prompt)."""
    f = _FIELDS[_loc(locale)]
    lab, gl = f["common_labels"], f["gender_labels"]
    g = child.get("gender", "")
    return "\n".join([
        f"{lab['name']}: {child.get('name', '')}",
        f"{lab['gender']}: {gl.get(g, g)}",
        f"{lab['birth']}: {child.get('birth_ym', '')}",
    ])


def drawing_to_story(drawing: dict, age_display: str | None = None, locale=None) -> str:
    """One drawing’s form fields -> free-text "story" for the prompt. age_display =
    the computed age at the drawing date (we don’t trust the model with date math)."""
    lab = _FIELDS[_loc(locale)]["story_labels"]
    lines = [f"{lab['drawn_date']}: {drawing.get('drawn_at', '')}",
             f"{lab['subject']}: {drawing.get('theme', '')}"]
    if age_display:
        lines.insert(1, f"{lab['age']}: {age_display}")
    for label_key, key in (("materials", "materials"), ("time", "time_spent"),
                           ("noticed", "noticed"), ("extra", "extra")):
        if drawing.get(key):
            lines.append(f"{lab[label_key]}: {drawing[key]}")
    return "\n".join(lines)
