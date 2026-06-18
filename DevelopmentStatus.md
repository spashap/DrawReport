# DevelopmentStatus.md — DrawReport build journal

Append-only. How the next session resumes work. DrawReport = US/English hard fork of
Golos Risunka (`C:\projects\GolosRisunka`, read-only reference).

Owner directive: build the complete, fully functional core system end-to-end (all phases),
QA at the end. Placeholders/stubs for anything not yet provided (Gemini/PayPal/Resend keys,
GA id, logo, launch price). Analytics = first-party events + admin dashboards, with **GA4**
(not Yandex) as the client snippet. Auth = email 6-digit code (same as Golos).

---

## Phase 0 — Skeleton + i18n + fonts — DONE (V0.001)

- Project tree created: `app/ pipeline/ templates/ static/{css,fonts,img} config/ data/
  scripts/ content/en/blog/ translations/en/LC_MESSAGES/ projectSpec/`.
- `config/settings.py` — adapted from Golos: USD currency, GA4 id, PayPal + Resend env,
  `LOCALES`/`DEFAULT_LOCALE`, paths, products.json mtime cache. Secrets via `.env`.
- `config/products.json` — USD placeholder prices ($29 snapshot / $49 development, English copy).
- `requirements.txt` — Golos deps + `flask-babel`, `babel`, `requests`.
- i18n layer (`app/i18n.py` + `app/__init__.py`): Flask-Babel, locale resolver
  (URL prefix → cookie → Accept-Language → `en`), main blueprint under `url_prefix="/<lang_code>"`,
  `url_value_preprocessor` pops locale to `g.lang_code` (404 on inactive locale),
  `url_defaults` auto-injects locale into `url_for('main.*')`, `/` → 302 to resolved locale,
  locale cookie persistence, `alternate_urls()` for hreflang. `babel.cfg` + empty `en` catalog.
- Fonts copied verbatim from Golos (`static/fonts/*` 7 faces × woff2+ttf, `fonts.css`).
  Design CSS copied verbatim (`tokens.css`, `components.css`, `report.css`) — used by base template.
- `scripts/hello_pdf.py` — adapted (English text + `$` glyphs).
- Phase-0 templates (`_base.html`, `landing.html`, `error.html`) — minimal, boot + i18n proof;
  Phase 1 replaces base/landing with the full design-system layout.
- `.env.example`, `.env` (placeholders), `VERSION` (0.001), `.gitignore`, `run.py`.
- venv created (Python 3.13.1), deps installed (weasyprint 69, flask 3.1, flask-babel 4.0, …).

**M0 verified:** `python scripts/hello_pdf.py` → `data/hello.pdf` (36 KB). Embedded fonts:
Rubik-Heavy/Ultra-Bold, Inter/Medium/Semi-Bold, Caveat-Bold/Semi-Bold (all subsetted, `XXXXXX+`
prefix). **Zero fallback fonts** (no Segoe/Verdana/Arial/Times). `$` renders.

**App boot verified:** `/` → 302 `/en/`; `/en/` → 200 with hero + `lang="en"`; `/xx/` → 404
(inactive locale); `/en/nope` → 404; `Accept-Language: es` → `/en/` (es not active).

### Pending
Phases 1–9 (design system, pipeline, landing, orders, worker/delivery/auth, admin, content/legal,
PayPal, deploy artifacts). See plan + task list.
