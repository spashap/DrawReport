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

## Phase 1 — Design system + base layout — DONE (V0.002)

- Copied verbatim: `tokens.css`, `components.css`, `report.css` (+ fonts in P0).
- `_base.html` full layout (canonical, hreflang loop, OG/Twitter, JSON-LD, font preloads,
  analytics include, header/footer). `_header.html` (English nav via url_for, logo <picture>,
  `data-goal` attrs). `_seo_jsonld.html` (English, per-locale inLanguage).
- `_analytics.html` — **GA4** client snippet (loads only if GA_MEASUREMENT_ID set; never on /admin)
  + first-party goal + engaged-session beacons to `/t/e` (fed to admin dashboards later).
- Route stubs (order/login/cabinet/blog/sample/legal) + `stub.html` so url_for resolves everywhere.
- Scripts: `build_logos.py`, `build_hero_image.py`, `build_og_image.py` (English/Golden Hour),
  `make_placeholder_assets.py` (placeholder logo/hero/favicon/og), `render_gallery.py`, `bump_version.py`.
- Self-contained dev gallery (`templates/dev/components.html`, English/USD).
- **M1 verified:** gallery renders; all pages 200; header/logo/canonical/OG present; GA conditional;
  beacon present. Placeholder brand assets generated.

## Phase 2 — Report pipeline + template — DONE (V0.003)

- Copied + de-Russified: `pipeline/schema.py` (language-neutral), `pipeline/images.py`.
- `pipeline/prompt.py` — English prompt, **per-locale** `PROMPTS["en"]` (faithful adaptation of
  Golos V3.0 §7.4: tone 70/20/10, 6 anchors, mandatory personalization, bridges, forbidden
  phrasings, age-honest scoring, multi-drawing consolidation, insufficient handling, JSON format).
  Fixed 7-direction taxonomy (keys immutable, English titles). `system_prompt(locale)`,
  `build_user_prompt(contexts, common, locale)`, `repair_instruction(locale)`.
- `pipeline/lint.py` — English banned patterns + allowed contexts, **per-locale**;
  `find_violations(data, locale)`.
- `pipeline/gemini.py` — locale flows through (system/user/lint/repair). Optional
  GOOGLE_GEMINI_BASE_URL proxy. lint→repair loop intact.
- `pipeline/render.py` — Babel dates (`format_report_date`), per-locale `REPORT_STRINGS`,
  locale-aware `render_html/render_report_files`. Standalone renderer saves header-free HTML + PDF;
  the navigable hosted page is rendered by the Flask route (Phase 3/5) with the header.
- `templates/report.html` — localized via `s` strings dict (renders outside Flask).
- `pipeline/samples/sample_report.json` — English, American name (Emma R.), 7-direction taxonomy,
  tone-compliant (lint-clean). Drawing SVG copied.
- Scripts: `generate_report.py` (CLI, --locale), `render_sample.py`.
- **M2 partial verified (no API key yet):** sample renders -> 7-page PDF (52 KB), **zero fallback
  fonts** (all Rubik/Inter/Caveat subsets), `$` ok. Linter clean on sample, catches injected
  violations. Live Gemini generation pending GEMINI_API_KEY (owner). `regenerate_report.py` deferred
  to Phase 5 (depends on jobs/db).

## Phase 3 — Landing + samples + SEO — DONE (V0.004)

- `templates/landing.html` — full cinematic landing adapted to English DRAFT copy from
  positioning-en.md (hero hook "say in drawings what they can't put into words", trio
  strengths/nurture/support, "grounded in developmental stages", no-myths framed positively,
  how-it-works, reviews rotator, trust, pricing USD, FAQ, blog carousel). url_for routing,
  `data-goal` analytics attrs, inline critical CSS, GA4 include, hreflang. JS (carousels/rotator/
  reveal/cta-pop) kept.
- `app/content.py` — per-locale FAQ + TESTIMONIALS (English DRAFT, American names).
- `app/samples.py` — per-locale sample registry, SVG-safe thumbnails; built-in sample (Emma R.)
  ships so the landing always has an example before live generation.
- `routes.py` — landing route (products/samples/faq/testimonials/schema/inline-css), `/sample/<token>`
  (SEO wrapper, Article schema), `/r/<token>` (full hosted report via Flask render_template with
  header), root blueprint `bp_root` for `/robots.txt` + `/sitemap.xml` (per-locale URLs, blocks
  /admin /cabinet /r/ /order). `templates/sample.html` English.
- **M3 verified:** `/en/` 200 (81KB, hero hook + $29 CTA + sample card + FAQPage schema + inline
  css); `/en/sample/sample-emma` + `/en/r/sample-emma` render; robots blocks /admin; sitemap lists
  /en/ pages. GA4 absent without id, loads with id set. (Hero/logo are placeholder art until owner
  supplies real images; Lighthouse mobile check pending real deploy.)

## Phase 4 — Order flow + DB + payment stub — DONE (V0.005)

- `app/db.py` — full SQLite schema (customers/children/orders/drawings/reports/sessions/
  login_codes/coupons/events) + idempotent migrations. USD `price_cents`, generic `payment_id`,
  per-order `locale`. WAL + FK + busy_timeout.
- `app/track.py` (visitor cookie `dr_v`, first-touch UTM, device parse, `track_event`),
  `app/geoip.py` (graceful: None if no data/geoip.db).
- `app/mailer.py` — **Resend** backend (replaces Unisender) + outbox dev backend behind
  `send_email`; English `_email_base/payment_received/login_code/report_ready/insufficient`.
