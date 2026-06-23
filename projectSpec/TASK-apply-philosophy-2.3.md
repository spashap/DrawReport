# TASK — finish applying Philosophy 2.3 to DrawReport

Executable spec for Claude Code. Goal: bring the whole English product onto Philosophy 2.3
("portrait of the child as a person"), matching the Russian site's depth. Reference (READ-ONLY):
`C:\projects\GolosRisunka` (already implements v4.0) and `projectSpec/HANDOFF-english-philosophy-2.3.md`.

## ⚖️ Calibration decision (OWNER — overrides the handoff's "dial zone-3 down")
Keep the **Russian level of depth** in English. Do NOT suppress zone-3. Safety comes from:
1. the **airtight 4-condition safe frame** (attribution to a real tradition/author + hypothesis hedge +
   visible detail + return-to-the-child), AND
2. **prominent disclaimers** that everything interpretive is a **SUGGESTION / HYPOTHESIS grounded in the
   developmental & art literature — never a recommendation, instruction, or diagnosis.**
"Educational observation, not a diagnosis" stays ironclad; never state a child's state as fact; never
claim to detect hidden problems/traumas. (The prompt/linter already reflect this calibration.)

## ✅ Already done (by Cowork — do NOT redo; mirror/extend only)
- `pipeline/schema.py` — v4.0 fields: `about_child`, split `understanding_recommendations` /
  `art_recommendations`, `specialists`, `development_directions`, refusal branch, 7-8 dimensions.
- `pipeline/prompt.py` — `PROMPTS["en"]` rewritten to Philosophy 2.3 (`PROMPT_VERSION="en-4.0"`):
  portrait-of-child, safe frame, the new 7 directions (`world_and_themes`, `character_in_line_color`,
  `mood_and_expression`, `story_and_characters`, `creativity`, `technique_and_materials`, `fine_motor`),
  age-relative varied scoring, the "fog" mechanic, split recommendations, specialists, life-wide
  development_directions, the calibration above, new JSON shape; repair instruction = frame-check.
- `pipeline/lint.py` — frame-check model: HARD bans (wide) everywhere + frame-check (hedge/attribution/
  artifact lists) only on interpretation fields; `find_violations(report_data, locale)` signature kept.
- `pipeline/render.py` — new section headings (about_child / understanding / art / specialists /
  "Where to grow your child's strengths"); cover + disclaimer re-aligned.
- `templates/report.html` — renders `about_child`, the two recommendation sections, optional specialists.
- `static/css/report.css` — `.r-about` block style.

## ▶️ Remaining tasks

### T1 — Admin-controlled end-of-report texts (handoff §7f). Mirror Golos.
Golos reference: `config/report_texts.json`, `config/settings.py` (`get_report_texts()` + default +
mtime cache), `pipeline/render.py` (`upsell_text`/`disclaimer_text`/`free_text` params on `render_html`
+ `render_report_files`), `templates/report.html` (suffix blocks before the footer disclaimer),
`app/admin.py` + `templates/admin/report_texts.html` (editor page + sidebar nav), and the worker/job
that **picks the upsell by drawing count** and passes the texts into render.
- Create `config/report_texts.json` (English): `upsell` {1,2,3}, `disclaimer_main`, `disclaimer_by_count`
  {1,2,3}, `free_text`. English content already drafted in the "report_texts.json content" section below.
- `settings.get_report_texts()` — read JSON, mtime cache (edits visible without restart), safe default.
- `render.py` — add `upsell_text`/`disclaimer_text`/`free_text` params (mirror Golos), pass to template.
- `report.html` — render the suffix blocks (upsell, then disclaimer_main + per-count add-on, then
  free_text) just before/within the footer disclaimer. Empty string = render nothing.
- The job/worker that renders a delivered report: pick `upsell[str(n_drawings)]`, build
  `disclaimer_text = disclaimer_main + disclaimer_by_count[str(n_drawings)]`, pass `free_text`. Find the
  Golos call site and mirror it.
- Admin: `/admin/report-texts` editor (textareas, save to the JSON) + sidebar entry. Mirror Golos
  `app/admin.py:report_texts` + its template. Admin stays English-only (not localized).
- Acceptance: edit a text in `/admin/report-texts` → next rendered report shows it, no restart; empty
  fields show nothing; a 1-drawing order shows the "one moment, not the full picture" add-on.

