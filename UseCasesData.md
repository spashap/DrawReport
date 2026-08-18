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

## #16 · Admin-controlled end-of-report texts (upsell/disclaimer by drawing count)
Problem: the report's closing upsell + disclaimers must be owner-editable without a deploy, and the
upsell/disclaimer must vary by how many drawings the order had. Solution (mirror Golos): a single
`config/report_texts.json` read via `settings.get_report_texts()` (mtime cache → edits live without a
restart; safe empty defaults if the file is missing/corrupt). The worker (`app/jobs.py`) selects by
`min(len(rows),3)`: `upsell[n]`, `disclaimer_main + disclaimer_by_count[n]`, `free_text`, and passes
them into `render_report_files(...)`. The template gates each block (`{% if %}`) so empty = nothing
rendered. Edited at `/admin/report-texts` (pass-through write, no business logic in the route).

## #17 · Regenerate samples after a schema change — never hand-edit old JSON
Problem: a schema/philosophy change makes the shipped sample JSON invalid (the old `sample_report.json`
had no `about_child`, used `recommendations` not the split fields, and old dimension keys → fails the
v4.0 validator). Solution: regenerate fresh from a real drawing via
`scripts/generate_report.py data/test_drawing.png --context CTX.txt --common COMMON.txt -o OUTDIR`
(needs `ANTHROPIC_API_KEY`), QA the output (safe frame on every zone-3 sentence, portrait `about_child`,
varied non-flat scores, a non-art specialist only when warranted), then copy `report.json` →
`pipeline/samples/sample_report.json` and the drawing → `pipeline/samples/`, and point `_SAMPLE_DEFS` +
`scripts/render_sample.py` at it. Landing sample cards lead with the `about_child` portrait quote
(`app/samples.py` falls back to `conclusion` for old JSON).

## #18 · Verify "no fallback fonts" by decompressing the PDF, not a plaintext grep
WeasyPrint packs font objects into FlateDecode streams, so `grep /BaseFont` on the raw PDF finds
nothing. To confirm only the self-hosted subsets are embedded: zlib-decompress each `stream…endstream`
and regex `/BaseFont /([A-Za-z0-9+\-]+)`. A clean report shows only `*+Caveat-*`, `*+Inter*`,
`*+Rubik-*` (random subset prefixes) and no Segoe/Verdana/Arial/Times/DejaVu/Calibri.

## #19 · Anthropic call needs an explicit per-request timeout
The SDK `messages.create(...)` has no short default wall-clock cap; a hung request can wedge the
worker. Pass `timeout=180` on every call in `pipeline/anthropic_llm.py` (both the image and the
text-repair calls). The orchestrator (`pipeline/llm.py`) already treats any exception as a failed
attempt with backoff → retry → model fallback, so a timeout fails cleanly.

## #20 · Verify copy on the RENDERED page, never on the template sources
A copy audit counted "25 straight apostrophes" on `/en/report`, but grepping the templates found
far more - because Jinja msgids written as `_('...')` must escape an inner apostrophe as `child's`,
which RENDERS as a straight `'`. Source counts and rendered counts are different numbers and only
the rendered one is what a reader sees. The check that works: `create_app().test_client().get(url)`,
strip `<script|style|head>`, strip comments, strip tags, unescape entities, then count. Same
technique catches copy that lives outside the two templates entirely - blog front matter, product
feature bullets, FAQ constants - all of which surfaced only once the page was rendered.

## #21 · A "public page" copy fix reaches further than the page's own template
`/en/report` renders strings from FIVE places: `templates/landing.html`, `app/content.py`
(FAQ + scenarios), `config/products.json` (pricing-card features), `content/en/blog/*.md`
(front matter, via the carousel) and `config/free_texts.py` (shared with the free wizard).
Editing only the template leaves the audit failing on phrases that are demonstrably on the page.
Grep the rendered text for each remaining hit and follow it back to its source.

## #22 · Do not show the build version in a production footer
`V0.0xx` under the disclaimer reads to a visiting parent as unfinished software. Gate it on
`settings.SHOW_VERSION`, DERIVED from `PUBLIC_BASE_URL` containing localhost/127.0.0.1 rather
than configured - a flag someone has to remember to flip is a flag that ships wrong. `SHOW_VERSION=1`
in `.env` forces it back on when debugging a live box.

