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
            {"key": "name", "label": "Child's name", "type": "text", "required": True,
             "hint": "The name appears in the report - it's how we'll refer to the young artist"},
            {"key": "gender", "label": "Gender", "type": "select", "required": True,
             "options": [("f", "Girl"), ("m", "Boy")],
             "hint": "So we refer to your child correctly in the report"},
            {"key": "birth_ym", "label": "Month and year of birth", "type": "ym",
             "required": True, "years_back": 18,
             "hint": "Skills are judged relative to age - this is key information"},
        ],
        "drawing": [
            {"key": "drawn_at", "label": "When it was drawn (month and year)", "type": "ym",
             "required": True, "years_back": 8, "default_current_year": True,
             "hint": "Helps track development over time"},
            {"key": "theme", "label": "What was asked / subject of the drawing", "type": "combo",
             "required": True, "placeholder": "Choose or write your own",
             "presets": ["Free choice - drew whatever they wanted", "Draw the family",
                         "Draw a person", "A favorite character or cartoon hero",
                         "An animal", "A house", "Nature, a landscape",
                         "A school or daycare assignment", "Copied from a model or from life"],
             "hint": "Were they asked to draw it, or did they pick the subject themselves?"},
            {"key": "materials", "label": "What they drew with", "type": "combo", "required": False,
             "placeholder": "Choose or write your own",
             "presets": ["Markers", "Colored pencils", "Pencil", "Crayons",
                         "Paint (gouache, watercolor)", "Pen", "Pastels", "Mixed materials"],
             "hint": "The material shapes the lines - without it we might judge the tool instead of the child"},
            {"key": "time_spent", "label": "How long they spent drawing", "type": "select",
             "required": False,
             "options": [("under 5 minutes", "under 5 minutes"),
                         ("about 10 minutes", "about 10 minutes"),
                         ("about 20 minutes", "about 20 minutes"),
                         ("about 30 minutes", "about 30 minutes"),
                         ("about an hour", "about an hour"),
                         ("more than an hour", "more than an hour")],
             "hint": "5 rushed minutes and half an hour of absorbed work are different stories"},
            {"key": "noticed", "label": "What stood out to you", "type": "textarea",
             "required": False, "placeholder": "e.g. drew eyes with eyelashes for the first time",
             "hint": "\"First time\" is especially valuable: new details mark emerging skills"},
            {"key": "extra", "label": "Any other context", "type": "textarea",
             "required": False, "placeholder": "Anything you think is worth sharing",
             "hint": "Context changes the read: drew from life, was in a hurry, left-handed, just started drawing..."},
        ],
        "email": {"key": "email", "label": "Email for the report", "type": "email",
                  "required": True, "placeholder": "you@example.com",
                  "hint": "The PDF report and your account access go here"},
        "coupon": {"key": "coupon", "label": "Coupon code", "type": "text",
                   "required": False, "placeholder": "If you have one",
                   "hint": "The discount applies straight to the total"},
        "gender_labels": {"f": "girl", "m": "boy"},
        "story_labels": {
            "drawn_date": "Drawing date", "age": "Child's age at the time of the drawing",
            "subject": "Subject", "materials": "Materials", "time": "Time spent",
            "noticed": "What the parent noticed", "extra": "Additional",
        },
        "common_labels": {"name": "Artist's name", "gender": "Gender", "birth": "Month/year of birth"},
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
    """One drawing's form fields -> free-text "story" for the prompt. age_display =
    the computed age at the drawing date (we don't trust the model with date math)."""
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
