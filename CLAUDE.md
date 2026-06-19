# CLAUDE.md — DrawReport (drawreport.com)

> **You (Claude Code) are building this project from scratch by faithfully cloning a proven Russian
> sibling site and adapting it to a US/English audience. READ the companion docs in this folder
> before starting: `development-plan.md`, `i18n-architecture.md`, `build-from-golos.md`,
> `positioning-en.md`. They are your spec. Build in phases, commit per phase, pause for owner
> review at milestones.**

---
## ✅ AS-BUILT STATUS (updated 2026-06-19) — build is COMPLETE; this section overrides the "building from scratch" framing above
Full system built, verified, committed, pushed to **https://github.com/spashap/DrawReport** (`main`, VERSION 0.015). All phases M0–M9 done. The spec docs below remain useful reference; these are the deviations + resume facts.

**Deviations from the original spec (current reality):**
- **LLM = Anthropic (Claude), not Gemini.** Provider abstraction: `pipeline/llm.py` (orchestrator: attempts, JSON validate, lint+repair, primary→fallback model) + `pipeline/anthropic_llm.py` (default) + `pipeline/gemini.py` (alternate). Env: `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-sonnet-4-6`, `LLM_FALLBACK_MODEL=claude-haiku-4-5-20251001`, `ANTHROPIC_API_KEY`. Verified live (full report, 0 lint hits, 8-page PDF, zero fallback fonts). Prompt lives in `pipeline/prompt.py` (`PROMPTS["en"]`, English, not yet polished). When editing LLM code, consult the `claude-api` skill.
- **Analytics = GA4** client snippet (`templates/_analytics.html`, placeholder `GA_MEASUREMENT_ID`) + first-party events/admin dashboards (kept). Not Yandex.
- **Server path = `/var/www/DrawReport` (capital D/R)**. Local dev on **port 3000** (`PORT` env, default 3000); prod gunicorn on **127.0.0.1:8002**.
- **Deployment kit = `drawreportDeploy/`** (provision.sh / deploy.sh / restart.sh / systemd units / nginx vhost / README). Copy to server `/var/www/drawreportDeploy`, run as root. See `DEPLOY.md`. `.gitattributes` forces LF on `*.sh/*.service/*.conf`.
- **DNS:** owner manages A records at the **registrar** (drawreport.com + www → server IP), **no Cloudflare** (or grey-cloud only — orange proxy breaks certbot + crawlers). TLS via `certbot --nginx`.

**Run locally:** `venv\Scripts\python.exe run.py` (web :3000) + `venv\Scripts\python.exe worker.py`. Admin at `/admin/login` (pass = `ADMIN_PASS`).

**Owner still to do before public launch:** DNS + `provision.sh` + `certbot`; in server `.env` set `PUBLIC_BASE_URL=https://drawreport.com` + strong `ADMIN_PASS`; add `RESEND_API_KEY`+`MAIL_BACKEND=resend`, `PAYPAL_*`+`PAYMENT_BACKEND=paypal`, `GA_MEASUREMENT_ID`; review DRAFT copy (landing/blog/legal) + legal with counsel; drop real logo art in `data/Images/` + run `build_logos.py` (placeholders ship; hero already built from owner art).

**Resume pointers:** journal `DevelopmentStatus.md` · solved problems `UseCasesData.md` · plan `development-plan.md`.

---

## What this is
DrawReport: a parent uploads 1–3 of their child's drawings + a little context, pays, and receives a
PDF report about the child's development — strengths, growth areas, and simple at-home activities —
based on what is visibly in the drawing and on the developmental stages of children's art.
**Educational observation, NOT psychological or medical diagnosis.** English first, architected
multi-language from day one (see `i18n-architecture.md`).

Pipeline: **LLM (Claude Sonnet 4.6, via the `pipeline/llm.py` provider abstraction) → JSON
(pydantic-validated) → Jinja2 → WeasyPrint PDF.** (Originally specified as Gemini; switched to
Anthropic — see AS-BUILT STATUS above.)

