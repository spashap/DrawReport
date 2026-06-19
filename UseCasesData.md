# Use Cases — problems met & solved (DrawReport)

Knowledge base: problem → cause → solution. One entry per case. Chronological build log lives in
`DevelopmentStatus.md`. Seeded from Golos (`C:\projects\GolosRisunka\UseCasesData.md`) — only the
cases that carry over to a Latin-script, US fork are kept, adapted for `$`/GA4/PayPal/Resend.

---

## #1 · WeasyPrint on Windows: GLib-GIO-WARNING spam (cosmetic)
**Problem:** every WeasyPrint run prints `GLib-GIO-WARNING **: Unexpectedly, UWP app … has no verbs`.
**Cause:** GTK's GIO enumerating Windows UWP app registrations; unrelated to rendering.
**Solution:** ignore (filter `grep -v GLib` in the terminal). Prod is Linux — won't appear there.

## #2 · Verify embedded PDF fonts after ANY font/report-CSS change (no fallbacks)
**Problem:** a missing glyph silently falls back to a system font (Segoe/Verdana on Windows; a
*different* random font on Linux prod — silent inconsistency).
**Detection recipe:** render the PDF, list `/BaseFont` per page via pypdf (incl. `/DescendantFonts`
for CID fonts). Every font must be a subset of Rubik/Inter/Caveat (`XXXXXX+` prefix). Any other
family = a glyph fell back. WeasyPrint 69 writes compressed object streams, so plaintext grep of the
PDF does NOT work — use pypdf. (Verified at M0: `$` is in the Inter subset, zero fallbacks.)
**Reusable principle:** the fonts subset must cover every glyph the LLM/report can emit. For `en` the
Golos Latin subset already covers ASCII + `$`; no rebuild needed. Prompt still bans emojis/exotic
symbols (arrows, checkmarks) so the model can't emit a glyph outside the subset.

## #3 · No italics anywhere in report/site CSS
**Problem:** `font-style: italic` pulls a system italic face (we host none) → fallback font in the PDF.
**Solution:** never use italics; distinguish notes by color/size. (Inherited Golos rule.)

## #4 · Prompt rules alone can't stop "inner-state language" → linter + repair pass
**Problem:** even with explicit bans, Gemini drifts into trait/emotion language (~3–6 spots/report).
**Solution (belt & suspenders):** `pipeline/lint.py` regex bans (per-locale) with allowed-context
exceptions (activities are NOT linted — they legitimately use task language). On hits, `gemini.py`
runs a cheap text-only repair call (temp 0.2): rewrite only flagged spots in skill-language, return
full JSON, re-validate + re-lint; accept only if violations decreased; max 2 rounds; a failed repair
never spoils an already-valid report.
**Reusable principle:** for any "LLM must not say X", add a programmatic post-check + targeted repair
instead of trusting the prompt. DrawReport needs its own **English** banned list.