### T2 — Landing rework to Philosophy 2.3 (front end). Spec: `positioning-en.md` + handoff §9.
`templates/landing.html` + `app/routes.py` (FAQ/meta/JSON-LD). All UI strings via i18n; copy as DRAFT.
- **Hero stays** (it was right): eyebrow "Every drawing has a voice"; H1 ≈ "Children often say in drawings
  what they can't yet put into words."; lead = personality-led + "read carefully, by the developmental
  stages of children's art".
- **What you'll learn** → personality-led (worlds & themes, character, the mood in their drawings, the
  stories/heroes that matter, how to understand & support); **skills last**.
- **How the conclusion is built** → a personality example: visible detail → gentle hypothesis → what to
  ask the child.
- **Illustrative scenarios** block (3-4 "for example, a situation like this…" cases; explicitly examples,
  never real clients; no fabricated testimonials).
- **Anti-fortune-teller** block (replaces any "we only read skills" copy): US = careful/serious, by
  methods (Piaget, Lowenfeld, Vygotsky); THEM = myths, "black = depression", fortune-telling, diagnosing
  from one photo, scaring with hidden traumas.
- **Disclaimers as positive identity**: "a tool to understand the child through their drawing — careful,
  literature-grounded suggestions and a hint, not a diagnosis and not fortune-telling." Keep "if seriously
  worried → see a professional." Word "diagnosis" only in the soft-negative.
- **Sample cards** lead with the drawing (big) + the `about_child` portrait quote + small score bars.
- Verbs allowed: reveal, show, understand, discern, help-understand, support, suggest. Banned: diagnose,
  fix/cure, predict-as-fact. Keep existing SEO keywords; blend the emotional message in.
- Acceptance: a cold visitor understands what/why from the hero; no section contradicts the new report;
  no fabricated testimonials; copy marked DRAFT.

### T3 — Regenerate sample reports (needs `ANTHROPIC_API_KEY`)
Run the new pipeline on the sample drawings; **American names**; do NOT re-render old saved JSON (new
required fields will break it — regenerate fresh). Read the outputs: safe frame present on every zone-3
sentence, `about_child` reads like a portrait, scores varied (not a wall of 9s), specialists include a
non-art option when warranted. These become the landing sample cards.

### T4 — Operational guard (handoff §11)
Ensure `pipeline/llm.py` (the Anthropic orchestrator) has a **per-request timeout (~180s)** so a hung
call aborts → retries → fails cleanly instead of wedging the worker.

### T5 — Verify + ship
- Render a full report end-to-end: PDF shows About-your-child, both recommendation sections, specialists,
  development directions, and the admin suffix blocks; **no fallback fonts** (no Segoe/Verdana); `$` ok.
- Linter: ~0 false positives on a good framed report; catches a deliberately bad string.
- Bump version, commit, append to `DevelopmentStatus.md` + `UseCasesData.md`.

## report_texts.json content (English draft — owner can tune in admin later)
```json
{
  "upsell": {
    "1": "This portrait is built from a single drawing — an honest snapshot of one moment. From one drawing it isn't possible to tell a stable trait from a particular day's mood. If you'd like to see what repeats from drawing to drawing (and what was a one-off), send 2-3 works from different days — a series makes the picture far clearer than a single sheet.",
    "2": "This portrait is built from two drawings — already enough to see what repeats and what was a one-off. A third work from another day would make the picture of stable traits even more reliable.",
    "3": ""
  },
  "disclaimer_main": "This report is an educational observation of what's visible in the drawing and a warm portrait of the child through their work. It is not a medical or psychological diagnosis: anything about mood, character, or inner world is a suggestion grounded in the developmental and art literature, best explored in conversation with the child. If you are seriously concerned about your child's wellbeing, behavior, or development, this report does not replace a consultation with a qualified professional.",
  "disclaimer_by_count": {
    "1": " Remember: this is a reading of one drawing — one moment, not the full picture of a child's development.",
    "2": "",
    "3": ""
  },
  "free_text": ""
}
```

## Reference map (Golos → mirror, adapt to English/Anthropic)
- Suffix: `config/report_texts.json`, `config/settings.py` get_report_texts, `pipeline/render.py`,
  `templates/report.html`, `app/admin.py` report_texts + `templates/admin/report_texts.html`.
- Landing: `templates/landing.html`, `app/routes.py` (FAQ/TESTIMONIALS/meta/JSON-LD).
- LLM/timeout: DrawReport `pipeline/llm.py` (Anthropic) — concept from Golos `pipeline/gemini.py` timeout.
Remember: DrawReport's LLM is Anthropic Claude via `pipeline/llm.py`; prompt/schema/lint concepts port
unchanged, only the provider call differs. Keep `C:\projects\GolosRisunka` read-only.
