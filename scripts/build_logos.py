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

# Favicons come from the SAME square source as the header icon. Building them here rather
# than by hand is the point: a logo change that updates the header but leaves a stale
# favicon is the most visible half-done rebrand there is, and it is exactly what happens
# when the two live in different tools.
FAVICON_DIR = OUT / "favico"
FAVICONS = [
    # (filename, size, background) - None background means keep transparency.
    ("favicon-96x96.png", 96, None),
    # iOS does NOT honour transparency on a touch icon: it composites the image onto
    # black, so a transparent icon arrives as line art on a black tile. Give it the paper
    # background explicitly (--paper in tokens.css).
    ("apple-touch-icon.png", 180, (0xFF, 0xFC, 0xF4)),
]


def kb(p: Path) -> float:
    return p.stat().st_size / 1024


def _find(names) -> "Path | None":
    for n in names:
        if (SRC / n).exists():
            return SRC / n
    return None


# How close a pixel must be to the corner colour to count as background, and how much
# breathing room to leave after trimming (as a fraction of the longest content edge).
_BG_TOLERANCE = 18
_PAD_RATIO = 0.06


def _dealpha_and_trim(im: "Image.Image") -> "Image.Image":
    """Turn a painted flat background transparent, then crop to the artwork.

    Two problems this solves, both invisible until the logo is on the page:

    1. A BAKED-IN BACKGROUND NEVER QUITE MATCHES. tokens.css sets the page background to
       the logo's colour on purpose ("so the header blends with the logo"), so a source
       exported at even a slightly different cream shows up as a faint square around the
       logo. It is also wrong in the dark theme, where a cream block glares.
    2. EXPORTED ARTWORK CARRIES HUGE MARGINS. This source is 60% empty, so a naive resize
       to 96px renders the actual drawing at about 58px and it reads as too small next to
       everything else in the header.

    Only runs when the source has no meaningful alpha; art that already has transparency
    is left alone.
    """
    rgba = im.convert("RGBA")
    if rgba.split()[-1].getextrema()[0] < 255:
        return rgba                      # already transparent - trust the artwork

    from PIL import ImageChops
    bg = rgba.convert("RGB").getpixel((0, 0))
    flat = Image.new("RGB", rgba.size, bg)
    diff = ImageChops.difference(rgba.convert("RGB"), flat).convert("L")
    mask = diff.point(lambda p: 255 if p > _BG_TOLERANCE else 0)

    box = mask.getbbox()
    if box is None:                      # a single flat colour - nothing to trim
        return rgba

    # Feather the edge: a hard threshold leaves the anti-aliased outline of the artwork
    # ringed with the old background colour, which shows as a pale halo once the logo
    # sits on a different background.
    alpha = diff.point(lambda p: min(255, int(p * 255 / max(1, _BG_TOLERANCE * 2))))
    rgba.putalpha(alpha)

    pad = int(max(box[2] - box[0], box[3] - box[1]) * _PAD_RATIO)
    box = (max(0, box[0] - pad), max(0, box[1] - pad),
           min(rgba.width, box[2] + pad), min(rgba.height, box[3] + pad))
    return rgba.crop(box)


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
        im = Image.open(src)
        before = im.size
        im = _dealpha_and_trim(im)
        if im.size != before:
            print("       trimmed %dx%d -> %dx%d (background made transparent)"
                  % (*before, *im.size))
        if w is None:
            w = round(im.width * h / im.height)
        else:
            # A square target must not squash non-square artwork: fit it inside the box
            # and centre it, keeping the transparent margin rather than distorting a face.
            fitted = im.copy()
            fitted.thumbnail((w, h), Image.LANCZOS)
            canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            canvas.paste(fitted, ((w - fitted.width) // 2, (h - fitted.height) // 2))
            im = canvas
        if im.size != (w, h):
            im = im.resize((w, h), Image.LANCZOS)
        png = OUT / (name + ".png")
        webp = OUT / (name + ".webp")
        im.save(png, "PNG", optimize=True)
        im.save(webp, "WEBP", quality=90, method=6)
        print("  %-11s %3dx%-3d  png %5.1f KB   webp %5.1f KB" % (name, w, h, kb(png), kb(webp)))

    # --- favicons, from the same square source as the header icon ---
    icon_src = _find(JOBS[1][0])
    if icon_src is not None:
        FAVICON_DIR.mkdir(parents=True, exist_ok=True)
        art = _dealpha_and_trim(Image.open(icon_src))
        for fname, size, bg in FAVICONS:
            fitted = art.copy()
            fitted.thumbnail((size, size), Image.LANCZOS)
            canvas = Image.new("RGBA", (size, size), bg + (255,) if bg else (0, 0, 0, 0))
            canvas.paste(fitted, ((size - fitted.width) // 2,
                                  (size - fitted.height) // 2), fitted)
            out = FAVICON_DIR / fname
            canvas.save(out, "PNG", optimize=True)
            print("  %-11s %3dx%-3d  png %5.1f KB%s"
                  % (fname.replace(".png", ""), size, size, kb(out),
                     "" if bg else "   (transparent)"))
        # A stale placeholder favicon.svg would WIN over these: browsers prefer an SVG
        # icon when one is offered, so leaving it would keep showing the old mark however
        # many PNGs we rebuild. It is removed here and its <link> dropped from _base.html.
        stale_svg = FAVICON_DIR / "favicon.svg"
        if stale_svg.exists():
            stale_svg.unlink()
            print("  removed favicon.svg (a stale SVG icon overrides the PNGs)")
    print("done -> %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
