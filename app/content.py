"""Per-locale landing content: FAQ + illustrative scenarios (Golos kept these as
constants; DrawReport namespaces them by locale). English copy is a DRAFT for owner
review (adapted from positioning-en.md / the Russian originals - not literal translations).

Philosophy 2.3: we show ILLUSTRATIVE SCENARIOS (clearly examples, never real clients),
not fabricated testimonials. Adding a locale = add its FAQ/SCENARIOS entries.
"""
from __future__ import annotations

from config import settings

# (question, answer)
FAQ = {
    "en": [
        ("Is this a psychological or medical assessment?",
         "No. This is an educational observation of the skills visible in a drawing, set "
         "against the typical stages of children’s art. It is not a diagnosis and not a "
         "judgment of your child’s personality or state."),
        # "judges" here used to contradict the answer directly above it, which promises the
        # report is "not a judgment of your child" - two adjacent FAQ answers arguing with
        # each other is worse than either wording on its own.
        ("What ages is it for?",
         "Roughly ages 3 to 12. The report reads skills against what’s typical for your "
         "child’s age, so a 4-year-old and a 9-year-old get genuinely different reports."),
        ("How many drawings can I send?",
         "1 to 3 drawings from the same period. They’re combined into one consolidated report, "
         "and the price is the same whether you send one drawing or three."),
        ("How long does it take?",
         "Usually within an hour. The PDF arrives by email and stays in your private account."),
        ("What exactly do I get?",
         "A warm, personal PDF (about 8 pages): your child’s strengths, how they work with color, "
         "form, detail and story, scores across 7 areas of development with plain-language "
         "explanations, and simple activities you can try at home."),
        ("Do you read emotions or hidden meanings from the colors?",
         "No. We don’t decode hidden feelings, and we don’t claim a color “means” anything. "
         "Every observation is tied to something actually visible in the drawing — the line, the "
         "shapes, the details, the composition."),
        ("Is my child’s drawing kept private?",
         "Yes. Your child’s drawings are never published, never used in advertising, and never "
         "shared with third parties. Only you can see them."),
        ("What if I’m not happy with the report?",
         "Write to us within 7 days and we’ll refund you — no fuss."),
        ("What do you need from me?",
         "A photo of 1–3 drawings your child already made, plus a short bit of context (age, what "
         "they drew with, the subject); it’s a 2-3 minute form. Nothing has to be drawn just for this."),
    ],
}

# Illustrative scenarios - NOT testimonials. Each is explicitly an EXAMPLE of what the
# report can do (never a real client), framed in the new philosophy: it reveals what the
# child expresses and suggests what to ask/notice, without scary interpretations. DRAFT,
# English.
#
# These are now WHOLE SENTENCES, starting with a capital. The template used to prepend
# "For example, a situation like this:" to every one of them under a heading that also
# began "For example" - so each card carried the frame twice over and the scenario itself
# started mid-sentence. The heading does the framing; these just tell the story.
SCENARIOS = {
    "en": [
        "A child draws only in black for a few weeks and a parent starts to worry. The report "
        "shows what actually keeps recurring across their drawings (say, space or dragons), "
        "and that a dark background often makes the bright parts stand out more; then it suggests "
        "what to ask the child and what to watch for in the next drawings. No scary readings.",
        "A child draws the same little house over and over. We help you see what matters to them in "
        "that house: their own world, a sense of safety, the people they love nearby. And how to "
        "ask about it gently.",
        "There’s almost always a single character and no other people. We don’t jump to “your child "
        "isn’t social.” We show that this can simply be a feature of the chosen subject, and "
        "suggest how to support the child’s interest in stories with several characters.",
        "You send three drawings from different days. We show what repeats from work to work (the "
        "steadier traits) and what appeared just once (a moment’s mood), something a single "
        "drawing can’t reveal.",
    ],
}


def _loc(locale: str | None) -> str:
    return locale if locale in FAQ else settings.DEFAULT_LOCALE


def get_faq(locale: str | None = None) -> list[tuple[str, str]]:
    return FAQ[_loc(locale)]


def get_scenarios(locale: str | None = None) -> list[str]:
    return SCENARIOS[_loc(locale)]