- `app/auth.py` — email 6-digit code, 30-day session (`dr_s`), `create_session`/`current_customer`.
- `config/form_fields.py` — English per-locale field config (gender f/m), `child_to_common` +
  `drawing_to_story` for the prompt.
- `app/orders.py` — config-driven validation (English errors, date sanity, coupon), saves files,
  writes order + drawings; captures order locale.
- `app/payments.py` — abstraction: `create_payment` (stub now; `PAYMENT_BACKEND=paypal` → Phase 8)
  + idempotent `mark_paid` (customer/child reuse, session, paid, payment_received email).
- Templates: `order.html` (field macro, dynamic drawing blocks, USD), `checkout_stub.html`,
  `order_success.html`. Routes: order GET/POST, stub checkout/confirm, success, `/t/e` beacon
  (root blueprint). `__init__` wires `init_db` + track hooks; funnel `track_event`s added.
- **M4 verified:** order form renders (ym selects, fields); POST creates order + saved drawing →
  redirect to stub checkout → confirm → status `paid`, customer+child created, `dr_s` session cookie
  set, success page, payment_received email in `data/outbox/`. price_cents 2900, locale en.

## Phase 5 — Worker + delivery + auth + cabinet — DONE (V0.006)

- `app/jobs.py` — `run_order`: paid → generating → delivered/insufficient/failed. Locale-aware
  (prompt/render/emails in order locale), age computed at drawing date (English plurals),
  `report.json`/`report.html`/`report.pdf` saved, reports row upsert (public_token preserved on
  regenerate), report_ready (PDF attached) / insufficient / failure(admin alert) emails.
- `worker.py` — poller (resets stale 'generating' → 'paid' on start), `--once` for tests/cron.
- Login routes (email → 6-digit code → verify → session), `_dev_code` (localhost owner cheat),
  logout. Cabinet (orders grouped by child, status pills, drawing thumbs, open report + download
  PDF, ownership checks), `/cabinet/drawing/<id>` thumb, `/cabinet/order/<id>/report.pdf`.
  `/r/<token>` extended to DB-backed order reports. `login.html`, `cabinet.html` (English, i18n).
- `scripts/regenerate_report.py`.
- **M5 verified:** login (dev code → verify → session → cabinet); cabinet empty + with order;
  simulated delivered order → cabinet shows ready pill + links, `/r/<token>` renders the report
  with site header, PDF download returns application/pdf (52 KB). worker `--once` exits cleanly.
  Live paid→delivered via Gemini pending GEMINI_API_KEY (owner); rendering/status/email/cabinet
  paths all verified by simulation.

## Phase 6 — Admin + analytics — DONE (V0.007)

- `app/admin.py` — password login (HMAC cookie `dr_a`, separate from customer login;
  empty ADMIN_PASS = 404). Sections: analytics (KPI/funnel/UTM sources/recent events, bots
  filtered, engaged vs all), visits (devices/sources/geo/visitor list), actions (event histogram
  + filter), orders (+ resend / regenerate), clients, coupons (create/toggle), settings
  (products.json editor in USD), emails (outbox list/view). USD revenue, GA4 status (not Yandex),
  Resend status. `geoip.geo_label/country_name`, `jobs.resend_report_email` added.
- Admin templates (`_base_admin` sidebar + 9 sections), English-only.
- **M6 verified:** guard redirects unauthed → /admin/login; wrong pass 401; login sets `dr_a`;
  all 8 sections render 200; coupon create works.

## Phase 7 — Content: blog + legal — DONE (V0.008)

- `app/blog.py` — per-locale markdown reader (`content/<locale>/blog/*.md`, frontmatter).
  3 English DRAFT articles (is-a-drawing-a-diagnosis / what-you-can-learn / only-draws-in-black).
- `blog_index.html` + `blog_post.html` (English, url_for, Article schema, hreflang). Landing blog
  carousel now populated.
- `app/legal.py` — US legal pages (privacy w/ **COPPA + children's data**, terms, refund),
  English DRAFT markdown, flagged for counsel. `legal.html`. Routes wired (blog/blog_post/legal
  replace the stubs).
- **M7 verified:** blog index (3 cards), blog post (Article schema), missing post 404; legal
  privacy/terms/refund render (privacy contains COPPA), bad page 404; landing shows blog section.

## Phase 8 — PayPal provider — DONE (V0.009)

- `app/paypal.py` — Orders API v2: OAuth token, `create_paypal_order` (creates order, stores
  `payment_id`, returns approval URL), `capture_order`, `verify_webhook` (signature via PayPal).
- `payments.create_payment` routes to PayPal when `PAYMENT_BACKEND=paypal` (stub otherwise).
- Routes: `/pay/paypal/return` (capture → mark_paid → success + session), `/pay/paypal/cancel`,
  `/pay/paypal/webhook` (root blueprint; verify + mark_paid on PAYMENT.CAPTURE.COMPLETED;
  idempotent with the return capture).
- **M8 (code-complete) verified:** app boots with PayPal wired; return/cancel/webhook routes
  exist; stub flow still default; PayPal create fails gracefully without creds. Live sandbox
  end-to-end pending owner's PAYPAL_CLIENT_ID/SECRET (set PAYMENT_BACKEND=paypal, PAYPAL_ENV=sandbox).

### Pending
Phase 9 (deploy artifacts: systemd/nginx/deploy.sh, runbook).
