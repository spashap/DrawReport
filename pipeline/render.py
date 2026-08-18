"""Report rendering: validated JSON -> HTML (hosted) + PDF (WeasyPrint).

Pure functions, no Gemini - reused by the worker, the CLI, and tests (spec §7.1).
The HTML is rendered twice with different static prefixes:
  - hosted variant ("/static") - served to the browser at /r/{token};
  - print variant ("static" relative to BASE_DIR) - fed to WeasyPrint.

Fixed report labels are per-locale (REPORT_STRINGS); the report’s own content
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
        "cover_h1": "Understanding your child<br>through their drawing",
        "drawing_alt": "Drawing",
        "cover_disclaimer": ("This report is a careful, educational observation of what your child’s "
                             "drawing expresses. It is not a medical or psychological diagnosis."),
        "h_context": "Details & context",
        "h_intro": "Introduction",
        "h_about_child": "About your child",
        "h_scores": "Summary scores",
        "callout_h": "How to read the scores",
        "callout_p": ("Scores describe a particular drawing or set of drawings, not the child "
                      "“as a whole.” An average score doesn’t mean a problem — "
                      "sometimes an area simply shows up less in the subject the child chose. "
                      "More on this in “How to read the scores in this report” at the "
                      "end of this report."),
        "h_dimensions": "A closer look at each area",
        "activities_label": "Ways to build on this:",
        "h_understanding": "Understanding & connecting with your child",
        "h_art": "Creative activities to try",
        "h_specialists": "If you’d like to go deeper",
        "specialists_note": ("Optional resources, not a sign that anything is wrong. This is simply "
                             "where to look if you’d like to go further with one of these areas."),
        "h_directions": "Ways to build on your child’s strengths",
        "directions_note": ("These are areas that might be fun for your child to explore, not a "
                            "prediction of who they will become. Any fields we name here are just "
                            "examples."),
        "h_conclusion": "In closing",
        "h_appendix": "How to read the scores in this report",
        "appendix_intro": ("Scores help you quickly see which skills came through most clearly in "
                           "a particular drawing or set of drawings. They are not a rating of the "
                           "child as a person, a school grade, or a psychological "
                           "diagnosis."),
        "appendix_lead": "A few things to keep in mind:",
        "appendix_items": [
            ("The score is about the drawing, not the child as a whole.",
             "For example, if a drawing shows a single tree with no people or characters, the "
             "“story & characters” area may score lower. That doesn’t mean "
             "the child struggles socially."),
            ("An average score doesn’t mean a problem.",
             "It can mean the skill only partly showed up, or that the subject the child picked "
             "gave less to look at."),
            ("A high score points to a strength in this particular drawing.",
             "A confident line, drawing big, careful coloring in, or a well-planned composition "
             "can all reflect strong drawing skills."),
            ("One drawing doesn’t show a child’s whole development.",
             "Several drawings made at different times give a fuller picture, especially "
             "if you write the date on the ones you keep."),
            ("The report isn’t a scorecard.",
             "It’s here to show what’s already going well and to suggest a few simple things you "
             "could try at home."),
        ],
        "appendix_outro": ("This report is an educational observation of what is visible "
                           "in a drawing. It does not replace a consultation with a specialist if "
                           "you have serious questions about your child’s well-being, behavior, or "
                           "development."),
        "footer": ("{site} ({domain}) · Report generated {date} · Educational "
                   "observation, not a medical or psychological diagnosis"),
        # The RUNNING FOOTER printed on every PDF page by @page { @bottom-center }.
        # It lives here, not in report.css, because content differs by locale while the
        # layout does not (UseCase #6). It was hardcoded in Russian in the CSS - inherited
        # from the Golos sibling - and shipped on every page of every English report.
        "page_footer": "DrawReport · educational observation, not a diagnosis · p. ",
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
                static_prefix: str = "/static", site_header: bool = False,
                upsell_text: str = "", disclaimer_text: str = "",
                free_text: str = "") -> str:
    """drawings: [{"src": data-URI, "caption": str}, ...]
    site_header=True - the site header (hosted variant only; absent in the PDF).
    upsell_text / disclaimer_text / free_text - admin-controlled blocks at the END of
    the report (the caller picks the upsell by drawing count); empty = not rendered."""
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
        upsell_text=upsell_text,
        disclaimer_text=disclaimer_text,
        free_text=free_text,
    )


def render_pdf(html_for_print: str, out_path: Path) -> None:
    # import inside: WeasyPrint is heavy and the web process doesn’t need it
    from weasyprint import HTML

    out_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_for_print, base_url=str(settings.BASE_DIR)).write_pdf(out_path)


def render_report_files(report: Report, drawings: list[dict], generated_date: str,
                        out_dir: Path, locale: str = settings.DEFAULT_LOCALE,
                        basename: str = "report",
                        upsell_text: str = "", disclaimer_text: str = "",
                        free_text: str = "") -> tuple[Path, Path]:
    """Save both variants. Returns (html_path, pdf_path).

    The renderer runs outside Flask (worker/CLI), so the saved HTML is rendered
    WITHOUT the site header (no url_for/gettext needed). The navigable hosted page
    (/r/<token>, /sample/<token>) is rendered by the Flask route with the header.

    upsell_text / disclaimer_text / free_text - admin-controlled end-of-report blocks
    (empty = not rendered); threaded into both variants (hosted + print).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    html_hosted = render_html(report, drawings, generated_date, locale,
                              static_prefix="/static", site_header=False,
                              upsell_text=upsell_text, disclaimer_text=disclaimer_text,
                              free_text=free_text)
    html_path = out_dir / f"{basename}.html"
    html_path.write_text(html_hosted, encoding="utf-8")

    html_print = render_html(report, drawings, generated_date, locale, static_prefix="static",
                             upsell_text=upsell_text, disclaimer_text=disclaimer_text,
                             free_text=free_text)
    pdf_path = out_dir / f"{basename}.pdf"
    render_pdf(html_print, pdf_path)

    return html_path, pdf_path
