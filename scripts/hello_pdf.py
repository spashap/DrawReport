"""Milestone M0: prove WeasyPrint renders our self-hosted fonts with the $ glyph.

Run: venv/Scripts/python.exe scripts/hello_pdf.py
Output: data/hello.pdf — open it and check all three font families + the $ sign.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from weasyprint import HTML

HTML_DOC = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="static/css/fonts.css">
<style>
  @page { size: A4; margin: 2cm; }
  body { font-family: Inter, sans-serif; color: #3A2A1C; background: #FCEFDF; }
  h1 { font-family: Rubik, sans-serif; font-weight: 900; font-size: 32pt; letter-spacing: -1px; }
  h2 { font-family: Rubik, sans-serif; font-weight: 800; font-size: 18pt; color: #3E4E78; }
  .hand { font-family: Caveat, cursive; font-weight: 700; font-size: 20pt; color: #B9722A; }
  .hand2 { font-family: Caveat, cursive; font-weight: 600; font-size: 16pt; }
  p { font-size: 12pt; line-height: 1.5; }
  .w500 { font-weight: 500; }
  .w600 { font-weight: 600; }
</style>
</head>
<body>
  <h1>Every drawing has a voice. Let's hear it.</h1>
  <h2>Rubik 800 — ABCDEFGHIJKLMNOPQRSTUVWXYZ</h2>
  <p>Inter 400: The quick brown fox jumps over the lazy dog. 1234567890 $29 $4,999</p>
  <p class="w500">Inter 500: A personal report on your child's development from their drawings.</p>
  <p class="w600">Inter 600: Seven areas of development, scored and explained, with at-home activities.</p>
  <div class="hand">Caveat 700: "Our House", Mia, age 5 — creativity 8/10</div>
  <div class="hand2">Caveat 600: PDF by email within the hour - nothing special to draw</div>
</body>
</html>"""


def main() -> None:
    out = BASE_DIR / "data" / "hello.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=HTML_DOC, base_url=str(BASE_DIR)).write_pdf(out)
    print(f"OK: {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
