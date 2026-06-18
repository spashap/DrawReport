"""Generate PLACEHOLDER brand assets so the site renders fully before the owner
supplies real images. Produces logo (strip + icon), hero (desktop + mobile),
favicons, and the OG image — all in the "Golden Hour" palette using project fonts.

Run: venv\\Scripts\\python.exe scripts\\make_placeholder_assets.py

Owner: replace data/Images/{stripLogo.png,logo.png,Hero.png} with real art and
re-run build_logos.py / build_hero_image.py to overwrite these placeholders.
ASCII-only console output (Windows cp1252 — UseCase #8).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "static" / "fonts"
IMG = ROOT / "static" / "img"
FAV = IMG / "favico"

BG = (252, 239, 223, 255)     # --bg warm paper
INK = (58, 42, 28, 255)       # --ink espresso
DENIM = (62, 78, 120, 255)    # --accent denim
AMBER = (185, 114, 42, 255)   # --accent2 amber
PAPER = (255, 252, 244, 255)  # --paper
MUTED = (110, 89, 66, 255)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def rounded(size, radius, fill):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=fill)
    return im


def text_size(d, text, fnt):
    b = d.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0], b[3] - b[1], b[0], b[1]


def make_wordmark():
    """logo-strip: 'Draw' (ink) + 'Report' (amber) wordmark on transparent bg."""
    h = 84
    f = font("rubik-900.ttf", 56)
    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    w1, th, ox1, oy1 = text_size(d, "Draw", f)
    w2, _, ox2, _ = text_size(d, "Report", f)
    pad = 6
    W = w1 + w2 + pad * 2
    im = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = (h - th) / 2 - oy1
    d.text((pad - ox1, y), "Draw", font=f, fill=INK)
    d.text((pad - ox1 + w1, y), "Report", font=f, fill=AMBER)
    im.save(IMG / "logo-strip.png", "PNG", optimize=True)
    im.save(IMG / "logo-strip.webp", "WEBP", quality=92, method=6)
    return im


def make_icon():
    """logo-icon: rounded denim square with 'DR' in paper."""
    s = 96
    im = rounded(s, 22, DENIM)
    d = ImageDraw.Draw(im)
    f = font("rubik-900.ttf", 46)
    tw, th, ox, oy = text_size(d, "DR", f)
    d.text(((s - tw) / 2 - ox, (s - th) / 2 - oy), "DR", font=f, fill=PAPER)
    im.save(IMG / "logo-icon.png", "PNG", optimize=True)
    im.save(IMG / "logo-icon.webp", "WEBP", quality=92, method=6)
    return im


def make_hero():
    """Warm vertical-gradient hero placeholder with a faint note."""
    for w, name in ((1600, "hero"), (960, "hero-800")):
        h = round(w * 9 / 16)
        base = Image.new("RGB", (w, h))
        top = (252, 239, 223)
        bot = (231, 169, 60)      # --amber-soft, warmer toward the bottom
        for y in range(h):
            t = y / h
            row = tuple(round(top[i] + (bot[i] - top[i]) * t * 0.55) for i in range(3))
            ImageDraw.Draw(base).line([(0, y), (w, y)], fill=row)
        d = ImageDraw.Draw(base)
        f = font("caveat-700.ttf", round(w / 22))
        msg = "hero image placeholder"
        tw, th, ox, oy = text_size(d, msg, f)
        d.text(((w - tw) / 2 - ox, (h - th) / 2 - oy), msg, font=f, fill=(110, 89, 66))
        base.save(IMG / (name + ".jpg"), "JPEG", quality=76, optimize=True, progressive=True)
        base.save(IMG / (name + ".webp"), "WEBP", quality=70, method=6)


def make_favicons(icon):
    FAV.mkdir(parents=True, exist_ok=True)
    icon.resize((96, 96), Image.LANCZOS).save(FAV / "favicon-96x96.png", "PNG", optimize=True)
    icon.resize((180, 180), Image.LANCZOS).save(FAV / "apple-touch-icon.png", "PNG", optimize=True)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">'
           '<rect width="96" height="96" rx="22" fill="#3E4E78"/>'
           '<text x="48" y="62" font-family="Arial,Helvetica,sans-serif" font-weight="900" '
           'font-size="42" fill="#FFFCF4" text-anchor="middle">DR</text></svg>')
    (FAV / "favicon.svg").write_text(svg, encoding="utf-8")


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    make_wordmark()
    icon = make_icon()
    make_hero()
    make_favicons(icon)
    print("OK placeholder assets -> %s" % IMG)
    print("   logo-strip, logo-icon, hero(+800), favico/* (replace with real art + rebuild)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
