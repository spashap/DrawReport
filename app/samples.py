"""Sample reports for the landing (Golos spec §4.1.3), per-locale.

When the owner adds real generated reports under data/test_reports/<name>/report.json
(+ the drawing image), list them in _SAMPLE_DEFS and they appear on the landing and at
/<locale>/sample/<token>. A built-in sample (pipeline/samples) ships so the landing
always has at least one example for QA before live generation is wired up.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from config import settings


def _first_sentence(text: str, max_len: int = 220) -> str:
    """First sentence, not breaking on initials ("Emma R.") - a period counts as a
    sentence end only after a lowercase letter / quote / paren."""
    m = re.search(r"^(.*?[a-z\"'\)])\.(?=\s|$)", text)
    s = (m.group(1) + ".") if m else text
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


# Per-locale sample definitions. Order = carousel order. hero=True -> polaroid on
# the first screen. report_path is relative to BASE_DIR.
_SAMPLE_DEFS = {
    "en": [
        dict(token="sample-liam", report_path="pipeline/samples/sample_report.json",
             drawing="pipeline/samples/sample_drawing.png",
             caption='"My house", Liam, age 6', hero=True, n_drawings=1),
    ],
}


@dataclass
class Sample:
    token: str
    locale: str
    name: str
    age_display: str
    caption: str
    thumb_url: str
    thumb_w: int
    thumb_h: int
    top_scores: list[dict]     # [{title, score}] - 3 rows for the card
    badge: str                 # "creativity 8/10"
    quote: str                 # short quote from the report
    report_path: Path          # report.json, rendered on the fly by the route
    hero: bool = True
    n_drawings: int = 1


def _thumb(drawing: Path, token: str, size: int = 480, quality: int = 72) -> tuple[str, int, int]:
    """Make a card thumbnail in static/. SVGs are copied as-is (PIL can't raster
    them); raster images become a webp (spec §4.2)."""
    out_dir = settings.BASE_DIR / "static" / "img" / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    if drawing.suffix.lower() == ".svg":
        out = out_dir / f"{token}.svg"
        shutil.copyfile(drawing, out)
        return f"/static/img/samples/{token}.svg", 84, 84
    out = out_dir / f"{token}.webp"
    im = Image.open(drawing)
    if im.mode != "RGB":
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        im = bg
    im.thumbnail((size, size), Image.LANCZOS)
    im.save(out, format="WEBP", quality=quality)
    return f"/static/img/samples/{token}.webp", im.width, im.height


def _load(locale: str) -> list[Sample]:
    samples: list[Sample] = []
    for sd in _SAMPLE_DEFS.get(locale, []):
        rjson = settings.BASE_DIR / sd["report_path"]
        if not rjson.exists():
            continue
        data = json.loads(rjson.read_text(encoding="utf-8"))
        dims = sorted(data["dimensions"], key=lambda d: -d["score"])
        first_name = data["child"]["name"].split()[0]
        # Lead the card with the portrait (about_child); fall back to conclusion for old JSON.
        portrait = (data.get("about_child") or data.get("conclusion") or "").strip()
        quote = _first_sentence(portrait)
        thumb_url, tw, th = _thumb(settings.BASE_DIR / sd["drawing"], sd["token"])
        samples.append(Sample(
            token=sd["token"], locale=locale,
            name=first_name, age_display=data["child"]["age_display"],
            caption=sd["caption"], thumb_url=thumb_url, thumb_w=tw, thumb_h=th,
            top_scores=[{"title": d["title"], "score": d["score"]} for d in dims[:3]],
            badge=f"{dims[0]['title'].lower()} {dims[0]['score']}/10",
            quote=quote, report_path=rjson,
            hero=sd["hero"], n_drawings=sd["n_drawings"],
        ))
    return samples


_cache: dict[str, list[Sample]] = {}


def get_samples(locale: str = settings.DEFAULT_LOCALE) -> list[Sample]:
    if locale not in _cache:
        _cache[locale] = _load(locale)
    return _cache[locale]


def get_sample_by_token(token: str, locale: str = settings.DEFAULT_LOCALE) -> Sample | None:
    return next((s for s in get_samples(locale) if s.token == token), None)