## #23 · `data/products.json` may not exist on the server - config/ is what is live
Prices and pricing-card copy have the same two-file split as everything else (tracked
`config/products.json` = default, gitignored `data/products.json` = admin edits). The local dev box
had a `data/` copy at $39/$59 while the SERVER had none, so production was serving the $29 from
`config/`. Before assuming a copy fix in `data/` will ship, check which file the target box actually
has: `ssh ... cat /var/www/DrawReport/data/products.json`.

## #24 · A prompt phrasing change is a LINTER change, or the repair loop eats the release
`pipeline/free_prompt.py` told the model to hedge with "may speak of" and to attribute with
"in the tradition of reading children's drawings". Both are calques, and because they were the
*preferred* forms they appeared near-verbatim in every reading - the single loudest "this was
translated" signal in the product. But `pipeline/free_lint.py` checks the SAME two lists
programmatically: `_check_hypothesis` requires a hedge matching `HEDGE["en"]` in
`hypothesis.phrase`, and requires `FREE_ATTRIBUTION` to match when the interpretation key has no
source in the dictionary. Swapping the prompt's wording alone would mean every correctly framed
hypothesis fails the lint, burns a repair call, and comes back re-worded into the old calque -
i.e. the fix would silently undo itself AND cost a paid call per reading.
The fix ships as one commit: new hedges (`may point to`, `often goes with`, `can be a sign that`,
`reads like`) added in a dedicated `FREE_PHRASE_HEDGE` used by `_check_hypothesis`, and the new
generic attributions (`people who study children's drawings...`, `in the research on children's
drawings...`, `one common reading of this is...`) added to `FREE_ATTRIBUTION` - which
`drop_hypothesis` also uses, so a smuggled attribution is still strippable. The test that proves
it: build a `FreeAnalysis` in the new voice and assert `find_free_violations(...) == []`.
**Rule: prompt wording that the linter also matches is one artifact in two files. Change both, and
prove it with a round-trip, before deploying.**

## #25 · Three word budgets, none of them agreeing, is what "clipped, translated" text is made of
The free prompt asked for `300-390 words, never more than 400`; `free_schema.py` computed the sum
of its own per-block targets as `255-360`; `FREE_MAX_WORDS` was `420`; and the block-2 header said
`60-90` while the JSON contract for the same block said `80-120`. The model pads to clear a floor
it cannot reach honestly (filler sentences) AND compresses to stay under a ceiling it keeps hitting
(dropped articles, stacked clauses) - which are exactly the two failure modes that read as
machine-translated English. Reconciled to `260-360 / never more than 420` in the prompt, `80-120`
in both places for block 2, an explicit "do not pad to reach the range - if the page gives you less,
write less", and a comment on `FREE_MAX_WORDS` naming the other place the number is stated.
**When output quality looks like a style problem, check whether the constraints contradict each
other first - the model is often just obeying two rules at once.**

