"""Image prep: jpg/png/heic/webp -> RGB JPEG, long side <= 2000px (Golos spec §6)."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

from config import settings

register_heif_opener()  # after this PIL opens .heic like any other file


def prepare_image(path: Path, max_side: int = settings.IMAGE_MAX_LONG_SIDE) -> bytes:
    """Return JPEG bytes, ready for both Gemini and the report's data URI."""
    im = Image.open(path)
    if im.mode != "RGB":
        # composite RGBA/P onto white, not black
        background = Image.new("RGB", im.size, (255, 255, 255))
        background.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        im = background
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()
