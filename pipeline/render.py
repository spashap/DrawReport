"""Report rendering: validated JSON -> HTML (hosted) + PDF (WeasyPrint).

Pure functions, no Gemini - reused by the worker, the CLI, and tests (spec §7.1).
The HTML is rendered twice with different static prefixes:
  - hosted variant ("/static") - served to the browser at /r/{token};
  - print variant ("static" relative to BASE_DIR) - fed to WeasyPrint.

Fixed report labels are per-locale (REPORT_STRINGS); the report's own content
already comes back from Gemini in the report language. Dates via Babel.
"""
from __future__ import annotations

import base64
import datetime
import mimetypes
from pathlib import Path

from babel.dates import format_date
from jinja2 import Environment, FileSystemLoader

from config import settings
from pipeline.schema import Report

_env = Environment(loader=FileSystemLoader(settings.BASE_DIR / "templates"),
                   autoescape=True)

# Per-locale fixed strings used by templates/report.html. The dynamic report text
# is already localized by Gemini; only these labels live here.
REPORT_STRINGS = {
    "en": {
        "report_title": "Report",
        "cover_h1": "A developmental report<br>from your child's drawing",
        "drawing_alt": "Drawing",
        "cover_disclaimer": ("This report is an educational observation of the skills visible "
                             "in the drawing. It is not a medical or psychological diagnosis."),
        "h_context": "Details & context",
        "h_intro": "Introduction",
        "h_scores": "Summary scores",
        "callout_h": "How to read the scores",
        "callout_p": ("Scores describe a particular drawing or set of drawings, not the child "
                      "“as a whole.” An average score doesn't mean a problem — "
                      "sometimes a direction is simply less visible in the chosen subject. "
                      "More on this in “How to read the scores in this report” at the "
                      "end of the PDF."),
        "h_dimensions": "Direction by direction",
        "activities_label": "How to develop this:",
        "h_recommendations": "Recommendations for parents",
        "h_directions": "Possible directions to explore",
        "directions_note": ("These ideas are for interest and inspiration, not a prediction of "
                            "the child's abilities."),
        "h_conclusion": "In closing",
        "h_appendix": "How to read the scores in this report",
        "appendix_intro": ("Scores help you quickly see which skills came through most clearly in "
                           "a particular drawing or set of drawings. They are not a rating of the "
                           "child as a person, not a school grade, and not a psychological "
                           "diagnosis."),
        "appendix_lead": "A few things to keep in mind:",
        "appendix_items": [
            ("The score is about the drawing, not the child as a whole.",
             "For example, if a drawing shows a single tree with no people or characters, the "
             "“story & interaction” direction may come through less. That doesn't mean "
             "the child struggles socially."),
            ("An average score doesn't mean a problem.",
             "It can mean the skill was only partly shown, or that the chosen subject gave less "
             "to observe."),
            ("A high score points to a strength in this particular work.",
             "A confident line, a large scale, neat filling, or a thought-out composition can all "
             "reflect well-developed graphic skills."),
            ("One drawing doesn't show a child's whole development.",
             "A series of drawings from different periods gives a fuller picture — especially "
             "if you keep the works with their dates."),
            ("The point of the report isn't to assign a score,",
             "but to point out what's already going well and which simple activities you could "
             "try at home."),
        ],
        "appendix_outro": ("This report is a calm, educational observation of the skills visible "
                           "in a drawing. It does not replace a consultation with a specialist if "
                           "you have serious questions about your child's wellbeing, behavior, or "
                           "development."),
        "footer": ("{site} ({domain}) · Report generated {date} · Educational "
                   "observation, not a medical or psychological diagnosis"),
    },
}


def _strings(locale: str) -> dict:
    return REPORT_STRINGS.get(locale, REPORT_STRINGS[settings.DEFAULT_LOCALE])


def format_report_date(d: datetime.date, locale: str = settings.DEFAULT_LOCALE) -> str:
    """e.g. 'June 18, 2026' - the generation date in the report header (Babel)."""
    return format_date(d, format="long", locale=locale)


def drawing_to_data_uri(path: Path) -> str:
    """Drawing -> data URI: works the same in the browser and WeasyPrint, so the
    hosted report needs no separate protected image route."""
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def render_html(report: Report, drawings: list[dict], generated_date: str,
                locale: str = settings.DEFAULT_LOCALE,
                static_prefix: str = "/static", site_header: bool = False) -> str:
    """drawings: [{"src": data-URI, "caption": str}, ...]
    site_header=True - the site header (hosted variant only; absent in the PDF)."""
    return _env.get_template("report.html").render(
        report=report,
        drawings=drawings,
        generated_date=generated_date,
        s=_strings(locale),
        locale=locale,
        site_name=settings.SITE_NAME,
        site_domain=settings.SITE_DOMAIN,
        static=static_prefix,
        site_header=site_header,
    )


def render_pdf(html_for_print: str, out_path: Path) -> None:
    # import inside: WeasyPrint is heavy and the web process doesn't need it
    from weasyprint import HTML

    out_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_for_print, base_url=str(settings.BASE_DIR)).write_pdf(out_path)


def render_report_files(report: Report, drawings: list[dict], generated_date: str,
                        out_dir: Path, locale: str = settings.DEFAULT_LOCALE,
                        basename: str = "report") -> tuple[Path, Path]:
    """Save both variants. Returns (html_path, pdf_path).

    The renderer runs outside Flask (worker/CLI), so the saved HTML is rendered
    WITHOUT the site header (no url_for/gettext needed). The navigable hosted page
    (/r/<token>, /sample/<token>) is rendered by the Flask route with the header.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    html_hosted = render_html(report, drawings, generated_date, locale,
                              static_prefix="/static", site_header=False)
    html_path = out_dir / f"{basename}.html"
    html_path.write_text(html_hosted, encoding="utf-8")

    html_print = render_html(report, drawings, generated_date, locale, static_prefix="static")
    pdf_path = out_dir / f"{basename}.pdf"
    render_pdf(html_print, pdf_path)

    return html_path, pdf_path
