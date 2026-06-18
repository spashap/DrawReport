"""Per-locale landing content: FAQ + testimonials (Golos kept these as constants;
DrawReport namespaces them by locale). English copy is a DRAFT for owner review
(adapted from positioning-en.md / the Russian originals - not literal translations).

Adding a locale = add its FAQ/TESTIMONIALS entries. No business-logic change.
"""
from __future__ import annotations

from config import settings

# (question, answer)
FAQ = {
    "en": [
        ("Is this a psychological or medical assessment?",
         "No. This is an educational observation of the skills visible in a drawing, set "
         "against the typical stages of children's art. It is not a diagnosis and not a "
         "judgment of your child's personality or state."),
        ("What ages is it for?",
         "Roughly ages 3 to 12. The report judges skills relative to what's typical for your "
         "child's age, so a 4-year-old and a 9-year-old get genuinely different reports."),
        ("How many drawings can I send?",
         "1 to 3 drawings from the same period. They're combined into one consolidated report - "
         "the price is the same whether you send one drawing or three."),
        ("How long does it take?",
         "Usually within the hour. The PDF arrives by email and stays in your private account."),
        ("What exactly do I get?",
         "A warm, personal PDF (about 8 pages): your child's strengths, how they work with color, "
         "form, detail and story, scores across 7 areas of development with plain-language "
         "explanations, and simple activities you can try at home."),
        ("Do you read emotions or hidden meanings from the colors?",
         "No. We don't decode hidden feelings, and we don't claim a color \"means\" anything. "
         "Every observation is tied to something actually visible in the drawing - the line, the "
         "shapes, the details, the composition."),
        ("Is my child's drawing kept private?",
         "Yes. Your child's drawings are never published, never used in advertising, and never "
         "shared with third parties. Only you can see them."),
        ("What if I'm not happy with the report?",
         "Write to us within 7 days and we'll refund you - no fuss."),
        ("What do you need from me?",
         "A photo of 1-3 drawings your child already made, plus a short bit of context (age, what "
         "they drew with, the subject) - a 2-3 minute form. Nothing needs to be drawn specially."),
    ],
}

# Testimonials - PLACEHOLDERS until the owner provides real ones. The strongest
# "takes the worry away" testimonial is first (positioning rule). DRAFT, English.
TESTIMONIALS = {
    "en": [
        ("My son drew only with a black pen for a month and I'd worked myself up over it. "
         "The report calmly showed he was working on outlines right now - and sure enough, the "
         "colors came back a month later.",
         "Anna, Mike's mom (age 5)"),
        ("It was like really looking at my daughter's drawings for the first time. Half the "
         "observations I'd never have noticed on my own.",
         "Maria, Sophie's mom (age 6)"),
        ("The skeptic in me went looking for generic filler and didn't find any. Every "
         "observation is tied to a specific detail - the shading, the line, how the figure is "
         "built.",
         "David, Vera's dad (age 7)"),
        ("We printed the report and hung it next to the drawing. My daughter walks around proud: "
         "\"that's written about me.\"",
         "Olga, Katie's mom (age 6)"),
        ("The most useful part was the activities at the end: specific, ten minutes each. My son "
         "now asks to \"play artist\" himself.",
         "Natalie, Ethan's mom (age 4)"),
        ("I sent three drawings and got back one connected story: what repeats from work to work, "
         "and what showed up for the first time. Not at all what I expected from a \"photo "
         "analysis.\"",
         "Sarah, Mia's mom (age 8)"),
    ],
}


def _loc(locale: str | None) -> str:
    return locale if locale in FAQ else settings.DEFAULT_LOCALE


def get_faq(locale: str | None = None) -> list[tuple[str, str]]:
    return FAQ[_loc(locale)]


def get_testimonials(locale: str | None = None) -> list[tuple[str, str]]:
    return TESTIMONIALS[_loc(locale)]