## ⛏️ THE REFERENCE PROJECT — read-only, copy don't invent
A complete, working, production sibling site exists at **`C:\projects\GolosRisunka`** (Russian:
golosrisunka.ru). It is mounted READ-ONLY for you.

- **RULE: NEVER create, edit, move, or delete anything inside `C:\projects\GolosRisunka`. Read only.**
- It is the source of truth for architecture, the report pipeline, the design system, the prompt
  philosophy, the admin/analytics, and the deploy scripts. **Lift its patterns verbatim, then adapt** —
  do not paraphrase logic or the prompt from memory.
- Public mirror: https://github.com/spashap/golosRisunka — but the **local folder is more complete**
  (it contains gitignored assets: `data/` sample-report JSON + drawing images, the real prompt in
  `pipeline/prompt.py`, fonts). Prefer the local folder.
- `build-from-golos.md` maps exactly which files to copy verbatim vs adapt vs replace.

## This repo
- Git: **https://github.com/spashap/DrawReport** (new, clean). Branch `main`. Push here.
- Local: `C:\projects\drawReport`.
- Stack: **Python 3 / Flask / Jinja2 / WeasyPrint / SQLite / google-genai**, gunicorn + background
  worker (systemd in prod), nginx, Let's Encrypt. **NOT Node, NOT Vercel** — server-side PDF + long
  report jobs require this stack (this was decided deliberately; do not switch).

## The product model (same as Golos)
1. **snapshot** — up to 3 drawings → ONE consolidated report; price independent of drawing count.
2. **development** — compare two sets ≥6 months apart (may be "coming soon" at launch).
- **All prices/numbers come from `config/products.json`** (future admin). Never hardcode prices.
- Prices in **USD ($)**. Owner sets launch price.

## US adaptations vs the Russian original
- **Language/UI:** English, via i18n (see `i18n-architecture.md`). **No hardcoded UI strings** anywhere —
  everything through the translation layer, English as the first catalog.
- **Payment:** **PayPal Business** (Orders API: create order → capture → webhook). Drops into the same
  payment-provider abstraction Golos uses for its stub/ЮKassa. Build with a stub provider first; owner
  wires real PayPal creds in `.env`.
- **Email:** **Resend** (HTTP API). Implement as a `resend` backend behind the same `mailer.py`
  abstraction (Golos has outbox/unisender backends). Owner provides `RESEND_API_KEY`.
- **Currency:** USD `$`; number/date formatting per-locale via Babel. (No ₽.)
- **Sample reports:** reuse Golos sample JSON + drawing images; **rename children to American names**;
  translate report content to natural US English (adapt, don't literal-translate).
- **Logo:** English wordmark (owner provides source images in `data/Images/`; build with a host script
  like Golos `build_logos.py`). Same «Golden Hour» visual identity otherwise.
- **Legal (US):** privacy policy + terms addressing **children's data / COPPA** (parent uploads child
  drawings), refunds, and PayPal. Keep the "educational, NOT diagnosis" framing — important for US
  (FTC) claims. This is not legal advice; flag for owner to review with counsel.

## Hard rules (inherited from Golos — keep them)
- **DESIGN ONLY via the design system.** One global source: `static/css/tokens.css` (values) +
  `static/css/components.css` (components), governed by `projectSpec/brand-book.md`. No hardcoded
  colors/sizes or one-off inline styles. Palette «Golden Hour» (warm paper bg `#FCEFDF`, espresso text
  `#3A2A1C`, denim `#3E4E78` = action/CTA, amber `#B9722A` = brand voice). 7-step font scale
  (`--fs-*`). Fonts self-hosted: Rubik (800/900 only), Inter (400/500/600), Caveat (handwriting brand
  accent only — logo + the «voice» word; sized contextually, outside the scale). Hero = full-bleed
  photo + frosted card. Copy `tokens.css`/`components.css`/`brand-book.md` from Golos verbatim, then
  only change the logo + any RU-specific copy.
