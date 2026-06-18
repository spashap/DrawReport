# DrawReport — Development Plan

Build by cloning `C:\projects\GolosRisunka` (read-only) and adapting for US/English with an i18n layer.
Commit at the end of each phase (bump version), and **pause for owner review at each 🧪 milestone**.
See `CLAUDE.md`, `i18n-architecture.md`, `build-from-golos.md`, `positioning-en.md`.

---

## Phase 0 — Skeleton + i18n scaffolding
- New Flask project layout mirroring Golos: `app/`, `pipeline/`, `templates/`, `static/{css,fonts,img}`,
  `config/`, `data/`, `scripts/`, `content/en/blog/`, `translations/`.
- `venv` + `requirements.txt` (flask, jinja2, weasyprint, google-genai, pillow, pillow-heif,
  python-dotenv, pydantic, **flask-babel, babel**, requests).
- `config/settings.py` reads `.env`; holds product codes, ADMIN, locale config (`LOCALES=["en"]`,
  `DEFAULT_LOCALE="en"`).
- **i18n layer:** Flask-Babel init, locale resolver (URL prefix → cookie → Accept-Language → `en`),
  `url_for` locale injection, `babel.cfg`, empty `en` catalog. (See `i18n-architecture.md`.)
- Copy self-hosted fonts from Golos `static/fonts/` (Rubik/Inter/Caveat subsets) + `fonts.css`. Ensure
  `$` glyph present.
- **🧪 M0:** `python scripts/hello_pdf.py` (port Golos's) renders a one-page PDF with the three fonts and
  `$` — proves WeasyPrint + fonts work on this machine.

## Phase 1 — Design system (copy verbatim)
- Copy `static/css/tokens.css`, `static/css/components.css`, `projectSpec/brand-book.md` from Golos
  **verbatim** (palette «Golden Hour», 7-step scale, components, hero, carousels, reveal).
- Only changes: the logo (English wordmark — owner provides `data/Images/` sources; port
  `scripts/build_logos.py`) and removing any RU-only copy. Keep `--bg` matched to the logo background.
- `templates/_base.html`, `_header.html`, `_metrika.html`(optional analytics later), footer — ported,
  **all strings via i18n**.
- **🧪 M1:** component gallery renders; palette/scale identical to Golos; English logo in header.

## Phase 2 — Report template + pipeline (the core IP)
- Copy `pipeline/` (`prompt.py`, `gemini.py`, `lint.py`, `schema.py`, `images.py`, `render.py`) and
  `templates/report.html` + `static/css/report.css` from Golos.
- Adapt: **English prompt** (faithful adaptation of §7.4 philosophy + 7-direction taxonomy in English,
  per-locale structure per `i18n-architecture.md`), **English linter** banned-phrasings + repair text,
  report fixed strings + `$` + Babel dates.
- `scripts/generate_report.py` CLI end-to-end (images + context → Gemini → validated JSON → HTML → PDF).
- Sample reports: reuse Golos sample inputs, **American names**, English output.
- **🧪 M2 (gate):** generate reports for several test drawings (toddler / ~6 / ~8yr + a 2-drawing set) and
  a garbage input (blank/blurry → `insufficient_input`, not an invented report). **Owner signs off on
  report quality and tone** — this gates everything downstream. Best outputs become landing samples.

## Phase 3 — Landing page
- Port Golos `templates/landing.html` structure (cinematic hero + frosted card, sections, infinite
  carousels, reveal, CTA popup). All copy via i18n; English **DRAFT** copy adapted from
  `positioning-en.md` (mark for owner review).
- Hosted sample report routes `/<locale>/sample/<token>` (port Golos `/primer/`).
- SEO: titles/descriptions/OG/Twitter/canonical + **hreflang**, Schema.org (Org/WebSite/Product/FAQ/
  Article), `robots.txt`, per-locale `sitemap.xml`.
- **🧪 M3:** landing renders in English at `/en/`, samples clickable, Lighthouse mobile ≥ 90, first
  screen lean (port Golos perf practices; hero image optimized via `build_hero_image.py`).

## Phase 4 — Order flow + DB + payment stub
- SQLite schema (customers, children, orders, drawings, reports, sessions, login_codes, coupons, events)
  + init/migration — port Golos.
- Order form (config-driven fields; child name/gender/birth month-year; per-drawing upload + story +
  "when drawn"; upload validation, HEIC convert, size limit). All UI via i18n.
- **Payment abstraction with a stub provider** (created → paid via simulated capture). Success page +
  session cookie. (Real PayPal in Phase 8.)
- **🧪 M4:** full order → stub-pay → order saved; worker (next phase) can pick it up.

## Phase 5 — Worker + delivery + auth + cabinet
- `worker.py` poller (paid → generating → delivered/insufficient/failed); `app/jobs.py`; age computed at
  drawing date; `scripts/regenerate_report.py`.
- `app/mailer.py` with backends: `outbox` (HTML files in `data/outbox/`, dev) + **`resend`** (prod).
  Localized email templates.
- Auth: email 6-digit code (TTL, rate limit), `/login` → `/cabinet` (statuses, drawing thumbnails, PDF
  download, ownership checks). All via i18n.
- **🧪 M5:** place order with stub-pay → worker delivers → email (outbox) → cabinet shows report + PDF.

## Phase 6 — Admin + analytics (optional for launch; port if time)
- `/admin` (separate password) sidebar: orders, clients, coupons, products.json editor, emails/outbox,
  analytics (visits/actions). Port from Golos; admin can be English-only (not localized).

## Phase 7 — Content: blog + legal
- Port a few Golos blog articles, **adapted to English** (philosophy §7.4, no esoterica), under
  `content/en/blog/`, with per-article inline SVG thumb. DRAFT for owner review.
- **US legal:** privacy (children's data / COPPA), terms, refund — English, owner to review with counsel.

## Phase 8 — PayPal (live payment)
- Implement **PayPal Business** provider behind the payment abstraction (Orders API: create → approve →
  capture; webhook verification). Owner provides `PAYPAL_CLIENT_ID/SECRET` (live + sandbox).
- Test in **sandbox** end-to-end (order → PayPal → capture → worker delivers).
- **🧪 M8:** real sandbox purchase produces a delivered report + receipt email.

## Phase 9 — Deploy to Hetzner (parallel to cosmyday-api)
- `/var/www/drawreport`, gunicorn bind 127.0.0.1:**8002**, systemd `drawreport-web` + `drawreport-worker`,
  nginx vhost for `drawreport.com` (+www), **Let's Encrypt** (certbot nginx, drawreport.com only),
  SQLite in `data/`. **Do not touch cosmyday-api (port 8001) units/vhost/cert/venv.**
- `apt` WeasyPrint deps (Pango/Cairo/GDK-Pixbuf). Own venv.
- `deploy.sh` (git pull + deps + restart drawreport units) + `restart.sh` in repo root, scoped to
  drawreport. DNS for drawreport.com → 5.78.181.152 (DNS-only).
- **🧪 M9:** drawreport.com live over HTTPS; cosmyday-api unaffected; a sandbox order delivers end-to-end.

---

### Notes
- Keep `DevelopmentStatus.md` (append-only journal) and `UseCasesData.md` updated as you go.
- Don't reinvent: when unsure, open the Golos equivalent and mirror it.
- Secrets only in `.env` (never committed); build with stubs so phases run before real creds arrive.