## #26 · Curly typography in a PDF string is a FONT question, not a taste question
Converting the report's straight `'` to `’` looks like pure copy-editing, but the report PDF is
built from self-hosted, subsetted fonts (Rubik / Inter / Caveat) - and a subset that lacks U+2019
silently falls back to a system font, which is the exact defect `CLAUDE.md` forbids. Check before
converting, do not assume: read the cmap with fontTools and assert the codepoints are present
(`’ “ ” — – $ … ·` all are, in all seven faces). Then verify on the OUTPUT, not the input: render
the sample and read `/BaseFont` off every page - `Caveat / Inter / Rubik` only, no Segoe or
Verdana, and the extracted text still contains the curly characters.

## #27 · A frame the prompt OFFERS but the linter cannot SEE burns a paid call, silently
Found while applying #24 to the paid prompt. `pipeline/prompt.py` had, since en-4.0, offered two
generic name-free attributions as a valid safe frame. One of them —
`"in the practice of reading children's drawings this is sometimes read as…"` — was **never matched
by `ATTRIBUTION` in `pipeline/lint.py`**: that regex keys off `tradition|approach|<author name>|
according to`, and this phrase contains none of them. So a model that obeyed the prompt exactly,
picked that form, and attached it to a HEAVY term produced a report that `_frame_scan` reported as
unframed. The report was correct; the linter could not tell. Cost: one repair call per occurrence,
and the repair — told to "ADD the frame" — rewrites the sentence into the phrasing the regex *does*
know, so the output silently converges on the one stock phrase the copy audit later flagged.
Nothing ever surfaced, because a repaired report still ships.
**The check that finds this class of bug takes three lines and belongs in every prompt edit:**
assert that every hedge/attribution the prompt offers is (a) actually present in
`system_prompt()` and (b) matched by the regex the linter uses. Both directions matter — (a) catches
a linter that has drifted ahead of the prompt, (b) catches a prompt that has drifted ahead of the
linter. Related: [[#24]], which is the same coupling in the FREE pipeline.

## #28 · Look for the prompt line behind a bad phrase in the OUTPUT, not for a better adjective
When shipped copy reads as machine-written, the instinct is to edit the copy. For anything the model
wrote, that fixes one instance and leaves the generator untouched. `pipeline/samples/sample_report.json`
is real output of `pipeline/prompt.py`, so every tell in it is traceable evidence:
`"small but real authorial decisions"` <- the prompt's `"authorial solutions"`;
`"follows a familiar template"` x2 <- `"departures from the template"`;
`"or engineering, as examples."` x2 <- an ALLOWED example that ended `"…as examples."`;
`"The overall register of this drawing"` x2 <- `"emotional register"` in the zone list.
Four defects, four prompt lines, none of them a matter of taste. **Grep the generated artifact for
the phrase, then grep the prompt for its source; if the source is there, fix the prompt — the copy
edit is only cleanup of the samples already shipped.**

## #29 · A prompt rule with nothing enforcing it holds on short output and collapses on long output
Measured, not theorised. Two reports generated the same day from the same prompt (en-4.1), which
says "at most two dashes in the whole report": **1 em dash in the 1,538-word report, 58 in the
3,465-word one.** Same rule, same model, same hour. The dashes themselves do not matter - report
prose style is accepted by owner decision (see #30) - but the pattern generalises to every rule in
the prompt, including the ones that carry product and legal weight.
en-4.2 acted on it: skill drills and normality verdicts moved into `pipeline/lint.py` as mechanical
checks feeding the existing repair pass, and both immediately caught real defects in already-shipped
output (`bead-stringing` / `playdough` / `dot-to-dot` / `mazes` in direction 7 of both reports, and
`"a normal and healthy part of..."` in Alisia's about_child).
The rules left in prompt text alone behaved exactly as this use case predicts - they held partially:
activities named 100% on the short report and 75% on the long one; the materials cap held inside a
direction and inside art_recommendations *separately*, so both reports spent it twice; the
NO RECYCLING rule did not take at all (`hair` 16 -> 22 occurrences).
**Rule of thumb: if you would be unhappy to find a rule violated in a shipped report, it needs a
check in `lint.py`. If you would merely wince, prompt text is enough.**

## #30 · Two different English standards, and they are not in conflict
The strict native-US-English standard (UseCase #20-#21, V0.032/V0.035) applies to the **website
front end** - pages that are crawled, scanned, compared with competitors, and read by someone
deciding whether to trust us with $29.
It does **not** apply to **generated report prose**. Owner decision, and the reasoning is sound: a
report is a personal document, nobody audits its style, and eight pages produced in two minutes is
self-evidently machine-assisted. Em-dash density, "not X, but Y", occasional British spelling and
sentence-shape repetition are all ACCEPTED inside a report. Professional and readable is the bar.
Do not spend prompt text, linter rules, or review effort on report prose style - and do not
"helpfully" re-fix it in a later session. What the report is judged on is WHAT IT TALKS ABOUT: the
child rather than the drawing. Related: [[#29]], [[#31]].

## #31 · `` written through a non-raw Python string becomes a BACKSPACE, silently
Hit while adding regex rules to `pipeline/lint.py` from a generator script. In a non-raw Python
string `"\s"` is an unknown escape - Python keeps it as backslash-s and emits a SyntaxWarning - but
`""` is a KNOWN escape and becomes ``, with no warning at all. The rule tables therefore
landed in the file as `r"origami|..."`, which reads correctly in an editor because the
control character is invisible, compiles fine, imports fine, and matches NOTHING.
Every new rule silently did nothing; the test suite is the only reason it surfaced.
**Two habits that catch it:** write generated regexes with a raw string in the generator too, and
after any programmatic edit run
`[hex(ord(c)) for c in open(f, encoding="utf-8").read() if ord(c) < 32 and c not in "	
"]`
- it should be empty. The repair is a one-liner: replace `` with the two characters ``.
And never trust "it compiled" as evidence that a regex edit worked - assert on a match.