- **NO hardcoded UI text** — i18n catalog only (this is DrawReport's added rule on top of Golos).
- **Prompt philosophy (§7.4):** NO Barnum statements, NO reading emotions/inner states from a drawing;
  every observation tied to a visible detail; skills-language not trait-language ("works confidently at
  large scale," NOT "isn't afraid of the page"). For "the LLM must not say X": prompt + a **programmatic
  linter + repair call**, not prompt alone. Copy Golos `pipeline/` and adapt the prompt to English
  (faithful adaptation of intent, not literal translation).
- **Child gender** only from the explicit gender field. Report name format "First L." (last initial);
  landing shows first name only.
- **Fonts self-hosted, own subsets**; `$` glyph required; after any font/report-CSS change verify the
  PDF has no fallback fonts (no Segoe/Verdana). No italics in reports.
- **Versioning:** bump minor before EVERY `git push` (`scripts/bump_version.py`); include `VERSION` in
  the same commit. Major only on explicit owner command.
- **Console/encoding:** keep scripts ASCII-safe in console output.
- **Secrets in `.env`, never committed** (`GEMINI_API_KEY`, `PAYPAL_*`, `RESEND_API_KEY`,
  `ADMIN_PASS`, etc.). Build features behind abstractions + stubs so the app runs before real creds.

## Deployment — Hetzner VPS, SHARED with another project (do not disturb it)
- Server: **root@5.78.181.152** (Hetzner). It already runs **cosmyday-api** (Python) at
  `/var/www/cosmyday-api` on **port 8001** (api.cosmyday.com). DrawReport must run **in parallel,
  isolated**:
  - Code in **`/var/www/DrawReport`** (capital); app on its **own port (8002)** (gunicorn bind 127.0.0.1:8002). Deploy kit in `drawreportDeploy/` (copy to `/var/www/drawreportDeploy`).
  - Own systemd units: **`drawreport-web`**, **`drawreport-worker`** (do not touch cosmyday units).
  - Own **nginx vhost** for `drawreport.com` (+ www); **DNS-only + Let's Encrypt** cert (certbot nginx
    plugin) for drawreport.com only. Do not modify cosmyday's vhost/cert.
  - Own **SQLite** db under `/var/www/DrawReport/data/`.
  - `deploy.sh` (git pull + deps + restart the two drawreport units) and `restart.sh` in repo root,
    mirroring Golos. Model them on Golos `deploy.sh` but scoped to drawreport units/paths.
- **System deps:** WeasyPrint needs Pango/Cairo/GDK-Pixbuf — `apt install` them on the box (document
  the exact packages in the deploy notes). Python venv per project (do not share cosmyday's venv).
- **No Vercel.** `drawreport.com` points directly at this server.

## Commands (mirror Golos; create equivalents)
```
venv\Scripts\python.exe run.py                 # dev server
venv\Scripts\python.exe worker.py [--once]     # report worker (paid -> delivered)
venv\Scripts\python.exe scripts\build_hero_image.py   # optimized hero from data/Images
venv\Scripts\python.exe scripts\build_logos.py        # optimized logos from data/Images
venv\Scripts\python.exe scripts\bump_version.py       # minor +1 before every push
release.bat "msg"                              # bump -> (export) -> commit -> push   (.\release.bat in PowerShell)
```

## Build discipline
- Follow `development-plan.md` phase by phase. **Commit at the end of each phase** with a clear message
  + version bump. **Pause and summarize for owner review at each milestone** — do not build all phases
  in one unbroken run.
- English marketing/landing copy: produce a solid **first draft adapting** the Russian intent in
  `positioning-en.md` (do NOT literal-translate). **Mark visible copy as DRAFT for owner review** — the
  owner will refine wording on the finished product, not now.
- When something is unclear, prefer the Golos implementation as the answer before inventing.

## Keep your own journals (like Golos)
Create and maintain:
- `DevelopmentStatus.md` — append-only build journal (what's done, current state, what's pending).
- `UseCasesData.md` — problem → cause → solution log (seed it from Golos's, keep DrawReport-specific ones).
Both are how the next session resumes work.
