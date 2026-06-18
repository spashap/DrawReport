# i18n architecture — DrawReport

The ONE structural difference from the Russian original: DrawReport is **multi-language from day one**,
even though only **English (`en`)** ships first. Build the whole locale layer now; adding a language
later (e.g. `es`, `de`) must be *translation + content files only — zero code changes*. Golos hardcodes
Russian everywhere; do NOT copy that habit.

## 1. Library
Use **Flask-Babel** (gettext). Add `flask-babel` + `babel` to `requirements.txt`.
- Wrap every UI string: `{{ _("Get the report") }}` in templates, `gettext("…")` in Python.
- Catalogs in `translations/<locale>/LC_MESSAGES/messages.po` (+ compiled `.mo`).
- `en` is the source/default catalog. Provide a `babel.cfg` + the standard extract/update/compile flow,
  and document it in the build journal:
  `pybabel extract -F babel.cfg -o translations/messages.pot .`
  `pybabel update -i translations/messages.pot -d translations`
  `pybabel compile -d translations`

## 2. URL strategy — locale path prefix
Serve every page under a locale prefix: `drawreport.com/en/…`, future `…/es/…`.
- Locale resolver order: **URL prefix → cookie → `Accept-Language` header → default `en`**.
- `/` (no prefix) → 302 to the resolved locale (or `/en/`).
- Set `<html lang="{{ locale }}">`, a per-locale `<link rel="canonical">`, and **`hreflang`** alternates
  for every active locale on every page. Generate a **per-locale `sitemap.xml`** (and a sitemap index).
- Implement with a Flask `url_value_preprocessor` + `url_defaults` so `url_for` auto-injects the active
  `lang`, and a `before_request` that validates/sets `g.locale` and calls Babel's locale selector.
- `robots.txt` allows all locales; block `/admin`, `/cabinet`, private report routes (mirror Golos).

## 3. Content is locale-scoped, not just UI strings
Anything a human reads is keyed by locale:
- **Blog:** `content/<locale>/blog/*.md` (Golos has `content/blog/`; namespace it by locale).
- **Products:** `config/products.<locale>.json` (or one file with per-locale `title/subtitle/features`).
  Prices/structure shared; display text per-locale.
- **FAQ / testimonials / legal:** per-locale (Python dict keyed by locale, or per-locale files). Golos
  keeps FAQ/testimonials in `app/routes.py` constants — make them `{ "en": [...], ... }`.
- **Sample reports:** stored per-locale (a sample is generated/written in its language). For `en`, reuse
  Golos sample structure with American names + English text. Hosted sample routes carry the locale.

## 4. The report itself is localized
The PDF is **generated in the target language**, so language flows through the whole pipeline:
- `pipeline/prompt.py`: the system prompt is **per-locale** (`PROMPTS["en"]`, …). The English prompt is a
  faithful *adaptation* of Golos's §7.4 philosophy (no Barnum, visible-detail-bound, skills-language) —
  not a literal translation. The 7-direction taxonomy is translated to English terms.
- The Gemini call passes the order's `locale`; the model must answer in that language.
- `pipeline/schema.py`: same structure for all locales (language-neutral keys; values are in the locale).
- `pipeline/lint.py`: the banned-phrasing linter is **per-locale** (English forbidden phrasings/command
  tone/diagnosis-talk). Each locale needs its own banned list + repair instruction.
- `report.html` / `report.css`: a locale field drives any fixed strings; currency `$`; date format via
  Babel. Fonts (Rubik/Inter/Caveat) already cover Latin — no font work for `en`. (A future CJK/Cyrillic
  locale would need a font subset for that script.)

## 5. Formatting & numbers
Use Babel for locale-aware number, currency, and date formatting (`format_currency(x, "USD", locale=…)`,
`format_date(…)`). Never hardcode `$1,234` or date strings.

## 6. Email is localized too
`mailer.py` templates (login code, report ready, payment received) live per-locale; send in the
recipient's order locale. The Resend backend doesn't change per locale — only the rendered content does.

## 7. Acceptance for "multi-language ready"
Before launch (English-only), verify the seam works by **temporarily adding a stub `xx` locale** (copy
`en`, prefix a marker) and confirming: routing, `hreflang`, content lookup, prompt selection, currency/
date formatting, and email all switch on locale with **no code edits** — only catalog/content files.
Then remove `xx`. Document this test in the journal.

## 8. Do / Don't
- DO put every visible string in a catalog or per-locale content file from the very first template.
- DO keep keys semantic (`hero.headline`) not English-as-key where it helps future translators.
- DON'T branch on `if locale == "en"` in business logic — only data/content differs by locale.
- DON'T let Claude invent the English report prompt from scratch — adapt Golos's proven prompt.