## #5 · Inlined CSS in templates breaks Jinja auto-escape
**Problem (Golos #24):** inlining critical CSS with quotes/`url()` broke under Jinja autoescape.
**Solution:** mark inlined CSS with `| safe`, use unquoted `url()` and `/static/` absolute paths.

## #6 · i18n: never branch business logic on locale
**Problem:** `if locale == "en"` scattered in logic makes adding a locale a code change, not a content
change.
**Solution:** only data/content differs by locale (prompt, catalog, products text, email, samples).
Routing/format read `settings.LOCALES`. Acceptance test before launch: temporarily add a stub `xx`
locale (copy `en`) and confirm routing, hreflang, content lookup, prompt selection, currency/date,
email all switch with **no code edits**; then remove `xx`.

## #7 · url_for inside the locale blueprint needs the active locale injected
**Problem:** every `url_for('main.*')` would otherwise require passing `lang_code` explicitly.
**Solution:** main blueprint registered `url_prefix="/<lang_code>"`; `url_value_preprocessor` pops
`lang_code` → `g.lang_code` (404 on inactive locale); `url_defaults` re-injects it for
`endpoint.startswith("main.")`. Admin/static stay outside the locale prefix.

## #9 · Linter allowed-contexts must cover the model's natural disclaimer phrasings
**Problem:** the English linter flagged "diagnosis" in a clean sample whose conclusion read
"not a psychological diagnosis" — the allowed-context list only had "not a diagnosis", and the
80-char window substring check didn't match because "psychological" sits between "not a" and
"diagnosis".
**Solution:** add the phrasings the model actually emits to `ALLOWED_CONTEXTS["en"]`:
"not a psychological diagnosis", "psychological diagnosis", "medical diagnosis", "not a medical".
**Reusable principle:** when a banned word is also legitimate inside a negated disclaimer, whitelist
the *disclaimer phrasings the model uses*, not just the textbook negation. Verified the linter still
catches real violations (anxiety / "will become an artist" / "you must").

## #10 · i18n acceptance test: use a REAL CLDR locale code, not a fake "xx"
**Problem:** the i18n doc says "add a stub `xx` locale" to prove multi-language. Setting
`LOCALES=en,xx` 500s: Flask-Babel calls `babel.Locale.parse("xx")` which raises
`UnknownLocaleError` (xx isn't a real CLDR locale).
**Solution:** test with a real code (e.g. `LOCALES=en,es`). Verified: `/es/` renders 200,
`lang="es"`, hreflang lists en+es, content falls back to English (FAQ/testimonials/samples/
prompt/report-strings use `_loc()` fallback), sitemap includes `/es/`, and Babel formats dates
per-locale ("18 de junio de 2026" vs "June 18, 2026") — **all with no code edits**, which is the
real acceptance criterion. Adding a locale = add `LOCALES` + its catalog/content/prompt, no logic.

## #8 · Console/encoding: keep script stdout ASCII-safe
**Problem:** Windows console (cp1252) raises `UnicodeEncodeError` on non-ASCII prints.
**Solution:** keep project-script console output ASCII; write any non-ASCII to UTF-8 files/logs.

## #11 · LLM is provider-abstracted (Anthropic default, Gemini alternate)
**Decision:** the report LLM lives behind `pipeline/llm.py` (provider-agnostic orchestrator: attempts,
JSON validate, lint+repair loop, primary→fallback model) calling a provider module —
`pipeline/anthropic_llm.py` (default) or `pipeline/gemini.py`. Selected by env, matching the owner's
other US projects: `LLM_PROVIDER`, `LLM_MODEL` (claude-sonnet-4-6), `LLM_FALLBACK_MODEL`
(claude-haiku-4-5-20251001), `ANTHROPIC_API_KEY`.
**Why these choices:**
- The Anthropic provider sends **no sampling params** (no temperature/top_p) so the exact same code
  works on Sonnet/Haiku AND future Opus/Fable (those 400 on sampling params).
- Kept **manual JSON parse** (text → json.loads → `validate_report`) instead of structured outputs,
  because the schema is a union `Report | InsufficientReport` and the prompt already asks for JSON.
- Refusal (`stop_reason == "refusal"`) and empty content are raised as a failed attempt → triggers
  retry / fallback model.
**Reusable:** any new provider = a module with `generate(system, image_jpegs, user, model)` and
`generate_text(prompt, model)`; register it in `llm._provider()`. When editing LLM code, consult the
`claude-api` skill (don't guess model ids/params).

## #12 · Carousel must be FINITE for a small site (don't clone for "infinite" scroll)
**Problem:** the Golos landing carousel cloned each card ×3 for an infinite-scroll effect. Golos had
14 blog posts so clones stayed off-screen; DrawReport has 1 sample + 3 posts, so the clones were
fully visible — duplicate cards, and the dot count looked wrong.
**Solution:** finite carousel in `landing.html` — no cloning, **one dot per real card**, arrows hidden
when nothing overflows. Dots always equal the sample/blog count.

## #13 · OG/social image = JPG from the hero, not a 1 MB PNG
**Problem:** a photographic 1200×630 OG saved as PNG was ~1 MB.
**Solution:** crop/resize the hero to 1200×630 and save **JPEG q82** (~114 KB) → `static/img/og-default.jpg`;
point all refs at `.jpg` (base/landing/sample/blog/_seo_jsonld/routes `_schema_jsonld`).
`build_og_image.py` (text-card fallback) also emits `.jpg`.

## #14 · Hero/logo are built by host scripts from data/Images (gitignored source)
Owner drops art in `data/Images/` (gitignored); `scripts/build_hero_image.py` reads
`data/Images/Hero.png` → `static/img/hero.{jpg,webp}` (1600×900) + `hero-800.{jpg,webp}` (960×540);
`scripts/build_logos.py` reads `stripLogo.png`/`logo.png`. The optimized `static/img/*` ARE committed.
Per-blog-post SVG thumbnails live in `templates/_blog_thumb.html` (one `{% elif slug == %}` per slug,
colored via palette `var(--*)`; default fallback for new posts).

## #15 · Deploy: capital path, port 8002, LF line endings, registrar DNS
- Server project dir is **`/var/www/DrawReport`** (capital D/R, matches the repo name). Local dev port
  **3000** (`PORT` env), prod gunicorn **127.0.0.1:8002**. systemd units `drawreport-web`/`drawreport-worker`.
- Deploy kit in **`drawreportDeploy/`** (copy to server `/var/www/drawreportDeploy`, run `provision.sh`).
  `provision.sh` git-pulls into `/var/www/DrawReport` WITHOUT clobbering the owner-placed `.env`.
- **`.gitattributes` forces `eol=lf` on `*.sh/*.service/*.conf`** so the scripts run on Linux after
  being copied from Windows. (Note: `grep -c $'\r'` in Git Bash mis-reports — verify CRLF with Python
  `b.count(b'\r')`, not grep.)
- **DNS at the registrar, no Cloudflare** (or grey-cloud only). The orange proxy breaks `certbot`
  HTTP-01 and rewrites robots.txt / 403s crawlers (the exact Golos pitfall). TLS = `certbot --nginx`.
