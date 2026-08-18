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

## Phase 9 — Deploy artifacts — DONE (V0.010)

- `deploy.sh` + `restart.sh` scoped to `drawreport-web`/`drawreport-worker`, `/var/www/drawreport`
  (compiles translations, chowns data, restarts only drawreport units). `release.bat` (bump +
  commit + push; no Vercel export).
- `scripts/deploy/`: `drawreport-web.service` (gunicorn 127.0.0.1:8002), `drawreport-worker.service`,
  `nginx-drawreport.conf` (drawreport.com vhost, 50M uploads, X-Real-IP), `provision.sh` (apt
  WeasyPrint deps + venv + units + nginx + certbot guidance). `DEPLOY.md` runbook (cosmyday-safe,
  port 8002, DNS, certbot, PayPal webhook, GeoIP/logo notes, adding a locale).
- **M9 (artifacts) verified:** full route smoke test all OK (`/` redirect, landing, order, login,
  blog, legal, sample, hosted report, cabinet redirect, admin login, robots, sitemap). **i18n
  acceptance PASSED** with `LOCALES=en,es`: routing/hreflang/fallback-content/sitemap/Babel dates
  all switch with no code edits. Actual server provisioning is owner-run (needs DNS + SSH).

---

## Phase 10 — Switch LLM to Anthropic (Claude) — DONE (V0.011)

- Provider abstraction matching the owner's US-project convention: `LLM_PROVIDER`
  (anthropic|gemini), `LLM_MODEL` (claude-sonnet-4-6), `LLM_FALLBACK_MODEL`
  (claude-haiku-4-5-20251001), `ANTHROPIC_API_KEY`. (Gemini kept as alternate provider.)
