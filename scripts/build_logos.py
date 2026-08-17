"""Build web-optimized navigation logos from data/Images/.

Run once after pulling / when a logo source changes:
    venv\\Scripts\\python.exe scripts\\build_logos.py

Sources (not web-served, gitignored data/). Either name is accepted for each:
    data/Images/logo-strip.png  (or stripLogo.png)  wide wordmark -> header on desktop
    data/Images/logo-icon.png   (or logo.png)       square icon   -> header on mobile

Produces (in static/img/, served at /static/img/):
    logo-strip.webp / logo-strip.png   ~84px tall (2x of 42px display)
    logo-icon.webp  / logo-icon.png    96x96 (2x of ~42-48px display)

Header (_header.html) uses <picture>: webp with png fallback, icon below 560px.
ASCII-only console output (Windows cp1252 — UseCase #8).
"""
from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    sys.stderr.write("Pillow not installed in this venv. Run: pip install pillow\n")
    sys.exit(1)

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "data" / "Images"
OUT = BASE / "static" / "img"

# (accepted source names, out_basename, target_height_px, target_width_px_or_None)
#
# Several accepted names per job on purpose. The script used to demand "stripLogo.png"
# while WRITING "logo-strip.png", so the natural thing to call the source file was the
# one name it rejected - and that is exactly the mistake that got made. The output name
# is listed FIRST because it is the one a person guesses.
JOBS = [
    (("logo-strip.png", "stripLogo.png"), "logo-strip", 84, None),  # keep aspect by height
    (("logo-icon.png", "logo.png"), "logo-icon", 96, 96),           # square
]


def kb(p: Path) -> float:
    return p.stat().st_size / 1024


def _find(names) -> "Path | None":
    for n in names:
        if (SRC / n).exists():
            return SRC / n
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # Build whatever IS present rather than refusing everything. The two logos have
    # independent lifecycles - replacing the wordmark should not require re-supplying the
    # square icon - and an all-or-nothing check meant a valid new wordmark could not be
    # built at all because an unrelated file was absent.
    found = [(names, name, h, w) for names, name, h, w in JOBS if _find(names)]
    absent = [(names, name) for names, name, *_ in JOBS if not _find(names)]
    if not found:
        sys.stderr.write("No logo sources found in %s. Expected any of:\n" % SRC)
        for names, name, *_ in JOBS:
            sys.stderr.write("  %-11s <- %s\n" % (name, ", ".join(names)))
        sys.stderr.write("Owner: drop the logo sources there, or run make_placeholder_assets.py.\n")
        return 1
    for names, name in absent:
        print("  SKIP  %-11s no source (%s) - keeping the existing asset"
              % (name, " / ".join(names)))
    for names, name, h, w in found:
        src = _find(names)
        # Say which file was actually used: with several accepted names, silence here
        # means a stale source can be rebuilt for weeks without anyone noticing.
        print("  using %s" % src.name)
        im = Image.open(src).convert("RGBA")
        if w is None:
            w = round(im.width * h / im.height)
        im = im.resize((w, h), Image.LANCZOS)
        png = OUT / (name + ".png")
        webp = OUT / (name + ".webp")
        im.save(png, "PNG", optimize=True)
        im.save(webp, "WEBP", quality=90, method=6)
        print("  %-11s %3dx%-3d  png %5.1f KB   webp %5.1f KB" % (name, w, h, kb(png), kb(webp)))
    print("done -> %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
