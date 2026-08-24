"""Blog: articles are markdown files under content/<locale>/blog/<slug>.md with
frontmatter between '---':
  title: ...
  description: ...
  date: 2026-06-20
  updated: 2026-08-24        (optional; defaults to `date`)
  faq:                       (optional; drives BOTH the visible FAQ block and
    - q: A question?           the FAQPage JSON-LD, so the two cannot drift -
      a: Its answer.           Google penalises schema that is not on the page)
    - q: Another?
      a: Another answer.
Add an article = drop a file. No admin. Per-locale (Golos kept content/blog/).

The frontmatter parser is hand-rolled rather than PyYAML on purpose: it is the
only YAML in the project, the shape above is the whole grammar, and a new
runtime dependency has to be installed on the server before the next deploy can
boot. Values may wrap onto indented continuation lines.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path

import markdown as md

from config import settings


def _blog_dir(locale: str) -> Path:
    return settings.BASE_DIR / "content" / locale / "blog"


@dataclass
class Post:
    slug: str
    title: str
    description: str
    date: datetime.date
    html: str
    updated: datetime.date | None = None
    faq: list[dict[str, str]] = field(default_factory=list)

    @property
    def modified(self) -> datetime.date:
        return self.updated or self.date


def _parse_frontmatter(fm: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Scalar keys plus the one list-valued key we support ('faq')."""
    meta: dict[str, str] = {}
    faq: list[dict[str, str]] = []
    in_faq = False
    cur: str | None = None          # which field a continuation line extends
    for raw in fm.strip().splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        indented = line[:1].isspace()
        stripped = line.strip()

        if not indented:
            # A top-level key ends any list block.
            in_faq = False
            cur = None
            if ":" not in stripped:
                continue
            k, v = stripped.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "faq" and not v:
                in_faq = True
                continue
            meta[k] = v
            cur = k
            continue

        if in_faq:
            if stripped.startswith("- q:"):
                faq.append({"q": stripped[4:].strip(), "a": ""})
                cur = "q"
            elif stripped.startswith("a:") and faq:
                faq[-1]["a"] = stripped[2:].strip()
                cur = "a"
            elif faq and cur in ("q", "a"):
                faq[-1][cur] = (faq[-1][cur] + " " + stripped).strip()
        elif cur:
            meta[cur] = (meta[cur] + " " + stripped).strip()
    return meta, faq


def _date(value: str, fallback: datetime.date) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return fallback


def _parse(path: Path) -> Post | None:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    faq: list[dict[str, str]] = []
    body = text
    if text.startswith("---"):
        try:
            _, fm, body = text.split("---", 2)
            meta, faq = _parse_frontmatter(fm)
        except ValueError:
            pass
    mtime = datetime.date.fromtimestamp(path.stat().st_mtime)
    date = _date(meta.get("date", ""), mtime)
    updated = _date(meta.get("updated", ""), date)
    return Post(slug=path.stem, title=meta.get("title", path.stem),
                description=meta.get("description", ""), date=date,
                html=md.markdown(body, extensions=["extra"]),
                updated=updated, faq=[f for f in faq if f["q"] and f["a"]])


def get_posts(locale: str = settings.DEFAULT_LOCALE) -> list[Post]:
    d = _blog_dir(locale)
    if not d.exists():
        return []
    posts = [p for f in sorted(d.glob("*.md")) if (p := _parse(f))]
    return sorted(posts, key=lambda p: p.date, reverse=True)


def get_post(slug: str, locale: str = settings.DEFAULT_LOCALE) -> Post | None:
    f = _blog_dir(locale) / f"{slug}.md"
    return _parse(f) if f.exists() else None


def related(slug: str, locale: str = settings.DEFAULT_LOCALE,
            limit: int = 3) -> list[Post]:
    """Everything else, newest first. With a handful of articles that is a
    better 'related' list than any keyword-overlap scoring would be, and it
    never returns an empty block."""
    return [p for p in get_posts(locale) if p.slug != slug][:limit]
