# Build-from-Golos map

Exactly what to take from `C:\projects\GolosRisunka` (READ-ONLY) and how. Three buckets:
**COPY verbatim**, **ADAPT**, **REPLACE**. Plus what the **owner provides**.

> **⚠️ The report pipeline now follows PHILOSOPHY 2.3 (prompt v4.0) — see
> `projectSpec/HANDOFF-english-philosophy-2.3.md`.** The RU reference already implements it
> (`pipeline/prompt.py` PROMPT_VERSION 4.0, `schema.py` with `about_child` + the 7 new directions +
> `understanding_/art_recommendations` + `specialists` + `development_directions`, `lint.py` frame-check,
> `config/report_texts.json`). **Mirror the CURRENT Golos structure**, then apply the **English
> recalibration**: zone-3 (psychological) dialed DOWN, safe frame airtight, wider HARD bans, "educational
> observation, not diagnosis" ironclad. DrawReport's LLM is Anthropic Claude via `pipeline/llm.py` — the
> prompt/schema/lint concepts port unchanged; only the provider call differs.

## COPY verbatim (then only de-Russify comments if needed)
| Golos path | Notes |
|---|---|
| `static/css/tokens.css` | Palette «Golden Hour», 7-step scale, radii, shadows. Keep `--bg` = logo bg. |
| `static/css/components.css` | Full component library (buttons, cards, hero, carousels, reveal, dots, forms, etc.). |
| `static/css/report.css` | PDF report styling (separate system; brand-book does NOT govern it). |
| `static/css/fonts.css` + `static/fonts/*` | Self-hosted Rubik/Inter/Caveat subsets (Latin + `$` covered). |
| `projectSpec/brand-book.md` | Design source of truth. Keep; swap RU examples for EN where textual. |
| `pipeline/schema.py` | Pydantic contract (language-neutral). |
| `pipeline/images.py` | Resize/HEIC handling. |
| `pipeline/render.py` | JSON → HTML → PDF. |
| `pipeline/gemini.py` | Gemini call + retries + lint+repair loop (logic; prompt content is per-locale). |
| `scripts/` | `hello_pdf.py`, `render_sample.py`, `generate_report.py`, `regenerate_report.py`, `bump_version.py`, `build_hero_image.py`, `build_logos.py`, `export_static.py` (optional), deploy scripts (scope to drawreport). |
| `worker.py`, `app/jobs.py` | Report worker + job runner. |
| `app/auth.py` | Email-code login (TTL, rate limit). |
| DB schema + init (in Golos `app/`) | SQLite tables + migrations. |
| `templates/report.html` | Report template (localize fixed strings). |
| `templates/_base.html`, `_header.html`, order/cabinet/login/legal/error templates | Structure; **all strings → i18n**. |
| `release.bat`, `deploy.sh`, `restart.sh` | Mirror; scope deploy to drawreport units/paths. |

## ADAPT (copy structure, change content/logic)
| Area | From Golos | Change for DrawReport |
|---|---|---|
| **Prompt** | `pipeline/prompt.py` v4.0 (Russian) | English prompt, **per-locale** (`PROMPTS["en"]`); adopt **philosophy 2.3** (portrait of the child + 4-condition safe frame + 7 new directions). NOT a literal translation; **dial zone-3 DOWN for US** (handoff §2). |
| **Schema** | `pipeline/schema.py` v4.0 | Mirror v4.0 fields: `about_child`, the 7 directions, `understanding_/art_recommendations`, `specialists`, `development_directions`, refusal branch. Language-neutral keys. |
| **Linter** | `pipeline/lint.py` (frame-check) | English HARD-ban patterns (wider for US), hedge list, attribution names (Piaget/Lowenfeld/Vygotsky/Machover…), artifact-noun list; frame-check only on interpretation fields; repair = "add frame, don't delete meaning". |
| **End-of-report texts** | `config/report_texts.json` | Mirror: admin-editable upsell (per 1/2/3 drawings) + disclaimer + free block, pass-through. |
| **All UI templates** | hardcoded Russian | English via Flask-Babel catalog; no hardcoded strings (see `i18n-architecture.md`). |
| **Products** | `config/products.json` | USD prices; English `title/subtitle/features`; per-locale text. |
| **Landing copy** | `templates/landing.html` RU copy | English DRAFT per `positioning-en.md` (adapt, mark for owner review). |
| **FAQ / testimonials / legal** | `app/routes.py` consts / templates | English, per-locale; US legal (COPPA). |
| **Blog** | `content/blog/*` | A few articles adapted to English under `content/en/blog/`. |
| **Sample reports** | `data/` sample JSON + images | Reuse drawings; **American child names**; English report text. |
| **Logo / hero in header** | `_header.html` `<picture>` | English logo images (built from owner's `data/Images/`). |
| **routes / locale** | `app/routes.py` | Add locale prefix routing + resolver; localize all rendered content. |

## REPLACE (different provider/region)
| Concern | Golos | DrawReport |
|---|---|---|
| **Payment** | ЮKassa (+stub) behind payment abstraction | **PayPal Business** (Orders API) behind the same abstraction. |
| **Email** | Unisender Go backend in `app/mailer.py` | **Resend** backend (HTTP API) in the same `mailer.py`. |
| **Currency** | ₽ | **$ (USD)**, Babel formatting. |
| **Analytics** | Yandex Metrika + first-party | Optional; if used, a US-appropriate analytics (or keep first-party only). Don't block launch on it. |
| **TLS/host** | golosrisunka VPS, shepotzvezd co-tenant | Hetzner 5.78.181.152, **cosmyday-api co-tenant** (port 8001). DrawReport = port 8002, own units/vhost/cert. |
| **Legal** | RU oferta/privacy | **US** privacy (COPPA/children's data), terms, refund. |

## Owner provides (will be supplied; build with stubs until then)
- `.env` secrets: `GEMINI_API_KEY`, `PAYPAL_CLIENT_ID/SECRET` (sandbox+live), `RESEND_API_KEY`,
  `ADMIN_PASS`, `MAIL_FROM_EMAIL`, etc.
- Logo source images → `data/Images/` (English wordmark strip + square icon).
- Hero image (reuse Golos `data/Images/Hero.png` if owner approves, or a new one).
- Launch price(s).
- Real child drawings for sample reports if different from Golos's.
- DNS for drawreport.com → 5.78.181.152; server access for deploy.

## Golos reference docs worth reading first
- `C:\projects\GolosRisunka\CLAUDE.md` — full architecture + hard rules.
- `C:\projects\GolosRisunka\DevelopmentStatus.md` — the build journal (how each phase was done).
- `C:\projects\GolosRisunka\UseCasesData.md` — solved problems (e.g. inline-CSS must be `| safe` #24;
  binary assets built by host script #25; WeasyPrint var() gotchas; Cyrillic console — the `$`/Latin
  equivalents are simpler). Seed DrawReport's own `UseCasesData.md` from the relevant ones.
- `C:\projects\GolosRisunka\projectSpec\brand-book.md` — design system spec.
