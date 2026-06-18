"""Create an order: config-driven form validation, save files, write the DB rows."""
from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

from flask_babel import gettext as _
from werkzeug.datastructures import FileStorage

from app.db import get_db, now
from config import settings
from config.form_fields import child_fields, drawing_fields

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class FormError(Exception):
    """Validation errors: {field: message} for re-rendering the form."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("form validation failed")
        self.errors = errors


def _validate_block(fields: list[dict], data: dict, prefix: str,
                    errors: dict[str, str]) -> dict:
    out = {}
    for f in fields:
        name = f"{prefix}{f['key']}"
        if f["type"] == "ym":
            m = (data.get(f"{name}_m") or "").strip()
            y = (data.get(f"{name}_y") or "").strip()
            val = f"{y}-{m}" if (m and y) else ""
            if f["required"] and not val:
                errors[name] = _("Choose a month and year")
            elif val and not MONTH_RE.match(val):
                errors[name] = _("Choose a month and year from the list")
        else:
            val = (data.get(name) or "").strip()
            if f["required"] and not val:
                errors[name] = _("Required field")
        out[f["key"]] = val
    return out


def validate_and_create_order(form: dict, files: list[FileStorage],
                              visitor_id: str | None, utm: dict | None,
                              locale: str = settings.DEFAULT_LOCALE) -> int:
    """Full server-side validation -> order in the DB + files on disk.
    Returns order_id. Raises FormError."""
    errors: dict[str, str] = {}

    email = (form.get("email") or "").strip().lower()
    if not EMAIL_RE.match(email):
        errors["email"] = _("Enter a valid email")

    child = _validate_block(child_fields(locale), form, "child_", errors)

    products = settings.get_products()
    product_code = form.get("product", "snapshot")
    if product_code not in products or not products[product_code]["enabled"]:
        product_code = "snapshot"
    product = products[product_code]

    drawings: list[dict] = []
    if not files:
        errors["drawings"] = _("Upload at least one drawing")
    if len(files) > product["drawings_max"]:
        errors["drawings"] = _("No more than %(n)s drawings", n=product["drawings_max"])
    for i, fs in enumerate(files, start=1):
        name = (fs.filename or "").lower()
        ext = Path(name).suffix
        if ext not in ALLOWED_EXT:
            errors[f"d{i}_file"] = _("Format: JPG, PNG, HEIC, or WebP")
            continue
        blob = fs.read()
        fs.seek(0)
        if len(blob) > settings.UPLOAD_MAX_BYTES:
            errors[f"d{i}_file"] = _("File is larger than 15 MB")
        if len(blob) < 100:
            errors[f"d{i}_file"] = _("File is corrupt or empty")
        ctx = _validate_block(drawing_fields(locale), form, f"d{i}_", errors)
        drawings.append({"ext": ext, "file": fs, "context": ctx})

    # date sanity: not before birth, not in the future
    this_month = datetime.date.today().strftime("%Y-%m")
    birth = child.get("birth_ym", "")
    if birth and birth > this_month:
        errors["child_birth_ym"] = _("Birth date is in the future?")
    for i, d in enumerate(drawings, start=1):
        da = d["context"].get("drawn_at", "")
        if da:
            if da > this_month:
                errors[f"d{i}_drawn_at"] = _("The drawing date is in the future")
            elif birth and da < birth:
                errors[f"d{i}_drawn_at"] = _("Drawing predates the child's birth - check the dates")

    db = get_db()
    price_cents = product["price_usd"] * 100
    coupon_code = (form.get("coupon") or "").strip().upper() or None
    if coupon_code:
        c = db.execute("SELECT * FROM coupons WHERE upper(code) = ?", (coupon_code,)).fetchone()
        if c is None or not c["active"] or (not c["multi_use"] and c["uses_count"] > 0):
            errors["coupon"] = _("Coupon not found or already used")
        else:
            price_cents = price_cents * (100 - c["percent_off"]) // 100

    if errors:
        raise FormError(errors)

    cur = db.execute(
        "INSERT INTO orders (email, product_code, price_cents, coupon_code, locale, status,"
        " child_json, visitor_id, utm_json, created_at)"
        " VALUES (?, ?, ?, ?, ?, 'created', ?, ?, ?, ?)",
        (email, product_code, price_cents, coupon_code, locale,
         json.dumps(child, ensure_ascii=False),
         visitor_id, json.dumps(utm, ensure_ascii=False) if utm else None, now()),
    )
    order_id = cur.lastrowid

    order_dir = settings.DRAWINGS_DIR / str(order_id)
    order_dir.mkdir(parents=True, exist_ok=True)
    for i, d in enumerate(drawings, start=1):
        path = order_dir / f"drawing_{i}{d['ext']}"
        d["file"].save(path)
        db.execute(
            "INSERT INTO drawings (order_id, file_path, drawn_at, context_json, uploaded_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (order_id, path.relative_to(settings.BASE_DIR).as_posix(),
             d["context"].get("drawn_at"),
             json.dumps(d["context"], ensure_ascii=False), now()),
        )
    db.commit()
    return order_id
