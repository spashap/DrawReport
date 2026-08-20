"""Build the Product structured-data images from data/Images/Hero.png.

Run when the hero source changes:
    venv\\Scripts\\python.exe scripts\\build_product_images.py

Produces (in static/img/, served at /static/img/):
    product-1x1.jpg    square   - the crop Google shows in most rich results
    product-4x3.jpg    4:3
    product-16x9.jpg   16:9

Why three: Google Search asks for the SAME product in 16:9, 4:3 and 1:1 so it can pick
the ratio the surface needs instead of cropping ours badly. `_schema_jsonld()` in
app/routes.py lists all three in Product.image - a MISSING image is the one CRITICAL
merchant-listing error, so if these files ever disappear the schema must be fixed too.

Crops are RIGHT-anchored: the drawings (the thing being sold a report about) sit on the
right of the hero, the mother-and-child on the left. A centre crop cuts the drawings in
half. ASCII-only console output (Windows cp1252 - UseCase #8).
"""
from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    sys.stderr.write("Pillow not installed in this venv. Run: pip install pillow\n")
    sys.exit(1)

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "data" / "Images" / "Hero.png"
OUT = BASE / "static" / "img"

# (name, aspect w, aspect h, jpg quality)
VARIANTS = [
    ("product-1x1", 1, 1, 82),
    ("product-4x3", 4, 3, 82),
    ("product-16x9", 16, 9, 80),
]


def kb(p: Path) -> int:
    return p.stat().st_size // 1024


def main() -> int:
    if not SRC.exists():
        sys.stderr.write("Source not found: %s\n" % SRC)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC).convert("RGB")
    print("source:", src.size[0], "x", src.size[1])
    for name, aw, ah, q in VARIANTS:
        want = aw / ah
        have = src.width / src.height
        if have > want:                      # source too wide -> trim the left
            w = round(src.height * want)
            box = (src.width - w, 0, src.width, src.height)
        else:                                # source too tall -> trim the bottom
            h = round(src.width / want)
            box = (0, 0, src.width, h)
        im = src.crop(box)
        p = OUT / (name + ".jpg")
        im.save(p, "JPEG", quality=q, optimize=True, progressive=True)
        print("  %-13s %4dx%-4d  jpg %3d KB" % (name, im.width, im.height, kb(p)))
    print("done -> %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
