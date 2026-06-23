"""Milestone M2: render the fake sample report to HTML + PDF.

Run: venv/Scripts/python.exe scripts/render_sample.py
Output: data/reports/sample/report.html (browser) + report.pdf
"""
import datetime
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import settings
from pipeline.render import drawing_to_data_uri, format_report_date, render_report_files
from pipeline.schema import validate_report


def main() -> None:
    locale = settings.DEFAULT_LOCALE
    samples = BASE_DIR / "pipeline" / "samples"
    raw = json.loads((samples / "sample_report.json").read_text(encoding="utf-8"))
    report = validate_report(raw)
    print("schema: valid |", len(report.dimensions), "dimensions")

    drawings = [{
        "src": drawing_to_data_uri(samples / "sample_drawing.png"),
        "caption": '"My house", Liam, age 6',
    }]

    out_dir = settings.REPORTS_DIR / "sample"
    html_path, pdf_path = render_report_files(
        report, drawings,
        generated_date=format_report_date(datetime.date.today(), locale),
        out_dir=out_dir, locale=locale,
    )
    print(f"OK html: {html_path}")
    print(f"OK pdf:  {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
