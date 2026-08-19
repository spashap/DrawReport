# CLAUDE.md — DrawReport (drawreport.com)

> **⚠️ The "build it from scratch" framing below is HISTORICAL.** The build is finished and the site
> is LIVE at https://drawreport.com. `development-plan.md`, `i18n-architecture.md`,
> `build-from-golos.md` and `positioning-en.md` remain useful reference for *why* things are shaped
> the way they are — they are no longer a to-do list. Start from the AS-BUILT section immediately
> below; it overrides anything that contradicts it.

---
## ✅ AS-BUILT STATUS — updated 2026-08-18, VERSION 0.042. **The site is LIVE and taking real payments.**

Repo **https://github.com/spashap/DrawReport** (`main`). Live at **https://drawreport.com** (TLS via
Let's Encrypt). All phases M0–M9 done, plus the Golos port (phases 1–6), the freemium funnel, the
full-deploy `release.bat`, and a native-US-English copy pass.

### What is running in production right now
| | |
|---|---|
| **Host** | Hetzner `root@5.78.181.152`, shared with **cosmyday-api** (port 8001) — never touch its units/vhost/cert/venv |
| **Code** | `/var/www/DrawReport`, gunicorn on `127.0.0.1:8002`, nginx vhost `drawreport.com` (+www) |
| **Units** | `drawreport-web`, `drawreport-worker`, **`drawreport-free`** (three, all active) |
| **LLM** | Anthropic. Paid report `claude-sonnet-4-6` (fallback `claude-haiku-4-5-20251001`); **free reading `claude-haiku-4-5-20251001`** (`FREE_LLM_MODEL` — its own knob because it is a per-*visitor* cost, not a per-*sale* one) |
| **Payments** | **PayPal LIVE** (`PAYMENT_BACKEND=paypal`, `PAYPAL_ENV=live`, webhook id set). Verified read-only; **never make a test charge** |
| **Email** | **Brevo over SMTP** (`MAIL_BACKEND=smtp`, `smtp-relay.brevo.com:587`, from `team@drawreport.com`). NOT Resend — its free tier allows one domain and refused ours. A stale `RESEND_API_KEY` is still in `.env`; harmless, unused |
| **Price** | **$29**, from the git-tracked `config/products.json`. The server has **no** `data/products.json`, so `config/` is what is live (see UseCase #23) |
| **Locales** | `LOCALES=en` only. The i18n plumbing is real but the `en` catalog is empty and uncompiled, so `_('...')` returns the msgid — **English source text lives inline in the templates** |

### Shared template partials — use them, do not re-inline (added V0.040)
`landing.html` does NOT extend `_base.html`, so anything in the page frame exists in two places
and WILL drift. It already did: the footer lost its legal links on every page except `/en/report`.
These partials are the single source; include them, never copy them:
| partial | what | used by |
|---|---|---|
| `_footer.html` | brand + disclaimer + Privacy/Terms/Refunds/Blog | `_base.html`, `landing.html` |
| `_faq.html` | FAQ (copy from `app/content.py`), takes `goal_prefix` | `home.html`, `landing.html` |
| `_samples.html` | sample carousel, takes `goal_prefix` / `soft` / `heading` | `home.html`, `landing.html` |
| `_page_js.html` | carousel + `.reveal` IntersectionObserver | `home.html`, `landing.html` |
| `_header.html` | header, **burger menu and its JS live here** | every page |
**`goal_prefix` is not cosmetic**: it keeps `home_*` and `landing_*` analytics goals apart, which is
how the admin tells the two doors of the funnel apart. `.reveal` is `opacity:0` until `_page_js.html`
adds `.is-in` — a page using the class without that include renders an invisible section.

### Site shape (this is the part that differs from Golos)
- **`/` (`templates/home.html`) is the FREE-first front door** — its only job is to move the visitor
  into `/free/`. This deliberately INVERTS Golos, where the free product is demoted so it cannot
  cannibalise the paid one. Re-check that trade-off once there is organic traffic to protect.
- **`/en/report` (`templates/landing.html`) is the paid product page**, one item in the nav.
- **`/free/`** is the freemium wizard (3 questions → mirror → upload → reading), served by its own
  worker unit. Caps are admin-controlled (`daily_cap`, `per_email_daily`).
- **`/admin`** — 13 sections, ported wholesale from Golos: Tasks, Analytics, Visits, Actions, Orders,
  Clients, Coupons, Prices, Site settings, Report texts, Emails, Freemium, Beta.
- **Samples: three REAL reports** (`app/samples.py`), covering 1 / 2 / 3 drawings — the full range
  `/en/report` sells. All are unedited en-4.2 pipeline output from real children's drawings, with
  assets in `pipeline/samples/` (optimized JPEGs: `/r/<token>` embeds them as base64 data URIs).
  `sample-liam` was retired in V0.039 — its image was vector clip art, not a child's drawing — and
  its URL **301s**; do not reinstate a sample without a real drawing behind it.
- **Mobile nav**: `≤880px` hides the inline nav and shows a burger (V0.042). Before that there was
  no burger at all, so Full report / Examples / Pricing / Blog were unreachable on a phone.
- Only the **snapshot** product is enabled; `development` is disabled on purpose (Golos decision).

### Copy standard — read this before writing ANY visible English
The first English conversion was rejected by the owner as an "epic fail". `/en/` and `/en/report`
were rewritten on 2026-08-17 to native US consumer English against
`projectSpec/drawreportcopyfixtask.md`; the **rest of the site** (freemium, emails, PDF strings,
sample report, blog, legal) followed in V0.035 against
`projectSpec/DrawReport-English-Copy-Repair-Report.md`. **Verify copy on the RENDERED page, never on
the template source** (UseCase #20) — and remember one page pulls strings from five places: the
template, `app/content.py`, `config/products.json`, `config/free_texts.py`, and
`content/en/blog/*.md` front matter (UseCase #21). Avoid the tells that got flagged: Britishisms,
`and a hint`-style translation artifacts, repeated not-X/never-X contrast, em-dash density,
rule-of-three lists, and gallery vocabulary (`work`, `piece`, `the medium`, `palette`) for a
child's drawing.
⚠️ **This standard governs the WEBSITE, not generated report prose** (UseCase #30, owner decision).
Inside a report, em-dash density, "not X but Y" and occasional British spelling are ACCEPTED: it is
a personal document, nobody audits its style, and eight pages in two minutes is self-evidently
machine-assisted. Professional and readable is the bar there. Do not spend prompt text or linter
rules on report prose style, and do not "helpfully" re-fix it in a later session. Typography is curly (`’ “ ”`) and dashes are real em dashes — never a spaced
ASCII hyphen. **Copy that lives in a PROMPT is different work:** it steers the model's own English,
and if the linter matches the same phrasing it must change in both files (UseCase #24). Curly
characters bound for the PDF need a font-subset check first (UseCase #26).

### Deploy / release — ONE command
```
release.bat "message"               bump -> commit -> push -> ssh deploy -> asserting health check
release.bat "message" --no-deploy   push only (use for docs/journal-only commits)
release.bat --deploy-only           deploy what is already on GitHub
```
`deploy.sh` re-execs itself after `git pull` (it rewrites itself mid-run otherwise — UseCase in the
log). Details in `DEPLOY.md` + `drawreportDeploy/README.md`.

### 🔴 WHAT IS MISSING (verified 2026-08-18 — this is the resume list)
**Analytics & search — CONNECTED on 2026-08-18 (V0.043). Values live in the server `.env` only.**
The three ids below are NOT in git. They are public values (all three are readable in the page
source or in a DNS record), but if the server is ever rebuilt they must be put back or measurement
silently stops — `templates/_analytics.html` and `_verification.html` both render nothing when their
value is empty, and nothing anywhere warns you. `/admin/settings` shows which of the three are set;
that line is the fastest check. See `drawreportDeploy/README.md` for the values.
1. ✅ **GA4 — LIVE.** Property `DrawReport` (account `Pasha_webAnalytics`), stream
   `https://drawreport.com`, `GA_MEASUREMENT_ID=G-FBQFBZNBRC`. Verified receiving realtime hits.
   Our own first-party analytics is INDEPENDENT of this: `static/js/track.js` loads unconditionally
   and the admin funnel works with or without GA (deliberate — see `_analytics.html`).
2. ✅ **Google Search Console — verified, sitemap submitted.** DOMAIN property `drawreport.com`
   (DNS TXT, so it covers www/non-www, http/https and every subdomain — better than the meta tag,
   and it is why `GOOGLE_SITE_VERIFICATION` is still empty and should stay that way). Sitemap
   accepted: Success, 12 URLs. GA4 ↔ Search Console link created, so organic query data reaches GA4.
3. ✅ **Bing Webmaster Tools — verified, sitemap submitted.** Verified by META TAG, not by importing
   from Search Console: the import needs a Google OAuth grant that hands Microsoft read access to
   EVERY GSC property on the account (cosmyday, belgradebest, fidgetgo, shepotzvezd), where the tag
   is scoped to this site alone. `BING_SITE_VERIFICATION=CDDA90767439BEC62E04291DE51BA231`.
   ⚠️ Bing re-checks the tag: removing it un-verifies the site.
4. ✅ **DONE (V0.043) — the verification-tag mechanism.** `templates/_verification.html`, included by
   BOTH `_base.html` and `landing.html` — landing has its own `<head>`, so a head change made in one
   file only is invisible on half the site.

**SEO gaps found while auditing.**
5. ✅ **DONE (V0.043) — the sitemap lists the blog POSTS**, not just `/blog`.
6. ✅ **DONE (V0.043) — `lastmod` means something.** Posts date themselves from their frontmatter;
   the blog index is as fresh as its newest post; everything else uses `settings.SITEMAP_LASTMOD`,
   a tracked constant. **Bump `SITEMAP_LASTMOD` when public copy really changes** — that is the
   whole point of it, and leaving it stale is the opposite failure to the `today` bug it replaced.
7. ✅ **DONE (V0.043) — `/llms.txt`.** Generated, not static: price comes from `products.json`,
   samples from `app/samples.py`, articles from the blog frontmatter, so it cannot drift. Its most
   load-bearing lines are the "what this is not" ones — an assistant that repeats the boundary
   accurately does not send us a parent who wants a screening tool.
7b. ✅ **DONE (V0.043) — IndexNow, key verified and 12 URLs submitted.** `INDEXNOW_KEY` in the server
   `.env`; the key file is served at `/<key>.txt` **only when the key is set**. Submit with
   `venv/bin/python scripts/indexnow_submit.py /en/blog/<slug>` **on the server** — the script
   refuses to run when `PUBLIC_BASE_URL` is localhost, so it cannot be driven from a dev box.
   Deliberately MANUAL, not a deploy hook: IndexNow is for pages that CHANGED, and re-announcing the
   whole site on every deploy is what gets a host throttled. `--sitemap` was the one first run.
7c. 🔴 **STILL OPEN — Ahrefs Webmaster Tools and UptimeRobot.** Both are free and both need an
   ACCOUNT the owner must create personally. AWT (`ahrefs.com/webmaster-tools`) is the best free
   thing after GSC: a crawl-based site audit plus our own backlink profile, and it verifies through
   the SAME Search Console link that already exists. UptimeRobot matters because `release.bat` only
   health-checks at deploy time — nothing watches the site in between, and downtime during a crawl
   is read as a site-quality signal, not as bad luck.

**Product / business.**
8. ✅ **DONE (V0.035 + V0.036) — English pass across every copy surface.** The site (freemium
   wizard, emails, PDF strings, sample report, blog, legal) was repaired in V0.035 against
   `projectSpec/DrawReport-English-Copy-Repair-Report.md`; **`pipeline/prompt.py`, the PAID report
   prompt, followed in V0.036** (`PROMPT_VERSION` en-4.1) — language and tone only, no rule or
   safe-frame change. It gained the `HOW THE ENGLISH MUST SOUND` section it never had.
   ⚠️ Before editing either prompt, read **UseCases #24 and #27**: hedge/attribution wording is
   matched by `lint.py` / `free_lint.py`, so it changes in both files in one commit, and you assert
   the coupling both ways. **Not yet verified on live output:** no en-4.1 report has been generated,
   so read one fresh paid report against the voice rules before assuming they took.
9. **Legal pages rewritten (V0.048), STILL not reviewed by counsel.** `projectSpec/TASK-legal-pages-v1.md`
   is the spec. The public "DRAFT — to be reviewed by counsel" banner is gone from all three pages
   (announcing unfinished terms to a paying customer is a written admission), the pages now name a
   contracting party, disclose the actual processors (Anthropic, Brevo, PayPal, host), state
   retention, and Terms + Privacy + Refunds are LINKED AT CHECKOUT — before that, `order.html`
   presented no terms at all, which is the weakest possible assent. **Two things are still open:**
   the identity is env-driven and ships as literal `[FULL LEGAL NAME]` brackets until the owner sets
   `LEGAL_ENTITY_NAME` / `_ADDRESS` / `LEGAL_STATE` / `LEGAL_VENUE` in the SERVER `.env` (admin task
   `legal_identity`; `app.legal.unfilled_placeholders()` reports what is missing), and the attorney
   review (COPPA, refunds, PayPal, FTC "educational, not diagnosis") is still not booked.
   ⚠️ **Never publish a retention promise the code does not keep.** The 90-day free-photo deletion is
   real (`app/free_retention.py`, run daily by `free_worker.py`); the drafted "analytics purged at 24
   months" line was CUT because no such job exists.
10. **Blog has only 3 posts.**
12. **`insufficient_input` does not fire on non-drawings.** en-4.2 has an explicit rule to reject an
    image that is not a child's drawing; fed flat vector clip art it produced a full, confident
    report praising the "confident and direct" lines of a computer-drawn graphic. Low impact (real
    customers photograph paper), but the rejection path is weaker than the prompt claims.
13. **The materials cap is the one en-4.2 acceptance check still failing**, off by exactly one on
    both samples: the model spends one allowance inside a direction and one in `art_recommendations`,
    satisfying each rule locally. A counter in `lint.py` spanning both would close it (UseCase #29).
11. **Launch price framing undecided.** Live is a flat $29. A `$59 → $39` strike-through variant
    exists only in the local dev `data/products.json` and is NOT on the server.

**Run locally:** `venv\Scripts\python.exe run.py` (web :3000) + `worker.py` + `free_worker.py`.
Admin `/admin/login` (pass = `ADMIN_PASS`). The footer version badge shows on localhost and is
hidden in production — `settings.SHOW_VERSION`, derived from `PUBLIC_BASE_URL`.

**Resume pointers:** journal `DevelopmentStatus.md` · solved problems `UseCasesData.md` (#1–#31 —
**#24/#27 prompt↔linter coupling, #29 unenforced rules collapse on long output, #30 the two English
standards, #31 `` becomes a backspace when writing regexes programmatically**) · copy tasks
`projectSpec/drawreportcopyfixtask.md`, `projectSpec/DrawReport-English-Copy-Repair-Report.md`,
`projectSpec/TASK-paid-report-en-4.2-north-star.md` · plan `development-plan.md`.

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
  payment-provider abstraction Golos uses for its stub/ЮKassa. ✅ DONE and **LIVE** — see AS-BUILT.
- **Email:** ⚠️ specced as **Resend**; **shipped as Brevo over SMTP.** Resend's free tier allows one
  verified domain and rejected ours. `app/mailer.py` now has three backends behind one abstraction —
  `outbox` (files, dev), `smtp` (**what prod uses**, portable to any provider) and `resend`. Prefer
  `smtp`: switching providers is then an `.env` change, not a new code path.
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
- **Prompt philosophy — PHILOSOPHY 2.3 "PORTRAIT OF THE CHILD AS A PERSON" (prompt v4.0).**
  ⚠️ This OVERRIDES the old "skills-only / no emotion-reading" rule (the RU site pivoted; the build did
  NOT follow this yet — see below). Source of truth: **`projectSpec/HANDOFF-english-philosophy-2.3.md`**.
  The report reads the CHILD (character, themes, inner world, mood, interests) THROUGH the drawing;
  drawing skills are SUPPORT, not the point. Emotional/psychological interpretation (zone 3) is ALLOWED
  but ONLY inside the **4-condition safe frame** (attribution to a real tradition/author + hypothesis
  hedge + anchored to a visible detail + return-to-the-child "ask [name]…"). Always forbidden even with
  the frame: bare diagnosis-as-fact, "fix/cure", hidden-trauma claims, colour/symbol fortune-telling,
  command tone, fate-as-fact talent predictions, fake testimonials.
  **ENGLISH CALIBRATION (OWNER DECISION — overrides handoff §2's "dial zone-3 down"):** KEEP the Russian
  level of depth in English. Safety comes from (1) the airtight 4-condition safe frame AND (2) prominent
  disclaimers that all interpretation is a **SUGGESTION / HYPOTHESIS grounded in the developmental & art
  literature — never a recommendation, instruction, or diagnosis** — NOT from suppressing zone-3.
  "Educational observation, not a diagnosis" stays ironclad; never state a child's state as fact; never
  claim to detect hidden problems/traumas; wider HARD bans still apply. (prompt.py/lint.py already reflect this.)
  For "the LLM must not say X": prompt + a **programmatic linter + repair call** (now a **frame-check** —
  add the safe frame, don't delete meaning — not a blunt word-ban), not prompt alone. Mirror the RU v4.0
  implementation (`pipeline/prompt.py` PROMPT_VERSION 4.0, `schema.py`, `lint.py`), adapt to English.
  **Now at `PROMPT_VERSION = "en-4.2"`** (free prompt `1.1`). en-4.1 added the `HOW THE ENGLISH MUST
  SOUND` section; **en-4.2 is the NORTH STAR pass** (`projectSpec/TASK-paid-report-en-4.2-north-star.md`):
  activities must change something BETWEEN parent and child, materials capped at ONE per report,
  skill drills banned, every activity NAMED, directions 6-7 capped at 2 sentences, and **normality
  verdicts about the child added to ALWAYS FORBIDDEN** — a reassurance verdict is a screening claim
  and this report does not screen. ⚠️ **Before editing either prompt read UseCases #24 and #27:**
  hedge/attribution wording is ALSO matched by `lint.py` / `free_lint.py`, so it changes in both
  files in ONE commit, and you assert the coupling both ways. Rules carrying product or legal weight
  get a linter check — UseCase #29 measured a prompt-only rule holding on a short report and
  collapsing on a long one.
- **Child gender** only from the explicit gender field. Report name format "First L." (last initial);
  landing shows first name only.
- **Fonts self-hosted, own subsets**; `$` glyph required; after any font/report-CSS change verify the
  PDF has no fallback fonts (no Segoe/Verdana). No italics in reports.
- **Versioning:** bump minor before EVERY `git push` (`scripts/bump_version.py`); include `VERSION` in
  the same commit. Major only on explicit owner command.
- **Console/encoding:** keep scripts ASCII-safe in console output.
- **Secrets in `.env`, never committed** (`ANTHROPIC_API_KEY`, `PAYPAL_*`, `SMTP_PASSWORD`,
  `ADMIN_PASS`, etc.). Build features behind abstractions + stubs so the app runs before real creds.
  ⚠️ **PayPal is LIVE with real credentials** — use read-only checks; never make a test charge.

## Deployment — Hetzner VPS, SHARED with another project (do not disturb it)
- Server: **root@5.78.181.152** (Hetzner). It already runs **cosmyday-api** (Python) at
  `/var/www/cosmyday-api` on **port 8001** (api.cosmyday.com). DrawReport must run **in parallel,
  isolated**:
  - Code in **`/var/www/DrawReport`** (capital); app on its **own port (8002)** (gunicorn bind 127.0.0.1:8002). Deploy kit in `drawreportDeploy/` (copy to `/var/www/drawreportDeploy`).
  - Own systemd units: **`drawreport-web`**, **`drawreport-worker`**, **`drawreport-free`** (the
    freemium reading worker; three units in total — do not touch cosmyday units).
  - Own **nginx vhost** for `drawreport.com` (+ www); **DNS-only + Let's Encrypt** cert (certbot nginx
    plugin) for drawreport.com only. Do not modify cosmyday's vhost/cert.
  - Own **SQLite** db under `/var/www/DrawReport/data/`.
  - `deploy.sh` (git pull + deps + restart the two drawreport units) and `restart.sh` in repo root,
    mirroring Golos. Model them on Golos `deploy.sh` but scoped to drawreport units/paths.
- **System deps:** WeasyPrint needs Pango/Cairo/GDK-Pixbuf — `apt install` them on the box (document
  the exact packages in the deploy notes). Python venv per project (do not share cosmyday's venv).
- **No Vercel.** `drawreport.com` points directly at this server.

## Commands (as built)
```
venv\Scripts\python.exe run.py                 # dev server on :3000 (PORT env)
venv\Scripts\python.exe worker.py [--once]     # PAID report worker (paid -> delivered)
venv\Scripts\python.exe free_worker.py         # FREE reading worker (its own unit in prod)
venv\Scripts\python.exe scripts\build_hero_image.py   # optimized hero from data/Images
venv\Scripts\python.exe scripts\build_logos.py        # header strip + icon + favicons from data/Images
venv\Scripts\python.exe scripts\bump_version.py       # minor +1 before every push
.\release.bat "msg"                            # bump -> commit -> push -> DEPLOY -> health check
.\release.bat "msg" --no-deploy                # push only (docs/journal commits)
.\release.bat --deploy-only                    # deploy what is already on GitHub
```
Three workers/units, not two: `drawreport-web`, `drawreport-worker`, `drawreport-free`.

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
