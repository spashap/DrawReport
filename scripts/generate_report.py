"""End-to-end report CLI: images + context -> Gemini -> JSON -> HTML -> PDF.

Usage:
  one drawing:   generate_report.py IMG --context FILE.txt [-o OUTDIR] [--locale en]
  2-3 drawings:  generate_report.py IMG1 IMG2 [IMG3] --context F1.txt F2.txt [F3.txt]
                 (one context file per drawing, in the same order; one file for all
                  is also allowed)
  shared data:   [--common COMMON.txt] - data about the child, separate from the
                 per-drawing stories

Context is the parent's free text (txt, UTF-8). Output: report_raw.json,
report.json, report.html, report.pdf in OUTDIR (default data/test_reports/<image-stem>/).
"""
import argparse
import base64
import datetime
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import settings
from pipeline.llm import ReportGenerationError, generate_report
from pipeline.render import format_report_date, render_report_files
from pipeline.schema import InsufficientReport


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--context", required=True, nargs="+", type=Path,
                    help="one file per drawing (in image order) or one file for all")
    ap.add_argument("--common", type=Path, default=None,
                    help="shared data about the child (optional)")
    ap.add_argument("--locale", default=settings.DEFAULT_LOCALE,
                    help="report language (default: %(default)s)")
    ap.add_argument("-o", "--out", type=Path, default=None)
    args = ap.parse_args()

    if len(args.context) not in (1, len(args.images)):
        ap.error(f"{len(args.context)} contexts, {len(args.images)} images - "
                 f"need 1 file or one per drawing")

    out_dir = args.out or (BASE_DIR / "data" / "test_reports" / args.images[0].stem)
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx_texts = [c.read_text(encoding="utf-8") for c in args.context]
    if len(ctx_texts) == 1 and len(args.images) > 1:
        contexts: list[str] | str = ctx_texts[0]          # one context for all
    else:
        contexts = ctx_texts
    common = args.common.read_text(encoding="utf-8") if args.common else ""

    print(f"-> {settings.LLM_PROVIDER} ({len(args.images)} img, locale {args.locale}), out: {out_dir}")
    try:
        result = generate_report(args.images, contexts, common_context=common,
                                 locale=args.locale, raw_dump_dir=out_dir / "raw")
    except ReportGenerationError as e:
        print("FAILED:", e)
        for line in e.attempts_log:
            print("  ", line.encode("ascii", "replace").decode())
        return 1

    (out_dir / "report_raw.json").write_text(result.raw_json_text, encoding="utf-8")
    print(f"attempts: {result.attempts_used} | prompt {result.prompt_version} | "
          f"{result.provider}:{result.model}"
          f" | repairs: {result.repair_rounds} | lint hits left: {result.lint_hits_left}")

    if isinstance(result.report, InsufficientReport):
        (out_dir / "insufficient.json").write_text(
            result.report.model_dump_json(indent=2), encoding="utf-8")
        print("INSUFFICIENT INPUT:",
              result.report.insufficient_reason.encode("ascii", "replace").decode())
        return 2

    (out_dir / "report.json").write_text(
        json.dumps(result.report.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    n = len(result.image_jpegs)
    drawings = [
        {"src": "data:image/jpeg;base64," + base64.b64encode(j).decode("ascii"),
         "caption": f"Drawing {i + 1}" if n > 1 else result.report.child.name}
        for i, j in enumerate(result.image_jpegs)
    ]
    html_path, pdf_path = render_report_files(
        result.report, drawings,
        generated_date=format_report_date(datetime.date.today(), args.locale),
        out_dir=out_dir, locale=args.locale,
    )
    print(f"OK html: {html_path}")
    print(f"OK pdf:  {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