- `pipeline/anthropic_llm.py` (Claude provider: image blocks + system/user, refusal handling,
  no sampling params so it's model-agnostic), `pipeline/gemini.py` slimmed to a provider module,
  `pipeline/llm.py` = provider-agnostic orchestrator (attempts, JSON validate, lint+repair,
  primary→fallback model). `jobs.py`/`generate_report.py` import from `pipeline.llm`.
- `anthropic` added to requirements; `.env.example` updated.
- **M2 report quality verified LIVE (Claude Sonnet 4.6):** generated a full report from a test
  drawing in 1 attempt, 0 repairs, **0 lint hits**; 7 directions, age-honest scoring (creativity 5
  = typical for 6, not inflated), warm + grounded in visible details (used the context cue), all
  activities in "you could offer" form, English. 8-page PDF, **zero fallback fonts**. The
  insufficient-input and fallback-model paths are wired (not separately exercised).

## STATUS: all phases complete + Anthropic LLM live. Build is feature-complete for owner QA.

### What needs the owner before launch (all behind stubs/placeholders now)
- `.env` secrets: `GEMINI_API_KEY` (enables live report generation), `RESEND_API_KEY` +
  `MAIL_BACKEND=resend`, `PAYPAL_CLIENT_ID/SECRET/WEBHOOK_ID` + `PAYMENT_BACKEND=paypal`,
  `ADMIN_PASS`, `GA_MEASUREMENT_ID`, `PUBLIC_BASE_URL=https://drawreport.com`.
- Real logo/hero art into `data/Images/` → run `build_logos.py` / `build_hero_image.py`
  (placeholders ship now).
- Launch price in `config/products.json` (or the admin Settings editor).
- DNS for drawreport.com → 5.78.181.152 + run `provision.sh` then `certbot`.
- Review the DRAFT copy (landing, blog, legal) and have legal reviewed by counsel.
- Live report quality (M2 owner sign-off): GEMINI no longer used — LLM is Anthropic now;
  run `scripts/generate_report.py <imgs> --context ... --locale en` (key already in `.env`).

## Session close — 2026-06-19 (V0.015, all pushed to origin/main)

Post-build work completed this session (after M0–M9):
- **LLM switched to Anthropic/Claude** behind `pipeline/llm.py` (Sonnet 4.6 primary, Haiku 4.5
  fallback); verified live. See UseCase #11.
- **Real hero + logo flow:** owner's hero built into `static/img/hero*.{jpg,webp}`; OG image is now a
  JPG cropped from the hero; per-post blog SVG thumbnails in `_blog_thumb.html`. UseCases #13–#14.
- **Carousel made finite** (dots = real card count). UseCase #12.
- **Local dev on port 3000** (`run.py` reads `PORT`, default 3000); web + worker run locally.
- **Deployment kit `drawreportDeploy/`** for server `/var/www/DrawReport` (capital) + port 8002,
  cosmyday-safe; `provision.sh`/`deploy.sh`/`restart.sh` + units + nginx + README. `DEPLOY.md` updated.
  `.gitattributes` forces LF. UseCase #15.
- **DNS decision:** owner sets A records at the registrar (no Cloudflare). TLS via certbot.
- CLAUDE.md given an AS-BUILT STATUS section.

**To resume:** read CLAUDE.md (AS-BUILT section) + this file + UseCasesData.md. Run locally with
`run.py`/`worker.py`. To deploy, follow `drawreportDeploy/README.md`.

## Session — 2026-06-24 (V0.017) — Philosophy 2.3 pivot finished (TASK T1–T5)

Engine (prompt `en-4.0` / lint frame-check / schema v4.0 / render sections) was already pivoted by the
prior session; this session completed everything around it per `projectSpec/TASK-apply-philosophy-2.3.md`.

- **T1 — admin-controlled end-of-report texts** (mirror Golos). New `config/report_texts.json`
  (upsell by drawing count + `disclaimer_main` + per-count add-on + `free_text`);
  `settings.get_report_texts()` (mtime cache, safe defaults); `render_html`/`render_report_files`
  gained `upsell_text`/`disclaimer_text`/`free_text`; `templates/report.html` renders the gated
  suffix blocks (`.r-upsell` / `.r-admin-note`) before the footer; `app/jobs.py` picks the
  upsell/disclaimer by `min(n_drawings,3)`; admin editor `/admin/report-texts` (+ `…/save`, sidebar
  nav, `templates/admin/report_texts.html`). Verified: save → 302 → next render shows it, no restart.
- **T2 — landing rework to the pivot** (`templates/landing.html`, `app/content.py`, `app/routes.py`,
  `app/samples.py`). "What you'll learn" now personality-led (skills last); "How the conclusion is
  built" is a personality example (visible detail → gentle hypothesis → what to ask the child);
  "No myths" reframed to careful, literature-grounded reading by real methods (Piaget/Lowenfeld/
  Vygotsky) + a positive-identity disclaimer; **fabricated testimonials removed** and replaced with an
  **illustrative-scenarios** case-list (`get_scenarios`, `.case` CSS mirrored from Golos); sample cards
  now lead with the `about_child` portrait quote. Copy is DRAFT.
- **T3 — sample regenerated** with the live Anthropic pipeline (en-4.0, 1 attempt, 1 repair, 0 lint
  hits left). American name **Liam C.**, house-scene drawing; `pipeline/samples/sample_report.json` +
  `sample_drawing.png` (old `sample_drawing.svg` removed); `_SAMPLE_DEFS` token `sample-liam`. QA:
  safe frame on every zone-3 sentence, portrait `about_child`, varied scores (8/7/8/7/6/7/6).
- **T4 — operational guard:** `pipeline/anthropic_llm.py` now passes `timeout=180` on both
  `messages.create` calls (hung call → orchestrator retry/fallback, not a wedged worker).
- **T5 — verified:** full report PDF shows About-your-child + both recommendation sections +
  specialists + development directions + the admin suffix blocks; **only self-hosted fonts embedded
  (Caveat/Inter/Rubik), zero fallback**; linter = 0 false positives on the framed report, 3 hits on an
  injected bare diagnosis. Bumped VERSION 0.016 → 0.017.

**To resume:** all of T1–T5 complete + committed (not pushed). Owner go-live steps unchanged
(see CLAUDE.md AS-BUILT). New admin screen: `/admin/report-texts`.

---

## 2026-08-17 — Copy edit: native US English on `/en/` and `/en/report` (V0.032)
Owner verdict on the first English conversion: "epic fail". A separate review produced
`projectSpec/drawreportcopyfixtask.md` (283 lines, copy-only). Executed in full and deployed.

- **Global.** All apostrophes/quotes curled, every ` - `-as-dash gone (checked on the RENDERED
  pages, not the sources). Footer version badge `V0.0xx` is now gated by `settings.SHOW_VERSION`,
  derived from `PUBLIC_BASE_URL` (localhost -> shown, production -> hidden; `SHOW_VERSION=1`
  forces it on). Both footers now carry the longer disclaimer "Educational observation, not
  medical **or psychological** diagnosis". `grounded in the developmental and art literature`
  -> `grounded in developmental and art-education research`.
- **`/en/` (home.html).** Britishism `to hand` -> `handy`; concern bullets made parallel (all
  start with a verb about the child) and `very schematic` -> `just outlines`; hero tricolon
  cut to one promise (it was a table of contents for the bullets a screen below); assorted
  idiom fixes. 419 -> 411 words.
- **`/en/report` (landing.html + `app/content.py` + `config/products.json`).** `in support:`,
  `and a hint` x3, `real methods`, `specially`, `within the hour` all gone; the "For example"
  block lost its five-times-repeated frame (heading is now "What this looks like in practice"
  and the scenarios are whole sentences); the prose sentence restating the three-panel diagram
  deleted; FAQ self-contradiction fixed (`judges` -> `reads`). Negation-contrast reduced from
  8 to 3 keepers, em dashes 29 -> 16, 1651 -> 1549 words.
- **Deliberate deviations from the task doc**, both forced by its own §2.8 budget (keep at most
  three "not/never a diagnosis"): §2.2's replacements for the "No myths" intro and closing note
  would have kept two more, so those two were rewritten positively instead. Flagged to the owner.
- **Also touched, on purpose:** `config/free_texts.py` CONCERNS labels (they ARE the home-page
  concern list) and the two MIRROR strings that paraphrase them - leaving the mirror quoting
  "very schematic" after the button stopped saying it would echo words the parent never saw.
  Blog front-matter title/description typography (those strings render in the landing carousel);
  blog BODIES untouched.
- **Verified on the live site**, not just locally: 0 straight quotes, 0 spaced-hyphen dashes,
  0 of the 11 banned phrases, no version badge, long disclaimer on both, all 12 public routes 200.

**Pending (owner):** review of the freemium wizard templates - explicitly deferred by the owner.

---

## 2026-08-17 — STATE SNAPSHOT (V0.034). Owner is pausing here and will resume later.

Verified against the running server and the live site on this date, not recalled.

### Live and working
- **https://drawreport.com** — TLS (Let's Encrypt), nginx vhost, gunicorn `127.0.0.1:8002`.
  Three systemd units all `active`: `drawreport-web`, `drawreport-worker`, `drawreport-free`.
- **PayPal LIVE** — `PAYMENT_BACKEND=paypal`, `PAYPAL_ENV=live`, client id/secret/webhook id set.
  Real money. Read-only checks only; no test charge has ever been made.
- **Email = Brevo over SMTP** — `MAIL_BACKEND=smtp`, `smtp-relay.brevo.com:587`,
  from `team@drawreport.com`. Resend was abandoned (free tier = one domain, refused ours);
  a stale `RESEND_API_KEY` remains in `.env`, unused and harmless.
- **LLM = Anthropic** — paid `claude-sonnet-4-6` (fallback `claude-haiku-4-5-20251001`);
  free reading `claude-haiku-4-5-20251001` via its own `FREE_LLM_MODEL`.
- **Price = $29**, served from git-tracked `config/products.json`. The server has NO
  `data/products.json` (see UseCase #23), so `config/` is live. The `$59 -> $39` variant exists
  only in the local dev `data/products.json` and has never shipped.
- Free funnel `/free/` end-to-end; admin `/admin` with 13 sections; sitemap + robots served;
  og image 200; all 12 public routes 200.

### 🔴 Missing — the resume list (nothing here is broken; it is unstarted)
**Measurement — the site is currently measuring nothing external.**
1. **GA4 not set up.** `GA_MEASUREMENT_ID` is EMPTY on the server; `templates/_analytics.html`
   therefore renders nothing and zero pages emit gtag. Fix = create the property, put
   `G-XXXXXXXXXX` in the server `.env`, restart. No code change needed.
2. **Google Search Console not verified** (no `google-site-verification` meta tag; sitemap never
   submitted).
3. **Bing Webmaster Tools not verified** (no `msvalidate.01`). Bing feeds Copilot and ChatGPT
   search, and IndexNow lives there, so it is not just "the other search engine".
4. **No mechanism for verification meta tags exists** — adding 2 and 3 is a small feature
   (env-driven `<meta>` in the head), and it must go in BOTH `templates/_base.html` AND
   `templates/landing.html`, because landing.html carries its own `<head>` and does not extend
   the base template.

**SEO gaps found during this audit, deliberately left unfixed.**
5. **Sitemap omits the blog posts.** `app/routes.py` emits `/en/blog` but none of the three
   `/en/blog/<slug>` URLs — and the articles are the only organic-search surface the site has.
6. **`lastmod` is `today` for every URL on every request** — claims the whole site changed today,
   every day, which devalues the signal.
7. **No `llms.txt`.**

**Product / business.**
8. **Freemium wizard copy has NOT had the native-English pass** — owner deferred it explicitly.
   `/en/` and `/en/report` are done (V0.032); `/free/*` is untouched.
9. **Legal pages are DRAFT**, never reviewed by counsel (COPPA/children's data, refunds, PayPal,
   FTC "educational, not diagnosis" claims).
10. **Blog has 3 posts.**
11. **Launch price framing undecided** (flat $29 live vs the $59->$39 strike-through variant).

### Docs updated in this session
`CLAUDE.md` AS-BUILT rewritten to the above (the old "build it from scratch" framing is now
explicitly marked historical); memory files `drawreport-build-state` and `drawreport-deploy`
rewritten from V0.017-era text to current; `UseCasesData.md` gained #20-#23.

---

## Session — 2026-08-17 · English copy repair, site-wide (V0.035)

Applied `projectSpec/DrawReport-English-Copy-Repair-Report.md` (307 findings) with judgement:
the English was not broken, it was *translated*. 41 files changed.

### What changed, by surface
- **`config/free_texts.py`** — rewritten. The single largest concentration of translated English
  in the repo (mirror, age anchors, duration modifiers, lenses, the ask, both special paths, the
  selling close). Calques removed at the source: `what stands behind it`, `settle the reasons`,
  `on their own initiative`, `a copy of a model`, `carry through to the end`, `notable events`,
  `to hand`, `only just launching`, plus every `work` / `piece` / `sheet` for a child's drawing.
  `possessive()` now returns `Lucas’s`, not `Lucas'`. `BAND_LABELS` is `ages 3–4`, not
  `3-4 years old` — it is substituted into a sentence about the DRAWINGS.
- **`pipeline/free_prompt.py`** — the highest-leverage file, since no template fix reaches the
  *generated* reading. Added a real **HOW THE ENGLISH MUST SOUND** section (US spelling/vocabulary,
  vary sentence length, no em-dash-joined clauses, no rule-of-three, an explicit banned-vocabulary
  list, read-it-back-as-the-parent). Removed the British spellings that were priming the model,
  rewrote every worked EXAMPLE (they set the register for their block and were being copied almost
  verbatim), un-mandated the canned `"Notice how..."` opener, broadened the not-X-but-Y ban from
  psychological negation to all five blocks, killed the stock phrases `the theme holding them` and
  `in the tradition of reading children's drawings`, and gave `insufficient_reason` real
  instructions — it renders word-for-word to a bounced visitor and previously had none.
  `FREE_PROMPT_VERSION` 1.0 → 1.1.
- **`pipeline/free_lint.py`** — the coupled half of the above. See **UseCase #24**.
- **`pipeline/free_schema.py` / prompt** — the three contradictory word budgets reconciled. **#25**.
- **Public pages** — `home.html`, `landing.html`, `_base.html`, `_header.html`, `app/content.py`
  (FAQ + scenarios), `config/products.json`, `config/form_fields.py`, plus order / cabinet /
  login / sample / blog / error / stub templates.
- **Emails** (all 7) + `app/mailer.py` subject lines; **PDF strings** in `pipeline/render.py` and
  `config/report_texts.json`; **`pipeline/samples/sample_report.json`** (the shipped sample, which
  is real pipeline output and carried the same tells into the page customers judge us by);
  the **3 blog posts**; **`app/legal.py`** (language only — every load-bearing clause preserved,
  still DRAFT, still needs counsel).
- Typography swept: curly `’ “ ”` and real em dashes everywhere, replacing the spaced ASCII hyphen.
  Fonts checked first — **UseCase #26**.

### Judgement calls (not everything in the report was applied as written)
- **F-056 seven dimension names — RECONCILED rather than skipped.** The report said "fix all three
  lists or leave them alone". The paid report's real labels live in `pipeline/prompt.py`
  `DIMENSIONS["en"]` and were already the good short ones (`Mood & expression`,
  `Technique & materials`). `free_texts.SEVEN_DIRECTIONS` had drifted away from them, which made
  the free funnel's sales list quietly false. Aligned it to the paid labels, with a comment naming
  the source of truth.
- **F-020** `How should we refer to your child?` → `Which pronoun should we use for your child?`
  (the report proposed "Which word should we use", which is no more idiomatic; the options are
  literally she/he/they).
- **F-091** written as "we only keep photos for 90 days" rather than the report's
  "as our retention policy says we would" — same commitment, less legal register.
- **F-224 / F-225** applied with em dashes, not the ASCII hyphens the report's own replacements
  used — those contradicted its F-003.
- Findings inside CSS/JS comments were left alone (not visitor-facing), matching the report's own
  rendered-vs-source discipline.
- **Found beyond the report:** the same `activities for parents` calque in the meta descriptions of
  `templates/sample.html` and `templates/blog_index.html`.

### Verification
- All Python byte-compiles; all edited JSON parses.
- Every free-summary path exercised (7 concerns × 5 durations × 3 pronoun forms) — no unfilled
  `{slot}`, no ASCII-hyphen dashes; all four narrative branches read end to end.
- All 12 public routes render 200 and were scanned as **rendered HTML** (UseCase #20) against the
  banned tells: zero hits outside CSS comments.
- Sample report re-rendered: 10-page PDF, fonts `Caveat / Inter / Rubik` only — **no fallback**,
  curly typography present, every flagged phrase gone.
- Prompt↔linter round trip: an analysis written in the new voice lints clean (0 violations,
  276 words), and all four new hedges + three new attribution forms match.
- Server checked read-only: no `data/products.json` and no `data/report_texts.json`, so the
  `config/` edits are what production serves (UseCase #23).

### Still open after this session
Item 8 of the resume list (freemium native-English pass) is now **done** — the owner had deferred
it, and this report covered it. Everything else on the list stands: **GA4 / GSC / Bing are still
unset**, the sitemap still omits the blog posts, `lastmod` is still `today`, there is still no
`llms.txt`, legal is still DRAFT-pending-counsel, and the blog still has 3 posts.
**The biggest remaining copy risk is `pipeline/prompt.py` — the PAID report prompt was NOT audited**
(Appendix C). Everything §1d found in the free prompt (British spellings, calqued examples,
mandatory sentence templates, no English-voice instruction) is very likely also shaping the
8-page PDF customers pay $29 for; `sample_report.json` was indirect evidence of exactly that.
That is the highest-value follow-up.

---

## Session — 2026-08-18 · Paid report prompt: language and tone (V0.036)

The follow-up named in V0.035 and in Appendix C of the copy report: `pipeline/prompt.py`, the PAID
report prompt, was the last unaudited copy surface and the one behind the $29 PDF.
**Language and tone only — no rule, ban, zone, score rule or safe-frame condition was changed.**
`PROMPT_VERSION` en-4.0 -> en-4.1.

### What the audit actually found (checked, not assumed from the free-prompt findings)
Two of the free prompt's biggest problems **do not exist here**, and were not "fixed":
- **British spellings: none.** The free prompt had 11; this one is clean.
- **Contradictory word budgets: none.** `about_child` is 110-170 in both the prose and the JSON
  contract, and `pipeline/schema.py` sets no word ceiling at all.

What did transfer was evidenced from `pipeline/samples/sample_report.json` — real output of this
prompt — rather than asserted (see UseCase #28):

| prompt line | what it produced in shipped output |
|---|---|
| `"authorial solutions"` | `"small but real authorial decisions"` |
| `"departures from the template"` | `"follows a familiar template"` x2 |
| ALLOWED example ending `"…as examples."` | `"or engineering, as examples."` x2 |
| `"emotional register"` | `"The overall register of this drawing"` x2 |

Plus: line 86 **mandated** the canned openers `"Notice how…" / "Look at the way…" /
"What matters here is…"`; line 64 offered two fixed generic attributions as *the* preferred form;
and the prompt carried 63 em dashes in 3,258 words.

**The gap: this prompt was WEAKER than the free one had been.** Its entire English-voice
instruction was the five words *"The report language is English."* The free prompt at least said
"American English", which the audit had already judged insufficient.

### Changes
- **Added `HOW THE ENGLISH MUST SOUND`** — the F-119 equivalent, written for this prompt rather than
  copied from the free one. US spelling/vocabulary, sentence-length variation, rationed em dashes,
  no rule-of-three default, no `not X but Y`, a banned-vocabulary list, no consulting/clinical
  register, no self-praising tone labels, parent-language nouns for the drawing, read-it-back-as-
  the-parent. **Its first rule is paid-specific:** the seven dimension observations are seven
  parallel blocks, so writing them to one shape is the most visible template risk in the product —
  nothing previously forbade it.
- De-templated the observation formula (kept the logic, removed the visible three-beat pattern) and
  downgraded the canned openers from required to "examples of the move, cap of one per report".
- The generic attributions and the hypothesis hedges must now **rotate**; added `may point to`,
  `often goes with`, `reads like`.
- Removed the studio-critic vocabulary traced above, and the sentence-final `as examples` calque.
- Rewrote the **gold-standard zone-3 sentence** — the register-setter for the report's highest-value
  block — dash-free and concrete. All four frame conditions still visibly demonstrated, and
  `"a hypothesis, not a conclusion"` kept verbatim because `lint.py` `HEDGE` matches that literal.
- The **repair instruction** now carries a VOICE line: adding the safe frame must not add a dash, a
  triad, a `not X but Y`, or clinical vocabulary — otherwise the repair pass reintroduces exactly
  the register the prompt just removed.
- Fixed a self-contradiction the new rules exposed: the prompt banned `"the work"` for a child's
  drawing while still using it twice itself.

### `pipeline/lint.py` — the coupled half (UseCase #24)
`_frame_scan` requires `ATTRIBUTION` to match within ±220 chars for heavy terms, so new attribution
wording that the regex cannot see turns a correctly framed report into a repair call. `ATTRIBUTION`
and `HEDGE` extended in the same commit to cover every form the prompt now offers.

**This surfaced a pre-existing bug — see UseCase #27.** The phrase
`"in the practice of reading children's drawings this is sometimes read as…"` has been offered by
the prompt as a valid frame since en-4.0 and was **never matched by `ATTRIBUTION`**. Every report
that used it on a heavy term burned a repair call, and the repair rewrote it into the one stock
phrase the regex did know — which is part of why that phrasing became ubiquitous. Now matched.

### Verification
- Both files compile; the system prompt assembles (4,025 words) and the user prompt builds.
- **Coupling test:** all 5 attribution rotations and all 8 hedges are (a) present in
  `system_prompt()` and (b) matched by the linter regex. This is the check UseCase #27 asks for.
- **Safety regression suite:** bare diagnosis, unframed state, hidden trauma, colour fortune-telling,
  fate-as-fact and command tone are all still caught (1-3 hits each).
- The shipped sample still lints clean; the 7 dimension keys and order are unchanged.
- No LLM call was made — generating a report costs money on the live key, and nothing in this change
  can be validated by one run anyway. The next real report will be tagged `en-4.1`; **that output is
  what should be read before assuming the voice change worked.**

### Follow-up
`PROMPT_VERSION` is recorded per report by `pipeline/llm.py`, so en-4.0 and en-4.1 reports are
distinguishable in the DB. Worth reading one fresh en-4.1 report end to end against the
`HOW THE ENGLISH MUST SOUND` list — especially whether the seven observations now vary in shape,
which is the rule with the least prior art behind it.

---

## Session — 2026-08-18 · Paid report **en-4.2**: the north star (V0.037)

Implemented `projectSpec/TASK-paid-report-en-4.2-north-star.md` in full, then regenerated both
samples as **V2** and measured against the task's own acceptance table.
**This is about WHAT the report talks about, not how the English sounds** (UseCase #30).

### 🔴 Ship-blocker fixed: every English PDF carried a Russian footer
`static/css/report.css` hardcoded
`content: "Голос рисунка · образовательное наблюдение, не диагностика · стр. "` in
`@page { @bottom-center }` — inherited from the Golos sibling. It printed on **9/9 and 11/11 pages**
of the two sample PDFs, and on every report any customer has ever received.
Fixed the i18n-correct way (UseCase #6): the string is now `REPORT_STRINGS["en"]["page_footer"]` in
`pipeline/render.py`, emitted from `templates/report.html` as an inline `@page` override; the CSS
keeps only the typography. The file's 15 Russian comment blocks were translated too — `report.css`
is now Cyrillic-free. Verified: **0 Cyrillic characters in either V2 PDF.**

### Prompt en-4.1 -> en-4.2 (no zone, score band, frame condition or disclaimer touched)
Activities must now change something BETWEEN parent and child; materials capped at one for the
whole report; skill drills banned; every activity NAMED like a game; directions 6-7 hard-capped at
2 sentences / 1 activity; NO RECYCLING (a fact may carry at most two directions) and LENGTH FOLLOWS
THE MATERIAL. `ALWAYS FORBIDDEN` gained **normality verdicts about this child** — the
highest-consequence line, because a false all-clear is the failure that could actually harm.
Per §3.7 the attribution wordings were deliberately left alone.

### `pipeline/lint.py` — enforcement, exactly the two sets the task scoped
`DRILL_BANNED` (activities only) and `NORMALITY_VERDICT` (every prose field, no allow-list amnesty).
Both immediately caught real defects in the **already-shipped V1 reports**: bead-stringing /
playdough / dot-to-dot / mazes in direction 7 of both, and `"a normal and healthy part of…"` in
Alisia's about_child. No style checks added, per §0.
⚠️ While writing those tables a generator script turned every `` into a literal backspace — the
rules compiled, imported, and matched nothing. See **UseCase #31**; the test suite is the only
reason it surfaced.

### Acceptance — V2 vs V1, measured

| # | Check | Alisia V2 | Dilan V2 |
|---|---|---|---|
| 1 | Cyrillic in PDF | **0** PASS | **0** PASS |
| 3 | Fine-motor drills | **0** PASS (was 1) | **0** PASS (was 1) |
| 4 | Activities named | **100%** PASS (was 0%) | 75% MISS (was 0%) |
| 6 | Dir 6/7 caps | **PASS** (2 sent/1 act, 2 sent/0 act) | MISS (dir6 = 3 sentences) |
| 8 | Normality verdicts | **0** PASS (was 1) | **0** PASS |
| 9 | Linter violations | **0** PASS | **0** PASS |
| 11 | Embedded fonts | Caveat/Inter/Rubik only PASS | PASS |
| 2 | Material suggestions (cap 1) | 2 MISS | 2 MISS |
| 5 | Fact used in >2 directions | MISS (`hair` 16 -> 22) | MISS |
| 7 | Alisia total words | 2,146 (target 1,700-2,100; was 2,870) | n/a |

Activities per report dropped 12 -> 7 (Alisia) and 14 -> 12 (Dilan); direction-7 activities are
now shared games, and Alisia's direction 7 honestly has none.

**The judgment check passes.** Alisia's report is now about Alisia: technique and fine motor are
two sentences each, and everything else is her — *"she has a picture in her mind of what beautiful
looks like, and she's patient enough to get there."* Activities read as named family games
("Who is she today?", "Heavy and light", "Mirror drawing") rather than homework.

### The four residual misses, and why they are all the same miss
Every failing check is a **prompt-only rule**, and every passing one has a linter behind it or is
mechanical. That is UseCase #29 restated, and it reproduced exactly:
- **Materials cap (both reports, off by exactly one).** Systematic, not random: the model spends
  one allowance inside a direction and one in `art_recommendations`, satisfying each rule locally.
  §3.2 anticipates this in words ("only if you have not already spent the report's single materials
  suggestion inside a direction") and the words were not enough.
- **NO RECYCLING did not take at all** — `hair` went 16 -> 22.
- Naming and the dir-6 sentence cap held on the short report, slipped on the long one.

**Recommendation (NOT done — §4.2 scoped the linter to two rule sets):** a materials counter in
`lint.py` that counts across directions *and* recommendations and raises one violation past the
first. It is the only residual miss with a clean mechanical definition, it is an explicit
acceptance number, and it would make both reports pass. Owner's call.

### Out of scope, flagged as §7 requires
Technique sections are now genuinely thin (2 sentences). `/en/report` and `config/products.json`
still read true — they promise "7 areas, each with a score and a plain-language explanation",
which remains accurate — so no marketing copy was edited.

---

## Session — 2026-08-18 · The approved en-4.2 samples go live (V0.038)

The two V2 sample reports were reviewed and approved, so they are now the site's published
examples. **These are the first samples on the site that are real, unedited output of the live
pipeline** (prompt en-4.2) from real children's drawings — until now the landing showed one
adapted built-in example.

### What shipped
- `pipeline/samples/alisia_report.json` + `alisia_drawing.jpg` — Alisia, 4y4m, one drawing.
- `pipeline/samples/dilan_report.json` + `dilan_drawing_{1,2,3}.jpg` — Dilan, 6y5m, **three**
  drawings, which is the case `/en/report` actually sells ("1-3 drawings together") and which
  the site had no example of.
- Both registered in `app/samples.py`; `sample-liam` kept last so its indexed URL does not 404.

### Two things the wiring needed
1. **The sample system only supported ONE drawing per sample.** `_SAMPLE_DEFS` had a singular
   `drawing` key and `/r/<token>` built a single-item `specs` list, so Dilan's report would have
   rendered with one image and a report body discussing three. Changed to a `drawings` LIST,
   with `n_drawings` now DERIVED from it (it was a hand-maintained field that could drift), and
   `/r/<token>` captions them exactly like a paid multi-drawing report — "Drawing 1..N" when
   there are several, the child's name when there is one. `sample_drawings()` still accepts the
   old singular key so an older locale definition keeps loading.
2. **Image weight.** `/r/<token>` embeds every drawing as a base64 data URI. The originals are
   PNGs up to 890 KB, which would have made the Dilan sample page ~4 MB. They ship as optimized
   JPEGs (1400 px long side, q82): 890 KB -> 94 KB, 821 KB -> 100 KB. The rendered 3-drawing
   sample page is **298 KB**.

Note `data/` is gitignored, so a sample cannot be served from `data/reports/images/` — the
approved files had to be copied into the tracked tree to deploy at all.

### Verified
All three sample pages and all three hosted reports return 200; Dilan's renders 3 drawings; no
Cyrillic anywhere (the en-4.2 footer fix holds); the landing carousel shows all three with the
"sample · 3 drawings" badge on Dilan; the sitemap lists all three.

### Worth the owner's attention
Card quotes are pulled from `about_child` automatically, and they landed well —
*"Dilan is a builder of worlds."* / *"Alisia is drawn to beauty, decoration, and the pleasure of
making something feel complete."* Nothing was hand-picked.

`sample-liam` is now the odd one out: it is en-4.0-era content and is no longer what a buyer
receives. It was kept only to avoid a dead URL. Retiring it (and 301-ing the URL) is a small
follow-up once the two real samples have settled.

---

## Session — 2026-08-18 · Third sample added, the placeholder sample retired (V0.039)

The sample set is now **three real reports covering 1, 2 and 3 drawings** — the full range
`/en/report` sells ("1-3 drawings from the same period"), which the site previously had no
example of beyond a single drawing.

| token | child | drawings | pages | badge |
|---|---|---|---|---|
| `sample-alisia` | Alisia, 4y4m | 1 (crayon portrait) | 9 | sample report |
| `sample-maya` | Maya, 7y2-3m | 2 (pencil, girl with a braid) | 10 | sample · 2 drawings |
| `sample-dilan` | Dilan, 6y5m | 3 (harbor / family / dragon) | 12 | sample · 3 drawings |

All three are unedited en-4.2 output from real children's drawings. Carousel order is 1 -> 2 -> 3
drawings on purpose. **"Maya" is a name I chose** — the owner supplied the drawings without one;
renaming is a one-line change in `app/samples.py` plus a regenerate.

### `sample-liam` removed, and why regenerating it was not the answer
The owner asked to regenerate it under en-4.2. Doing so surfaced the real problem: **the image
was never a child's drawing.** `sample_drawing.png` is flat vector art — measured, **11 unique
colors covering 99.3% of pixels**, against 47,576 for a photographed crayon drawing and 135,790
for a felt-tip one. It entered the repo in V0.017 as a stand-in.
The report that had been live for months therefore said *"the lines are not perfectly straight or
closed, which is typical and expected at 6"* about mathematically straight vector lines — text
adapted from the Russian sibling, never written from that image.
Regenerating under en-4.2 produced a clean report (0 lint hits) that praised the *"confident and
direct"* stick-figure lines and *"even and controlled"* color fills of a computer-drawn graphic,
and scored it 6-7/10 on fine motor and technique. **A new prompt only reworded the fabrication**;
no prompt version fixes an input that was never a child's drawing.
Removed: the definition, and `sample_report.json` / `sample_drawing.png` themselves.
`/en/sample/sample-liam` and `/en/r/sample-liam` now **301** to the Alisia sample — the URL was
public for months and is in older sitemaps, so it must not 404. `scripts/render_sample.py` was
repointed at `alisia_report.json`, so the QA fixture is now a real report too.

### Noted, not acted on
en-4.2 has an explicit rule to return `insufficient_input` when the image is not a child's
drawing, and it **did not fire on obvious vector clip art**. Low impact in production — real
customers photograph paper — but it is a genuine gap in the rejection path, and the only reason
it mattered here is that we were feeding it a synthetic asset.

### Acceptance for the new sample (en-4.2 criteria)
0 Cyrillic · 0 drills · 0 normality verdicts · 0 linter violations · activities named 10/10 ·
directions 6 and 7 both at exactly 2 sentences / 1 activity (the caps held) · scores 9/8/9/7/8/8/8.
Prose-style items (23 em dashes, one "not X but Y") are accepted per UseCase #30 and were not
touched.

---

## Session — 2026-08-18 · One shared footer; samples + FAQ on the home page (V0.040)

### 🔴 The footer existed twice and had drifted
`landing.html` does not extend `_base.html`, so it carried its own `<footer>`. The two copies
diverged: the base version — used by **every page except `/en/report`** — had lost the legal
links entirely. The home page, the free wizard, the order form, the blog, the sample pages and
the 404 all shipped a footer with **no Privacy Policy, no Terms, no Refunds link**. On a page
where someone is deciding whether to pay $29, and on the pages where they would go looking for
the refund policy, that is the worst place to lose them.

Fixed by extraction, not by copying: `templates/_footer.html` is now the single source, included
by both `_base.html` and `landing.html`. The version badge stays with whichever template owns the
`<footer>` element, since only it knows if it is inside the base layout. Verified identical on all
nine page types including the 404.

### Samples and FAQ added to the home page
Both were on `/en/report` only, which meant a visitor landing on `/` and going straight into the
free funnel **never saw a single example of the product**. Both sections are now shared partials
rendered on both pages:
- `templates/_samples.html` — the sample carousel (all three reports).
- `templates/_faq.html` — the FAQ, from the one source in `app/content.py`, so the two doors of
  the funnel cannot drift on what the product is.
- `templates/_page_js.html` — the carousel and reveal-observer JS, lifted out of `landing.html`.

`app/routes.py index()` now passes `samples` and `faq`.

**Analytics stays separable.** Both partials take a `goal_prefix`, so the home page emits
`home_faq_open` / `home_sample_open_<token>` and the landing keeps `landing_*`. Without that the
admin could not tell which door a sample was opened from — the same reasoning that keeps
`home_view` and `landing_view` distinct.

### The `.reveal` restriction is lifted
`home.html` carried a standing warning that `.reveal` must never be used there: the class is
`opacity:0` and the observer that adds `.is-in` lived inside `landing.html`'s inline script, so
any `.reveal` block on another page would stay invisible forever. That observer now lives in
`_page_js.html`, which home includes — the warning in the template header was rewritten to say so,
with the condition attached (drop the include and you must drop the classes with it).

Landing-only JS (the hero "what's inside" popup, the quote rotator) deliberately stayed inline in
`landing.html`; no other page has those elements.

### Flagged, not acted on
The FAQ text now appears on two indexable pages. `/en/report` carries the `FAQPage` JSON-LD and
`/` does not, so there is no competing structured-data claim, but it is duplicate body copy on the
two most important pages. Worth a look once Search Console is verified and there is data to judge
it by — the alternative (a shortened FAQ on the home page) trades away exactly the reassurance the
section is there to provide.

---

## Session — 2026-08-18 · Home recognition-block CTA (V0.041)

`"Start with one drawing"` -> **`"Get a free reading of your child's drawing"`**.

Owner's call, and it was the odd button out: the home page's other two CTAs both say
"Get a free reading", while this one described what the VISITOR has to supply rather than what
they get, and never said free - the most persuasive word available at that point in the page.

It sits under the worry list *and* under the "or maybe nothing worries you and you're just
curious" line, so it deliberately is not worded around a worry.

Minor: the rationale went in as an HTML comment first, which ships to every visitor. Moved to a
Jinja `{# #}` comment so it stays in the source and out of the response.

---

## Session — 2026-08-18 · Mobile burger menu (V0.042) — end of session

### The bug
Owner reported no burger on mobile. It was not hidden — **it never existed**.
`components.css` had, inherited from Golos:
`.site-nav { display: none; }  /* мобайл: лого + Войти + CTA, без JS-бургера */`
("mobile: logo + Sign in + CTA, no JS burger"). So at ≤880px the nav simply vanished and nothing
replaced it: **Full report, Examples, Pricing and Blog were unreachable from a phone** — on a
product whose whole design premise is "a parent on a phone, late in the evening."

### The fix
- `_header.html` gains a burger button and a dropdown panel. Its JS lives **in the header partial**,
  not in `_page_js.html`: the header is on every page and `landing.html` does not extend
  `_base.html`, so a shared JS partial would need including twice and would eventually be forgotten
  in one of them.
- "Sign in" moves into the panel at ≤880px — a 360px row cannot hold logo + link + CTA + burger
  without squeezing the CTA, which is the one thing that must stay.
- CSS through the design system (`components.css`, tokens only, no hardcoded colors). Burger
  animates to an X; `prefers-reduced-motion` disables it.
- Accessibility: real `<button>` with `aria-expanded` / `aria-controls` / `aria-label`, visible
  focus ring, and it closes on outside click, Escape (returning focus), link click, and on resize
  past the breakpoint so a stray open panel cannot overlay the desktop layout.
- Analytics: `header_menu` plus `header_menu_*` per link.
- The Russian comments in that CSS block were translated while there.

### Verified in a real browser, not just in markup
Chrome would not resize below ~1000px, so the responsive behaviour was tested inside a **390px
iframe**, which gets its own viewport and therefore evaluates the real media query:
- 390px: burger `display:flex`, 40x40, at x=321 — **on the same row as the logo, not under it**
  (the owner's suspicion), inline nav hidden, Sign in hidden, panel starts `hidden`.
- Opens/closes correctly; all 5 links render; panel sits below the header row; closes on outside
  click, Escape and link click. Confirmed on `/en/report` too, which has its own `<head>` and
  inlined CSS.
- 1200px on home, landing and free: burger `none`, inline nav `flex`, Sign in visible — desktop
  untouched.

### Also this session
`CLAUDE.md` brought up to date: AS-BUILT header to V0.042, a table of the shared template partials
and why they exist, the three real samples, the mobile-nav rule, `PROMPT_VERSION en-4.2` with the
prompt↔linter warning, the website-vs-report English split (UseCase #30), and two new resume items
(the `insufficient_input` gap, the materials cap).
