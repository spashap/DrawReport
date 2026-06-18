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

## #8 · Console/encoding: keep script stdout ASCII-safe
**Problem:** Windows console (cp1252) raises `UnicodeEncodeError` on non-ASCII prints.
**Solution:** keep project-script console output ASCII; write any non-ASCII to UTF-8 files/logs.
