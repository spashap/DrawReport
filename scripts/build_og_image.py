"""Generate the default OpenGraph/social image (1200x630) -> static/img/og-default.png.

Brand-consistent: warm paper bg ("Golden Hour"), espresso title in Rubik, denim accent,
educational tagline. Uses the project's self-hosted fonts. Re-run after brand/copy changes.
ASCII-only console output (Windows cp1252 rule #8).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "static" / "fonts"
OUT = ROOT / "static" / "img" / "og-default.png"

W, H = 1200, 630
BG = (252, 239, 223)        # --bg warm paper
INK = (58, 42, 28)          # --ink espresso
ACCENT = (62, 78, 120)      # --accent denim
ACCENT2 = (185, 114, 42)    # --accent2 amber
MUTED = (110, 89, 66)       # --muted


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def center(draw, y, text, fnt, fill):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    w = bbox[2] - bbox[0]
    draw.text(((W - w) / 2, y), text, font=fnt, fill=fill)
    return bbox[3] - bbox[1]


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 12], fill=ACCENT)                       # top accent bar
    center(d, 92, "DrawReport", font("rubik-900.ttf", 64), ACCENT)
    center(d, 200, "What your child's drawing", font("rubik-900.ttf", 72), INK)
    center(d, 288, "says about them", font("rubik-900.ttf", 72), INK)
    d.rectangle([(W - 230) / 2, 392, (W + 230) / 2, 400], fill=ACCENT2)   # underline
    center(d, 430, "A personal PDF report on your child's development", font("inter-600.ttf", 36), INK)
    center(d, 490, "for parents - not a diagnosis - drawreport.com", font("inter-400.ttf", 30), MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print("OK wrote %s (%dx%d, %d bytes)" % (OUT, W, H, OUT.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
