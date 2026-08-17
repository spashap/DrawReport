# DrawReport — English Copy Repair Report

**Date:** 2026-08-17 · **Repo state audited:** `main` @ `e0c2a39` (V0.034) · **Mode:** review only — no source file was modified, nothing was committed.

## How to use this document

Every finding has the same shape:

```
### F-NNN `path/to/file:LINE`
- Severity / Type
- CURRENT:      <text exactly as it appears in the file>
- REPLACE WITH: <drop-in replacement>
- Why:          <one line>
```

`CURRENT` is quoted **verbatim from the source**, including straight vs. curly apostrophes and any Jinja wrapper, so it can be found by exact search. Line numbers are from the audited commit; if the file has moved since, search the `CURRENT` string instead.

**Severity**

| | |
|---|---|
| **must-fix** | An actual error, a Britishism, or a phrase no US native produces. A reader notices. |
| **should-fix** | Reads as translated or machine-written. Costs trust rather than comprehension. |
| **optional** | Style, consistency, tone. Apply if you agree with the direction. |

**Apply order that wastes the least effort:** §0 (global sweeps, mechanical) → §1 (freemium — the surface the owner flagged) → §2 (public pages) → §3 (emails + PDF) → §4 (blog + legal).

## Scope

| Audited | Not audited |
|---|---|
| `/` home, `/en/report` landing, `/free/*` wizard + result, order / cabinet / login / sample / blog / error templates | Admin UI (13 sections, internal only) |
| `config/free_texts.py` — the pre-written interpretation library | Code comments and docstrings (not visitor-facing) |
| `pipeline/free_prompt.py`, `pipeline/free_schema.py` — what makes the *generated* free reading sound translated | Variable names, log messages, validator strings |
| `app/content.py` FAQ + scenarios, `config/products.json`, `app/samples.py`, `pipeline/samples/sample_report.json` | `pipeline/prompt.py` (paid report prompt) — same treatment recommended as a follow-up |
| 7 transactional emails, `pipeline/render.py` REPORT_STRINGS, `config/report_texts.json` | |
| 3 blog posts (front matter + body), `app/legal.py` privacy / terms / refund | |

## What the audit found, in one paragraph

The English is not broken — it is *translated*. The dominant patterns are (1) Russian abstract-noun constructions carried over intact (`what stands behind it`, `from work to work`, `in the tradition of reading children's drawings`, `a direction is less visible in the chosen subject`), (2) art-gallery vocabulary applied to a six-year-old's drawing (`work`, `piece`, `the medium`, `palette`, `graphic skills`, `authorial decisions`), (3) the not-X-but-Y contrast used as a default sentence shape — it appears in the templates, in the sample report, in the blog posts, **and in the prompt itself**, which is why it comes back in every generated reading, and (4) mechanical inconsistency the V0.032 copy pass fixed on `/en/` and `/en/report` but nowhere else — straight apostrophes, ASCII hyphens standing in for em dashes, and British spellings that survive in the freemium prompt. The single highest-leverage change in the whole report is **F-119** (a real English-voice section in `free_prompt.py`), because it governs text no template can fix.

## Counts

| Section | entries | must-fix | should-fix | optional |
|---|---|---|---|---|
| §0 Global sweeps | 7 | 5 | 1 | 1 |
| §1 Freemium (free_texts, free_keys, /free/ templates, prompt) | 117 | 34 | 70 | 13 |
| §2 Public pages (home, landing, FAQ, products, sample, forms) | 101 | 10 | 68 | 23 |
| §3 Emails + PDF report strings | 39 | 5 | 30 | 4 |
| §4 Blog + legal | 43 | 3 | 30 | 10 |
| **Total** | **307** | **57** | **199** | **51** |

A few entries are batch fixes (a table of related lines, or a whole-file sweep such as F-002 and F-003), so the number of individual edits is somewhat higher than the entry count.

---

# §0 — Global sweeps

These are mechanical and cheap. Do them first: several later findings become no-ops afterwards.

### F-001 `templates/_base.html:49` **and** `templates/landing.html:327`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `{{ _('Educational observation, not medical or psychological diagnosis') }}`
- **REPLACE WITH:** `{{ _('Educational observation, not a medical or psychological diagnosis') }}`
- **Why:** Missing indefinite article — the classic Slavic-language omission — sitting in the footer of every page on the site. It must be changed in **both** files: `landing.html` carries its own `<head>` and footer and does not extend `_base.html`.

### F-002 — apostrophe typography, whole-repo sweep
- **Severity:** must-fix · **Type:** error
- **Files and current counts** (straight `'` vs curly `’`):

| File | straight | curly |
|---|---|---|
| `config/free_texts.py` | 56 | 3 |
| `pipeline/samples/sample_report.json` | 47 | 0 |
| `app/legal.py` | 16 | 0 |
| `pipeline/render.py` | 16 | 0 |
| `content/en/blog/is-a-childs-drawing-a-diagnosis.md` | 15 | 6 |
| `templates/email/report_ready.html` | 10 | 0 |
| `content/en/blog/what-you-can-learn-from-a-drawing.md` | 9 | 1 |
| `content/en/blog/my-child-only-draws-in-black.md` | 7 | 0 |
| `config/report_texts.json` | 6 | 0 |
| `templates/email/*.html` (others) | 15 | 0 |

- **Fix:** convert every apostrophe and quotation mark in these files to curly (`’ “ ”`), matching what V0.032 already did for `/en/` and `/en/report`.
- **Why:** The pages that got the copy pass render curly, everything else renders straight, so a visitor moving from the landing page into the free wizard or a blog post sees the typography change under them. In `sample_report.json` the mix is visible *within one page*, because the page frame is curly and the report body is straight. Curly quotes need no JSON escaping, unlike `\"`.

### F-003 — ASCII hyphen used as an em dash, whole-repo sweep
- **Severity:** must-fix · **Type:** error
- **Where:** `config/free_texts.py` (lines 103, 112, 147, 154, 167, 188, 216, 221, 258, 264, 291, 293, 303, 344, 352, 355, 359, 360, 367, 405), `config/report_texts.json` (3, 4, 9), `templates/email/_email_base.html:14`, `templates/email/insufficient.html:14`, `templates/email/payment_received.html:6,11`, `app/mailer.py:189,197`, `config/form_fields.py` (16, 22, 31, 39, 51, 54).
- **Fix:** replace ` - ` with ` — ` (em dash, no surrounding spaces is also acceptable house style) **or** recast as a comma / period. Prefer recasting where the sentence already has a dash — the site's own copy standard flags em-dash density.
- **Why:** A spaced ASCII hyphen is not US punctuation; it reads as a typo. V0.032 removed every one of these from `/en/` and `/en/report` and verified it on the rendered page — the same sweep was never run on the freemium, email or report strings.

### F-004 — British spellings inside the freemium prompt
- **Severity:** must-fix · **Type:** britishism
- **Where:** `pipeline/free_prompt.py` — `colour` (30, 34, 74, 167, 193), `colours` (36), `colourful` (74, 193), `coloured` (163), `moustache` (74, 193), `analyse` (172), `analyses` (117), `centre` (145), `Analyse` (276); `config/free_keys.py` — `centres` (55).
- **Fix:** color / colors / colorful / colored / mustache / analyze / analyzes / center / centers.
- **Why:** These strings are pasted into the model's prompt immediately before it writes. The two words `American English` on line 175 are the only counterweight, and they lose: the model mirrors the spelling it just read. `free_prompt.py:276` is the literal last sentence of every request, so its `Analyse` has maximum priming effect.

### F-005 `config/free_texts.py:257`
- **Severity:** must-fix · **Type:** britishism
- **CURRENT:** `NO_DRAWING_TITLE = "No drawing to hand?"`
- **REPLACE WITH:** `NO_DRAWING_TITLE = "No drawing handy?"`
- **Why:** `to hand` is the exact Britishism the V0.032 pass caught and fixed on the home page — it survives here, on a heading in the free funnel. (The same phrase in the comment on line 253 and the docstring at `app/mailer.py:187` is internal and can be left alone.)

### F-006 — "work" / "piece" for a child's drawing
- **Severity:** should-fix · **Type:** translationese
- **Where:** `config/free_texts.py` (222, 224, 226, 235, 248), `config/report_texts.json` (3, 4, 7), `pipeline/render.py:76`, `pipeline/samples/sample_report.json` (multiple).
- **Fix:** use `drawing`, `picture`, or `page` throughout.
- **Why:** `работа` translates to *work*, and *work* / *piece* in English is gallery vocabulary. A US parent says "the drawing" or "the picture." Individual instances are itemized in their sections; this entry is here so the sweep can be done once.

### F-007 — the free CTA tells the visitor to do the reading
- **Severity:** optional · **Type:** microcopy
- **Where:** `templates/home.html:44` and `:113`, `templates/_header.html:26`, `templates/landing.html:216` and `:279`, `config/free_texts.py:371`.
- **CURRENT:** `{{ _('Read a drawing free') }}` (and `UPLOAD_BUTTON = "Read this drawing"`)
- **REPLACE WITH:** `{{ _('Get a free reading') }}` (and `UPLOAD_BUTTON = "Get my reading"`)
- **Why:** The imperative assigns the action to the parent, but *we* do the reading. Decide once and make all six match — right now the same click is labelled three different ways.

---

# §1 — Freemium

The surface the owner flagged. It splits in two: **§1a–§1c** are fixed strings the server writes (deterministic — fixing them fixes them everywhere), and **§1d** is the prompt, which governs the *generated* reading and is where the "AI-generated text" complaint actually originates.

## §1a — `config/free_texts.py`, the pre-written interpretation library

This is the file the owner asked about specifically. It is the single largest concentration of translated-sounding English in the repo, because it was adapted from the Russian original paragraph by paragraph and has never had a native pass.

### F-010 `config/free_texts.py:44-48` — `possessive()`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `    return name + ("'" if name.endswith("s") else "'s")`
- **REPLACE WITH:** `    return name + "’s"`
- **Why:** This renders in `SELLING_TITLE`, `RESULT_CTA_BUTTON`, `SUMMARY_TITLE` and `LIMIT_CTA`, so `Lucas` becomes `Lucas'` — the AP newsroom convention, which US consumer writing does not use for names. Chicago (and every parent) writes `Lucas’s`. The straight apostrophe is also covered by F-002.

### F-011 `config/free_texts.py:61`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `BAND_LABELS = {b["key"]: f"{b['label']} years old" for b in AGE_BANDS}`
- **REPLACE WITH:** `BAND_LABELS = {b["key"]: f"ages {b['label']}" for b in AGE_BANDS}`
- **Why:** This value is substituted into `NEUTRAL_PATH[2]`, which renders as "At 3-4 years old the drawings can already be looked at…" — the age phrase attaches to *the drawings*, not the child. "At ages 3–4, the drawings…" reads correctly. (Use an en dash in the band labels on lines 55-58 while you are there.)

### F-012 `config/free_texts.py:81`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `{"key": "monsters", "label": "Draws monsters, weapons, fights, frightening scenes"},`
- **REPLACE WITH:** `{"key": "monsters", "label": "Draws monsters, weapons, fights, scary scenes"},`
- **Why:** `frightening` is the register of a clinical intake form; a US parent picking a button says *scary*. The file's own comment (line 127) argues that "frightening" is a judgment rather than an observation — the mirror was fixed accordingly, but the button the parent actually taps was not.

### F-013 `config/free_texts.py:88`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `{"key": "pressure", "label": "Presses hard, scribbles over, tears the paper"},`
- **REPLACE WITH:** `{"key": "pressure", "label": "Presses hard, scribbles over the drawing, tears the paper"},`
- **Why:** `scribbles over` is transitive in English and has no object here, so the list reads as "scribbles over [something]… tears the paper". The mirror on line 136 already supplies the object; the button should match it.

### F-014 `config/free_texts.py:96`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `DURATION_QUESTION = "How long have you been noticing this?"`
- **REPLACE WITH:** `DURATION_QUESTION = "How long has this been going on?"`
- **Why:** *Notice* is punctual in English, so the progressive is unidiomatic — you notice something once, you don't spend weeks noticing it.

### F-015 `config/free_texts.py:97`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `DURATION_QUESTION_STOPPED = "How long has {sub} barely been drawing?"`
- **REPLACE WITH:** `DURATION_QUESTION_STOPPED = "How long has it been since {sub} drew much?"`
- **Why:** "How long has she barely been drawing?" is not a sentence a native produces — *barely* cannot sit under *how long* like that.

### F-016 `config/free_texts.py:100-103`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `    {"key": "days", "label": "a few days"},`
- **REPLACE WITH:** `    {"key": "days", "label": "A few days"},`
- **Why:** These four options render as buttons in the same wizard as the `CONCERNS` list, which is capitalized. Capitalize all four (and the override on line 108) or the step looks half-finished.

### F-017 `config/free_texts.py:103`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    {"key": "always", "label": "a long time - it's just how {sub} draw{s}"},`
- **REPLACE WITH:** `    {"key": "always", "label": "A long time — it’s just how {sub} draw{s}"},`
- **Why:** Hyphen-as-dash (F-003) plus straight apostrophe (F-002) in a string on a tappable button.

### F-018 `config/free_texts.py:112`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `FREE_TEXT_QUESTION = "What have you noticed in {poss} drawings? One line - or skip it."`
- **REPLACE WITH:** `FREE_TEXT_QUESTION = "What have you noticed in {poss} drawings? A line or two, or skip it."`
- **Why:** "One line - or skip it" is a telegraphic fragment held together by a hyphen; "a line or two" is what a person writing a form label says.

### F-019 `config/free_texts.py:113`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `FREE_TEXT_PLACEHOLDER = "For example: three weeks of drawing only with a black pen"`
- **REPLACE WITH:** `FREE_TEXT_PLACEHOLDER = "For example: three weeks of nothing but a black marker"`
- **Why:** "three weeks of drawing only with a black pen" is a nominalized construction, and US kids draw with markers and crayons — *pen* is the Russian «ручка» default.

### F-020 `config/free_texts.py:115`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `ADDRESS_QUESTION = "How should we refer to your child?"`
- **REPLACE WITH:** `ADDRESS_QUESTION = "Which word should we use for your child?"`
- **Why:** *Refer to* is administrative register on the friendliest screen in the funnel, and the three options underneath are literally she / he / they.

### F-021 `config/free_texts.py:131`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `    "monsters": "your child draws monsters, weapons, fights",`
- **REPLACE WITH:** `    "monsters": "your child draws monsters, weapons, and fights",`
- **Why:** This is substituted into "You’ve noticed that …", so the asyndetic list ends a sentence without a conjunction and reads as truncated.

### F-022 `config/free_texts.py:132`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "alone": "your child draws themselves alone, without other people",`
- **REPLACE WITH:** `    "alone": "your child draws themselves alone, with no one else in the picture",`
- **Why:** `without other people` is a literal rendering of «без других людей»; the English idiom names where the people aren't.

### F-023 `config/free_texts.py:133-134`
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `    "faceless": "people in the drawings come out without faces or without hands, "
                "just outlines",`
- **REPLACE WITH:** `    "faceless": "the people in the drawings don’t have faces or hands, "
                "just outlines",`
- **Why:** "come out without faces" is «получаются без лиц» word for word, and the doubled `without` is the Russian construction too. Note this mirror does not say "your child" while the other six do, which makes the sentence read as though the drawings did it by themselves.

### F-024 `config/free_texts.py:136`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "pressure": "your child presses hard on the pencil, scribbles over the drawing "
                "or tears it",`
- **REPLACE WITH:** `    "pressure": "your child presses down hard, scribbles over the drawing "
                "or tears it",`
- **Why:** "presses hard on the pencil" describes the pencil; English says the child presses down hard. Keep the `or` — the file's comment on lines 121-125 is right that turning it into `and` would put a claim in the parent's mouth.

### F-025 `config/free_texts.py:145-148` — age anchor 3-4
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `    "3-4": "At three and four the hand is still learning to steer the tool, and drawing "
           "is largely an exploration of the mark rather than a picture of something. A "
           "closed shape, a change of direction, coming back to something already drawn - "
           "at this age those are notable events.",`
- **REPLACE WITH:** `    "3-4": "At three and four, a child’s hand is still learning to steer the crayon, and "
           "drawing is mostly about making marks rather than making a picture of something. "
           "Closing a shape, changing direction, going back to something already drawn — at "
           "this age, those are a big deal.",`
- **Why:** "the hand" as a free-floating body part and "an exploration of the mark" are both source-language constructions; "notable events" is a phrase from a research abstract, not something you say to a parent about a four-year-old.

### F-026 `config/free_texts.py:149-151` — age anchor 5-6
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `    "5-6": "At five and six the same child can use color, line and the ways of drawing "
           "{sub} already know{s} very differently from one drawing to the next. What is "
           "settled and what is incidental are still easy to mix up here.",`
- **REPLACE WITH:** `    "5-6": "At five and six, the same child can use color, line, and the tricks {sub} "
           "already know{s} completely differently from one drawing to the next. At this "
           "age it’s still easy to mistake a one-off for a habit.",`
- **Why:** The first sentence puts 14 words between subject and adverb and cannot be parsed on one pass; "the ways of drawing they already know" is «способы рисования» rendered literally; "what is settled and what is incidental" is two abstractions where English names the concrete confusion. This is the age band most parents land on.

### F-027 `config/free_texts.py:152-154` — age anchor 7-9
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "7-9": "At seven to nine a child builds a system of their own: how to set up a scene, "
           "where the ground goes, how to show what is happening. The choices get more "
           "deliberate and show more - but so do the demands the child makes of themselves.",`
- **REPLACE WITH:** `    "7-9": "Between seven and nine, a child works out a system of their own: how to set up "
           "a scene, where the ground line goes, how to show what’s happening. The choices get "
           "more deliberate — and so does how hard they are on themselves.",`
- **Why:** "The choices get more deliberate and show more" leaves *show more* with no object, and "the demands the child makes of themselves" is a nominalized calque of «требования к себе».

### F-028 `config/free_texts.py:155-158` — age anchor 10-12
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "10-12": "At ten to twelve a child starts seeing the world realistically and comparing "
             "the drawing with what they intended. This is often the age when an inner "
             "critic appears, and \"it won't come out the way I want\" starts to outweigh "
             "the wish to draw.",`
- **REPLACE WITH:** `    "10-12": "Between ten and twelve, a child starts drawing for realism and measuring the "
             "drawing against what they had in mind. This is often when the inner critic "
             "shows up, and “it never looks the way I want” starts to outweigh the urge to "
             "draw.",`
- **Why:** "seeing the world realistically" says the younger child sees it unrealistically, which is not the intended claim; "the wish to draw" is «желание рисовать» literally, where English says *the urge*.

### F-029 `config/free_texts.py:163-164` — duration, days
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "days": "A few days is too short a stretch to talk about a pattern: for now this may "
            "simply be what the last few evenings have been about.",`
- **REPLACE WITH:** `    "days": "A few days isn’t long enough to call it a pattern. For now it may just be what "
            "the last few evenings happened to be about.",`
- **Why:** "too short a stretch to talk about a pattern" is three abstractions in a row; splitting the colon into two sentences also removes one of this file's many stacked clauses.

### F-030 `config/free_texts.py:165-166` — duration, weeks
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `    "weeks": "A few weeks is long enough to notice a pattern, but the pattern on its own "
             "is not yet enough to explain what is behind it.",`
- **REPLACE WITH:** `    "weeks": "A few weeks is long enough to be a pattern. What the pattern means is a "
             "separate question, and one drawing won’t settle it.",`
- **Why:** "enough to X, but not enough to Y" is the mirrored-contrast shape, and "what is behind it" is the same «что за этим стоит» calque as the months modifier.

### F-031 `config/free_texts.py:167-169` — duration, months
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `    "months": "A few months means this is a settled way of drawing by now. What stands "
              "behind it cannot be read from the duration alone: the same habit forms in "
              "different children for different reasons.",`
- **REPLACE WITH:** `    "months": "A few months means this is a settled way of drawing by now. How long it has "
              "gone on doesn’t tell you why — the same habit shows up in different children "
              "for completely different reasons.",`
- **Why:** "What stands behind it cannot be read from the duration alone" is «что за этим стоит» plus an agentless passive, and it is the most conspicuously translated sentence in the file.

### F-032 `config/free_texts.py:170-172` — duration, always
- **Severity:** must-fix · **Type:** ai-tell
- **CURRENT:** `    "always": "If it has always been this way, it is more likely {poss} way of drawing "
              "than a change. Then the interesting question is not what changed, but what "
              "this way of drawing gives {obj}.",`
- **REPLACE WITH:** `    "always": "If it has always been this way, it’s more likely to be {poss} way of drawing "
              "than a change. The question worth asking is what {sub} get{s} out of drawing "
              "like this.",`
- **Why:** `Then` as a sentence opener is «тогда» carried over, and "the interesting question is not X, but Y" is the not-X-but-Y contrast the site's own copy standard bans.

### F-033 `config/free_texts.py:181-184` — override, pressure × always
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `        "If it has always been this way, then it is a settled way of drawing rather than "
        "a recent change. Why {sub} draw{s} like this is not something the duration alone "
        "can show.",`
- **REPLACE WITH:** `        "If it has always been this way, it’s a settled way of drawing rather than a recent "
        "change. How long it has gone on can’t tell you why {sub} draw{s} like this.",`
- **Why:** The fronted subject clause ("Why they draw like this is not something…") is Russian topic-comment order; English puts the short subject first. Note the override's protective purpose (documented at lines 175-179) is preserved — it still refuses to normalize the behavior.

### F-034 `config/free_texts.py:185-188` — override, stopped × always
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `        "If {sub} never drew much to begin with, this is not a change. Then one drawing "
        "certainly cannot settle the reasons - but the drawing itself is still worth "
        "looking at.",`
- **REPLACE WITH:** `        "If {sub} never drew much to begin with, this isn’t a change. One drawing certainly "
        "can’t explain why — but it’s still worth looking at.",`
- **Why:** "settle the reasons" is not English (`выяснить причины` rendered word for word), plus the `Then` opener again.

### F-035 `config/free_texts.py:192`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `LENS_PREFIX = "If the drawing is nearby, look at just one thing:"`
- **REPLACE WITH:** `LENS_PREFIX = "If the drawing is handy, look at just one thing:"`
- **Why:** A drawing is not *nearby*; `handy` is the word the V0.032 pass settled on for exactly this idea on the home page.

### F-036 `config/free_texts.py:194-195` — lens, black
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "black": "is the black used almost everywhere, or only for particular characters, "
             "outlines and details?",`
- **REPLACE WITH:** `    "black": "is the black all over the page, or just on certain characters, outlines, "
             "and details?",`
- **Why:** Agentless passive plus `particular` as a calque of «отдельных»; the serial comma also matches the rest of the site.

### F-037 `config/free_texts.py:197-198` — lens, alone
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "alone": "is there space left on the page where others could have been, or is the "
             "whole page taken up by one character?",`
- **REPLACE WITH:** `    "alone": "is there empty space where someone else could have gone, or does the one "
             "character fill the whole page?",`
- **Why:** "space left … where others could have been" is a past-perfect construction English does not use for hypothetical drawing space, and the second half is a passive where the active is shorter.

### F-038 `config/free_texts.py:199` — lens, faceless
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `    "faceless": "are the faces and hands missing on every figure, or only on some?",`
- **REPLACE WITH:** `    "faceless": "are the faces and hands missing from every figure, or only from some?",`
- **Why:** *Missing from*, not *missing on* — a preposition transfer, and the parent is being asked to go check, so the sentence has to be instantly clear.

### F-039 `config/free_texts.py:202-203` — lens, pressure
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "pressure": "is the pressure the same across the page, or heavier in one particular "
                "place?",`
- **REPLACE WITH:** `    "pressure": "is the pressure the same across the page, or heavier in one spot?",`
- **Why:** "one particular place" is the «в одном определённом месте» stack; *one spot* is what a parent looking at paper says.

### F-040 `config/free_texts.py:204-205` — lens, stopped
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "stopped": "in {poss} last piece, what did {sub} carry through to the end, and what "
               "did {sub} leave unfinished?",`
- **REPLACE WITH:** `    "stopped": "in the last thing {sub} drew, what did {sub} finish, and what did {sub} "
               "leave unfinished?",`
- **Why:** `piece` (F-006) plus "carry through to the end", which is «довёл до конца» rendered literally where English simply says *finish*.

### F-041 `config/free_texts.py:209`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `WAIT_PREFIX = "While we look, notice one thing yourself:"`
- **REPLACE WITH:** `WAIT_PREFIX = "While we read it, look for one thing yourself:"`
- **Why:** *Notice* cannot be commanded in English — you can look for something, but you can't be told to notice it. This renders on the waiting screen, where the parent has nothing else to read.

### F-042 `config/free_texts.py:216-217`
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `TRANSITION = ("A description is enough to choose where to look. But only the drawing "
              "itself will show what is actually there.")`
- **REPLACE WITH:** `TRANSITION = ("What you’ve told us is enough to know where to look. Only the drawing "
              "can show what’s actually there.")`
- **Why:** "A description is enough to choose where to look" has no agent anywhere in it — it is the impersonal Russian construction, and it lands at the hinge of the funnel where the parent decides whether to upload.

### F-043 `config/free_texts.py:218`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `ASK_ANY = ("Any recent drawing will do. Photograph the whole sheet in ordinary light.")`
- **REPLACE WITH:** `ASK_ANY = ("Any recent drawing will do. Take a photo of the whole sheet in daylight if you can.")`
- **Why:** *Photograph* as an imperative is formal-to-archaic in US consumer copy, and "ordinary light" is «при обычном свете». The home page already says "Take a photo of the whole sheet."

### F-044 `config/free_texts.py:220-222` — ask note, standard
- **Severity:** must-fix · **Type:** ai-tell
- **CURRENT:** `    "standard": "If there are several like this, pick an ordinary example - not the most "
                "frightening and not the most unusual one. A typical piece is more useful "
                "to us than an extreme case.",`
- **REPLACE WITH:** `    "standard": "If there are several like this, pick an ordinary one — not the scariest and "
                "not the strangest. A typical drawing tells us more than an extreme one.",`
- **Why:** Doubled `not the most X and not the most Y` negation, `piece` (F-006), and "an extreme case" is clinical intake vocabulary. The paragraph's real job — documented at lines 213-215, keeping the sample unbiased — survives intact.

### F-045 `config/free_texts.py:223-224` — ask note, neutral
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "neutral": "For a first reading, don't pick the prettiest or the most \"correct\" "
               "drawing. Take an ordinary recent piece your child made on their own.",`
- **REPLACE WITH:** `    "neutral": "For a first reading, don’t pick the prettiest one or the most “correct” one. "
               "Take an ordinary recent drawing your child made on their own.",`
- **Why:** `piece` again, plus the straight quotes around *correct* render as straight on a page that is otherwise curly.

### F-046 `config/free_texts.py:225-227` — ask note, stopped
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `    "stopped": "If you still have a drawing from around the time {sub} {was} still drawing "
               "on {poss} own initiative, use that one - not a school assignment and not a "
               "copy of a model.",`
- **REPLACE WITH:** `    "stopped": "If you still have something from back when {sub} {was} drawing without being "
               "asked, use that — not a school assignment, and not a copy of a picture.",`
- **Why:** "on their own initiative" is bureaucratic («по собственной инициативе»), and "a copy of a model" is studio-art vocabulary that a US parent will not map onto *copied a picture off the iPad*.

### F-047 `config/free_texts.py:232` — neutral path, ¶1
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "Then there is no need to go looking for a problem.",`
- **REPLACE WITH:** `    "Good — then there’s no need to go looking for a problem.",`
- **Why:** A paragraph opening on bare `Then` is the «тогда» calque, and as the first thing the untroubled parent reads it currently sounds like a correction.

### F-048 `config/free_texts.py:233-235` — neutral path, ¶2
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `    "What is more interesting is what your child chose for themselves: what they decided "
    "to draw, what they gave the most room to, which details they added, and the story "
    "they tell about their own work.",`
- **REPLACE WITH:** `    "What’s more interesting is what your child picked out for themselves: what they "
    "decided to draw, what they gave the most room to, which details they added, and the "
    "story they tell about it.",`
- **Why:** "chose for themselves" is ambiguous between *selected* and *chose on their own behalf*, and "their own work" is the gallery register of F-006.

### F-049 `config/free_texts.py:236-238` — neutral path, ¶3
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `    "At {band} the drawings can already be looked at against what usually appears and "
    "changes at this stage of development - but the interesting part starts where the age "
    "patterns end and this particular drawing by this particular child begins.",`
- **REPLACE WITH:** `    "At {band}, you can already read a drawing against what usually shows up and changes "
    "at this stage. The interesting part starts where the age patterns run out and this "
    "one drawing by this one child begins.",`
- **Why:** Agentless passive ("can already be looked at"), a 40-word single sentence, and "this particular X by this particular Y" — a Russian rhetorical doubling that in English reads as padding.

### F-050 `config/free_texts.py:246-247` — stopped path, ¶1
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `    "From one drawing there is no honest way to establish why this happened. And judging "
    "whether {sub} drew well or badly would not give much here either.",`
- **REPLACE WITH:** `    "One drawing can’t honestly tell you why this happened. And deciding whether {sub} drew "
    "well or badly wouldn’t get you very far either.",`
- **Why:** "From one drawing there is no honest way to establish…" is the impersonal Russian frame, and "would not give much" is «мало что даст» word for word. The hard boundary documented at lines 242-244 — no promise to explain why the child stopped — is untouched.

### F-051 `config/free_texts.py:248-250` — stopped path, ¶2
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `    "What helps more is looking at the last piece {sub} chose to make on {poss} own: what "
    "{sub} wanted to draw, how hard a task {sub} set {refl}, what {sub} carried through "
    "and what {sub} left unfinished.",`
- **REPLACE WITH:** `    "What helps more is looking at the last drawing {sub} made without being asked: what "
    "{sub} wanted to draw, how much {sub} took on, what {sub} finished and what {sub} left "
    "unfinished.",`
- **Why:** "how hard a task they set themselves" is «какую сложную задачу поставил себе» carried over whole; `piece` and "carried through" are covered above.

### F-052 `config/free_texts.py:258-259`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `NO_DRAWING_BODY = ("We'll save your place and email you the link - add the photo when you "
                   "find one. You won't have to answer the questions again.")`
- **REPLACE WITH:** `NO_DRAWING_BODY = ("We’ll save your place and email you a link — add a photo whenever you "
                   "find one. You won’t have to answer the questions again.")`
- **Why:** Both definite articles point at things that do not exist yet (there is no link and no photo at this moment), which is the Russian article-free habit surfacing as *the* by default.

### F-053 `config/free_texts.py:262`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `LIMIT_TITLE = "{name} already has a free reading of one drawing."`
- **REPLACE WITH:** `LIMIT_TITLE = "We’ve already read one of {name_poss} drawings."`
- **Why:** A child does not *have* a reading; the service did the reading. (Requires passing `name_poss` where this is formatted — check `app/free.py` before applying.)

### F-054 `config/free_texts.py:263-265`
- **Severity:** must-fix · **Type:** ai-tell
- **CURRENT:** `LIMIT_BODY = ("The next step isn't reading another single sheet on its own, but looking at "
              "what repeats between pieces and what changes. The first drawing is saved - "
              "you won't need to add it again.")`
- **REPLACE WITH:** `LIMIT_BODY = ("The next step is to look at what repeats from one drawing to the next, and "
              "what changes. The first drawing is saved — you won’t need to add it again.")`
- **Why:** "isn't X, but Y" contrast, `pieces` (F-006), and "another single sheet on its own" doubles the same idea twice.

### F-055 `config/free_texts.py:266`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `LIMIT_CTA = "Look at {name_poss} drawings together"`
- **REPLACE WITH:** `LIMIT_CTA = "Compare {name_poss} drawings side by side"`
- **Why:** *Together* is ambiguous — the parent reads it as "look at them with you", which is not what the button does.

### F-056 `config/free_texts.py:273-278` — SEVEN_DIRECTIONS
- **Severity:** should-fix · **Type:** translationese · ⚠️ **verify before applying**
- **CURRENT:** `    "The world and themes of the drawing", "Character in line and color",
    "Mood and expressiveness", "Story and characters",
    "Creativity and imagination", "Technique and handling of materials",
    "Fine motor skills and detail",`
- **REPLACE WITH:** `    "The world and themes of the drawing", "Character in line and color",
    "Mood and expression", "Story and characters",
    "Creativity and imagination", "Technique and materials",
    "Fine motor skills and detail",`
- **Why:** `expressiveness` is a calque of «выразительность» and `handling of materials` nominalizes a verb. **⚠️ The comment on lines 269-271 is correct that these names must match the paid report exactly** — `pipeline/render.py` renders the dimension labels (e.g. `“story & characters”` at line 67, lowercase with an ampersand). Reconcile all three lists — this file, `render.py`, and `templates/report.html` — in one pass, or don't touch them at all. Right now they already differ in case and connector.

### F-057 `config/free_texts.py:282-284`
- **Severity:** should-fix · **Type:** britishism
- **CURRENT:** `SELLING_LAUNCH = ("Right now the reading of one drawing is free: we are only just launching "
                  "and we want as many parents as possible to try it. It won't always be "
                  "this way.")`
- **REPLACE WITH:** `SELLING_LAUNCH = ("Right now a reading of one drawing is free — we just launched, and we want "
                  "as many parents as possible to try it. That won’t last forever.")`
- **Why:** `only just` in this sense is British; US English says *we just launched*. "It won't always be this way" is vague enough to read as a warning about the child rather than the price.

### F-058 `config/free_texts.py:285-287`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `SELLING_BODY = ("The full report is built differently. We look at 1-3 drawings at once and "
                "read them across seven dimensions: {directions}. With a score and an "
                "explanation for each.")`
- **REPLACE WITH:** `SELLING_BODY = ("The full report is built differently. We look at 1–3 drawings together and "
                "read them across seven areas — {directions} — with a score and a "
                "plain-language explanation for each.")`
- **Why:** "With a score and an explanation for each." is a sentence fragment, `1-3` should use the en dash the rest of the site uses, and `dimensions` is internal vocabulary (the landing page and FAQ both say *areas*).

### F-059 `config/free_texts.py:288-290`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `SELLING_MAIN = ("And above all, with a chapter of its own about who {name} is: what draws "
                "{obj}, what {poss} temperament is like, what matters to {obj} and how to "
                "support {obj}. About eight pages, a PDF by email within the hour.")`
- **REPLACE WITH:** `SELLING_MAIN = ("Above all, it has a chapter of its own about who {name} is: what pulls {obj} "
                "in, what {poss} temperament is like, what matters to {obj}, and how to "
                "support {obj}. About eight pages, emailed as a PDF within the hour.")`
- **Why:** Three problems in one string — the sentence is a fragment continuing the previous fragment; `what draws {obj}` is an accidental pun on drawing and reads as "what draws them [on paper]"; and the serial comma is missing before *and how to support*.

### F-060 `config/free_texts.py:292`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `SELLING_GUARANTEE = "Not what you hoped for? We refund within 7 days."`
- **REPLACE WITH:** `SELLING_GUARANTEE = "Not what you hoped for? Ask within 7 days and we’ll refund you."`
- **Why:** As written this promises how fast the money comes back; the policy is about the window in which the buyer can ask. Same string and same fix on `templates/landing.html:260`.

### F-061 `config/free_texts.py:293`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `RESULT_CTA_BUTTON = "Build {name_poss} portrait - ${price}"`
- **REPLACE WITH:** `RESULT_CTA_BUTTON = "Get {name_poss} full report — ${price}"`
- **Why:** Hyphen-as-dash, and `Build` puts the work on the parent. The landing page's equivalent button says "Get the report — $29"; these are the same purchase and should read the same way.

### F-062 `config/free_texts.py:300-304`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `COLORING_CTA_BODY = ("A coloring page shows how {name} handles a ready-made shape. What "
                     "{sub} invent{s} alone, what scale {sub} work{s} at and what stories "
                     "{sub} tell{s} are only visible where the page started empty. Take any "
                     "recent drawing of {poss} own - an ordinary one, not the prettiest - "
                     "and we'll read that.")`
- **REPLACE WITH:** `COLORING_CTA_BODY = ("A coloring page shows how {name} handles a shape someone else drew. What "
                     "{sub} come{s} up with, how big {sub} draw{s}, the stories {sub} tell{s} — "
                     "those only show up on a page that started out empty. Send any recent "
                     "drawing of {poss} own, an ordinary one rather than the prettiest, and "
                     "we’ll read that.")`
- **Why:** The middle sentence buries its verb 18 words in behind a three-part subject; "what scale they work at" is art-school vocabulary; and the two hyphens are doing an em dash's job in the same sentence.

### F-063 `config/free_texts.py:343-345`
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `SUMMARY_EXPLAINER = ("We haven't seen the drawing yet, so there are no guesses here about "
                     "what it means. Only what can be said from your answers and your "
                     "child's age - and where it's worth looking yourself.")`
- **REPLACE WITH:** `SUMMARY_EXPLAINER = ("We haven’t seen the drawing yet, so nothing here is a guess about what it "
                     "means. This is only what your answers and your child’s age can tell us, "
                     "plus one thing worth looking at yourself.")`
- **Why:** "Only what can be said from…" is a verbless fragment built on an agentless passive — the single most translated-sounding line on the summary screen, which is the screen that has to earn the upload.

### F-064 `config/free_texts.py:352`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `OFFER_TITLE = "Send us that drawing - we'll read it free"`
- **REPLACE WITH:** `OFFER_TITLE = "Send us that drawing and we’ll read it free"`
- **Why:** Hyphen-as-dash in a heading; the conjunction is cleaner than adding another dash to a page that already has several.

### F-065 `config/free_texts.py:353-355`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `OFFER_LEAD = ("Right now a reading of one drawing is free: we're only just launching. In "
              "about a minute you'll have a reading of this sheet - here on this page and "
              "as a copy by email.")`
- **REPLACE WITH:** `OFFER_LEAD = ("Right now a reading of one drawing is free — we just launched. In about a "
              "minute you’ll have a reading of this drawing, here on the page and as a copy "
              "by email.")`
- **Why:** `only just` (F-057) and "a reading of this sheet" — *sheet* is the Russian «лист»; the parent thinks of it as a drawing.

### F-066 `config/free_texts.py:359`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `    "what's visible on the page - the medium, the scale, details that are easy to miss",`
- **REPLACE WITH:** `    "what’s on the page — what it’s drawn with, how big things are, details that are easy to miss",`
- **Why:** "the medium, the scale" is gallery-catalog register. The identical phrase appears on the home page (`templates/home.html:78`) and should be changed in both places together.

### F-067 `config/free_texts.py:363`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `OFFER_HOW = "Which drawing works"`
- **REPLACE WITH:** `OFFER_HOW = "Which drawing to send"`
- **Why:** As a heading, "Which drawing works" reads as a question with the verb missing, and *works* is doing double duty against the child's "work".

### F-068 `config/free_texts.py:364`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `OFFER_FREE_NOTE = "Free, no card, no account."`
- **REPLACE WITH:** `OFFER_FREE_NOTE = "Free. No credit card, no account."`
- **Why:** Bare *card* is ambiguous in US checkout copy; the standard reassurance is *no credit card*. Same fix at `templates/home.html:18` and `:46` and `templates/landing.html:280`.

### F-069 `config/free_texts.py:367-370`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `UPLOAD_BODY = ("The reading appears right here in about a minute, and a copy goes to your "
               "email - so it isn't lost, and so you have something to show. The same "
               "email has your account link: if you ever want the full report, the drawing "
               "is already there and you won't have to upload it again.")`
- **REPLACE WITH:** `UPLOAD_BODY = ("The reading shows up right here in about a minute, and a copy goes to your "
               "email so you don’t lose it. That email also has your account link: if you "
               "ever want the full report, the drawing is already there and you won’t have "
               "to upload it again.")`
- **Why:** "so you have something to show" has no one to show it to and reads as an afterthought; "The same email has your account link" is a possessive-inversion English avoids.

### F-070 `config/free_texts.py:372`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `UPLOAD_NOSPAM = "No newsletter. Only your reading and whatever you order yourself."`
- **REPLACE WITH:** `UPLOAD_NOSPAM = "No newsletter — just your reading, and anything you order."`
- **Why:** "whatever you order yourself" is the Russian reflexive («что закажете сами») carried over; the reflexive adds nothing in English and reads as a warning.

### F-071 `config/free_texts.py:391-395` — SPARSE_PARAGRAPHS
- **Severity:** must-fix · **Type:** ai-tell
- **CURRENT:** `    "In a drawing like this, the interesting thing is not to hunt for a hidden meaning in "
    "every line, but to see how {name} uses drawing itself: whether {sub} repeat{s} a "
    "movement, change{s} direction, come{s} back to something already drawn, and whether "
    "{sub} give{s} {poss} marks names. This, at this age, is where the important thing is "
    "happening.",`
- **REPLACE WITH:** `    "In a drawing like this, the thing to watch is how {name} uses drawing itself: whether "
    "{sub} repeat{s} a movement, change{s} direction, come{s} back to something already "
    "drawn, whether {sub} give{s} {poss} marks names. At this age, that’s where the real "
    "work is happening — not in the hidden meaning of any one line.",`
- **Why:** "the interesting thing is not to X, but to Y" is the banned contrast, and "This, at this age, is where the important thing is happening" is a Russian cleft rendered word for word. Moving the negation to the end keeps the reassurance without opening on it.

### F-072 `config/free_texts.py:397-401` — COLORING_PARAGRAPH
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `COLORING_PARAGRAPH = ("We can see this is a coloring page. It is a great way to practice "
                      "fine motor control, but here the child is working inside borders "
                      "someone else set. To see {poss} own character, {poss} sense of "
                      "scale and how {sub} build{s} a story, we need a drawing on a blank "
                      "page.")`
- **REPLACE WITH:** `COLORING_PARAGRAPH = ("This looks like a coloring page. Those are great practice for fine motor "
                      "control, but your child is working inside lines someone else drew. To "
                      "see {poss} own character, how big {sub} draw{s}, and how {sub} build{s} "
                      "a story, we need a drawing on a blank page.")`
- **Why:** `borders` is «границы» — an American parent calls them *the lines*; "the child" switches to third person about the reader's own kid; "sense of scale" is art-school vocabulary.

### F-073 `config/free_texts.py:405-409` — MISMATCH_PARAGRAPH
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `MISMATCH_PARAGRAPH = ("One thing up front: the particular thing you mentioned isn't visible "
                      "in this drawing - there is something else here. We'll read what is "
                      "on this page. If you'd like us to look at the drawings you were "
                      "describing, show us one of those and it will be a different "
                      "conversation.")`
- **REPLACE WITH:** `MISMATCH_PARAGRAPH = ("One thing up front: what you described isn’t in this particular drawing — "
                      "this one is something else. We’ll read what’s on this page. If you’d "
                      "like us to look at the drawings you were describing, send us one of "
                      "those and we’ll read that instead.")`
- **Why:** "the particular thing you mentioned" and "there is something else here" are both literal renderings, and "it will be a different conversation" reads in US English as *that's a topic I'm refusing to discuss* — the opposite of the intent. The paragraph's protective design (documented at lines 402-404 — never tell the parent they were wrong) is preserved.

### F-074 `config/free_texts.py:412-413` — STORAGE_NOTICE
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `STORAGE_NOTICE = ("We keep the photo of the drawing for 90 days, then delete it. "
                  "The reading itself stays with you at your link.")`
- **REPLACE WITH:** `STORAGE_NOTICE = ("We keep the photo for 90 days, then delete it. Your reading stays at "
                  "your link.")`
- **Why:** The emphatic *itself* is «сам» carried over and adds nothing; "the photo of the drawing" says the same noun twice. The 90-day claim is unchanged.

## §1b — `config/free_keys.py` (the interpretation-key library)

These strings do double duty: `source_note` renders to the visitor under "Source:" on the result page, and `feature` is pasted into the system prompt by `prompt_block()`.

### F-075 `config/free_keys.py:38`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"source_note": "the projective tradition; the observation is widely described, but as a hypothesis rather than a measurement",`
- **REPLACE WITH:** `"source_note": "from the projective tradition — widely described, though as a hypothesis rather than a measurement",`
- **Why:** This renders under "Source:" on the result page (`templates/free_result.html:58`). The semicolon splice plus the agentless "the observation is widely described" is academic passive in a line a parent reads on her phone.

### F-076 `config/free_keys.py:55`
- **Severity:** must-fix · **Type:** britishism
- **CURRENT:** `"feature": "the page divided into zones or planes, several centres of attention",`
- **REPLACE WITH:** `"feature": "the page divided into zones or planes, several centers of attention",`
- **Why:** British spelling, and because this string is injected into the prompt it also steers the model's own spelling. (Covered by the F-004 sweep.)

## §1c — the `/free/` templates

### F-077 `templates/free.html:4`
- **Severity:** optional · **Type:** error
- **CURRENT:** `{{ _('A free reading of one child’s drawing.') }}`
- **REPLACE WITH:** `{{ _('A free reading of one of your child’s drawings.') }}`
- **Why:** "one child's drawing" parses as *a drawing of one child* rather than *one drawing by your child*.

### F-078 `templates/free.html:30`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `<div class="hint">{{ _('The name will be used in the reading') }}</div>`
- **REPLACE WITH:** `<div class="hint">{{ _('We’ll use it in the reading') }}</div>`
- **Why:** An agentless passive under a form field is the classic translated-UI tell; the active version is shorter and warmer.

### F-079 `templates/free.html:48`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `<label>{{ _('How old?') }}</label>`
- **REPLACE WITH:** `<label>{{ _('How old are they?') }}</label>`
- **Why:** The two labels above it are full questions, so the bare fragment reads as clipped form-speak.

### F-080 `templates/free.html:118`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `<p class="sub">{{ _('This is taking longer than usual. We’ll email it as soon as`
- **REPLACE WITH:** `<p class="sub">{{ _('This is taking longer than usual. We’ll email the reading as soon as`
- **Why:** `it` points at nothing on this screen, at the exact moment the parent is deciding whether to close the tab.

### F-081 `templates/free.html:137`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `_('Finding a detail worth holding on to…'),`
- **REPLACE WITH:** `_('Finding a detail worth a second look…'),`
- **Why:** *Worth holding on to* doesn't collocate with a detail in a drawing; the home page already uses "worth a second look" for the same idea.

### F-082 `templates/free.html:138`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `_('Re-reading the wording…'), _('Almost there…')] | tojson }},`
- **REPLACE WITH:** `_('Checking how it’s worded…'), _('Almost there…')] | tojson }},`
- **Why:** "Re-reading the wording" describes our internal process; the parent has no idea whose wording is being re-read.

### F-083 `templates/free.html:141`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `'format': _('Format: JPG, PNG, HEIC or WebP.'),`
- **REPLACE WITH:** `'format': _('That format won’t work. Please use a JPG, PNG, HEIC, or WebP.'),`
- **Why:** An error message that is only a label doesn't say what went wrong, and the missing serial comma is inconsistent with US consumer style used elsewhere.

### F-084 `templates/free.html:142`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `'broken': _('That file is damaged, or it isn’t a photo.'),`
- **REPLACE WITH:** `'broken': _('We couldn’t open that file — it may be damaged, or it may not be a photo.'),`
- **Why:** Stating the damage as fact blames the parent's file; hedging puts the failure on our side.

### F-085 `templates/free.html:145`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `'cap': _('We’ve read the maximum number of drawings for today. Leave your email and we’ll send you a link tomorrow.'),`
- **REPLACE WITH:** `'cap': _('We’ve hit today’s limit on free readings. Leave your email and we’ll send you a link tomorrow.'),`
- **Why:** "read the maximum number of drawings for today" is a nominalized clause where English uses a short verb phrase.

### F-086 `templates/free.html:146`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `'email_cap': _('This email has used its free readings for today. Please try again tomorrow.'),`
- **REPLACE WITH:** `'email_cap': _('You’ve used your free readings for today. Please try again tomorrow.'),`
- **Why:** An email address can't "use" readings; the personification reads as machine-translated and avoids addressing the person.

### F-087 `templates/_free_summary.html:59`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `<div class="fd-text">{{ _('Tap to choose a photo — JPG, PNG or HEIC, up to 15 MB') }}</div>`
- **REPLACE WITH:** `<div class="fd-text">{{ _('Tap to choose a photo — JPG, PNG, HEIC, or WebP, up to 15 MB') }}</div>`
- **Why:** Missing serial comma, and the list omits WebP even though the input accepts it and the error string at `free.html:141` names it.

### F-088 `templates/_free_summary.html:63`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `<div class="hint field--gap-sm">{{ _('Only the analysis system sees the drawing — we`
- **REPLACE WITH:** `<div class="hint field--gap-sm">{{ _('Only our reading system ever sees the drawing — we`
- **Why:** "the analysis system" is cold engineering register in the one line meant to reassure a parent about her child's work.

### F-089 `templates/_free_summary.html:89`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `data-goal="free_no_drawing">{{ _('Save my place and come back later') }}</button>`
- **REPLACE WITH:** `data-goal="free_no_drawing">{{ _('Email me the link') }}</button>`
- **Why:** The button emails a link; "come back later" describes what the parent does afterwards, not what the click does.

### F-090 `templates/free_result.html:19`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `<p>{{ _('The reading didn’t finish. Nothing was charged and nothing was lost —`
- **REPLACE WITH:** `<p>{{ _('The reading didn’t finish, and nothing was lost —`
- **Why:** This is the free product, so "Nothing was charged" plants the idea that a charge was possible, at the moment trust is thinnest.

### F-091 `templates/free_result.html:31`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `<p class="hint">{{ _('The photo has been deleted under our retention policy.`
- **REPLACE WITH:** `<p class="hint">{{ _('We’ve deleted the photo, as our retention policy says we would.`
- **Why:** Agentless passive plus "under our retention policy" is legal register; the active version keeps the same commitment and sounds like a person.

### F-092 `templates/free_result.html:32`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `The reading itself stays.') }}</p>`
- **REPLACE WITH:** `The reading stays.') }}</p>`
- **Why:** The emphatic *itself* is «сам» carried over and adds nothing in English. Same pattern as F-074.

### F-093 `templates/free_result.html:51`
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `<div class="interp__label">{{ _('How this is read in the tradition of children’s drawing') }}</div>`
- **REPLACE WITH:** `<div class="interp__label">{{ _('How this is read in the literature on children’s drawing') }}</div>`
- **Why:** "in the tradition of children's drawing" is a word-for-word rendering of «в традиции чтения детских рисунков» that no US writer produces. It also appears inside the prompt (F-114) as the *preferred* attribution phrasing, so it currently shows up in both the label and the generated sentence beneath it. Fix both together — the required attribution is preserved either way.

### F-094 `templates/free_result.html:54`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `can’t confirm it. The most accurate answer will come from %(name)s — the question`
- **REPLACE WITH:** `can’t confirm it. The best answer will come from %(name)s — the question`
- **Why:** "the most accurate answer" applies a measurement word to a child's reply; *best* is what a native writes and the hedge is unchanged.

### F-095 `templates/free_result.html:72`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `<button class="btn btn--ghost" data-vote="no" data-goal="free_vote_no">{{ _('Not %(name)s', name=name) }}</button>`
- **REPLACE WITH:** `<button class="btn btn--ghost" data-vote="no" data-goal="free_vote_no">{{ _('That’s not %(name)s', name=name) }}</button>`
- **Why:** The yes button is a full sentence and this one is a fragment, so the pair reads unbalanced.

### F-096 `templates/free_result.html:74`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `<p class="hint" hidden data-thanks>{{ _('Thank you — this is what helps us get more accurate.') }}</p>`
- **REPLACE WITH:** `<p class="hint" hidden data-thanks>{{ _('Thank you — this is exactly what helps us get better.') }}</p>`
- **Why:** "get more accurate" is not idiomatic — *accurate* is not a state you *get* this way.

## §1d — `pipeline/free_prompt.py` and `pipeline/free_schema.py`

**This is where the "AI-generated text" complaint actually comes from.** No template fix reaches the generated reading; only the prompt does. Three mechanisms are at work: British spellings and calques in the instructions that the model mirrors (§0 F-004), *examples* written in stilted English that set the register for the whole block, and *mandatory structures* that guarantee every reading has the same shape.

### F-097 `pipeline/free_prompt.py:34`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `    "black": "how the dark colour is distributed: does it cover almost the whole field, or "`
- **REPLACE WITH:** `    "black": "how the dark color is distributed: does it cover almost the whole page, or "`
- **Why:** British spelling plus "the field" — a calque of «поле листа» with no consumer meaning in US English. The model echoes it back as "takes up most of the field".

### F-098 `pipeline/free_prompt.py:39`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `    "alone": "how much of the field the figure takes up; is there empty space left and "`
- **REPLACE WITH:** `    "alone": "how much of the page the figure takes up; is there empty space left and "`
- **Why:** Same «поле листа» calque, in the hint that shapes the opening sentence the parent reads first.

### F-099 `pipeline/free_prompt.py:41-44`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `    "faceless": "do all the figures lack faces and hands or only some of them; what has "
                "been worked out in detail instead",`
- **REPLACE WITH:** `    "faceless": "do all the figures lack faces and hands or only some of them; which "
                "parts the child did put detail into instead",`
- **Why:** "worked out in detail" (`проработано`) appears four times across the prompt and comes back in the reading as "the face is worked out in detail" — not how an American writes about a kid's drawing.

### F-100 `pipeline/free_prompt.py:46`
- **Severity:** optional · **Type:** prompt-instruction
- **CURRENT:** `                "crossings-out, layers, tears in the paper, and exactly where",`
- **REPLACE WITH:** `                "cross-outs, layered marks, torn paper, and exactly where",`
- **Why:** "crossings-out" is British/non-idiomatic and "tears in the paper" is a literal translation; the model reproduces both.

### F-101 `pipeline/free_prompt.py:55` — the word budget
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `Your job is a living, concrete reading of this one page: 300-390 words in total across the five blocks, and never more than 400. Keep room in hand - going over the limit means the analysis is regenerated, so aim for the middle of that range rather than the top of it.`
- **REPLACE WITH:** `Your job is a living, concrete reading of this one page: 260-360 words in total across the five blocks, and never more than 420. Do not pad to reach the range - if the page gives you less, write less. Going over 420 means the analysis is regenerated, so aim for the middle of the range, not the top.`
- **Why:** Three budgets are currently in play and none of them agree: this line says 300-390 / max 400, `free_schema.py:34` computes the per-block sum as 255-360, and `FREE_MAX_WORDS` is 420. The model pads to clear the floor (filler sentences) *and* compresses to stay under the ceiling (dropped articles, stacked clauses) — the two failure modes that read most like translated text. "Keep room in hand" is also a Britishism.

### F-102 `pipeline/free_prompt.py:100` — contradictory block-2 budget
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `BLOCK 2 - detail, "One detail". 60-90 words. ONE visual feature - OBSERVATION ONLY.`
- **REPLACE WITH:** `BLOCK 2 - detail, "One detail". 80-120 words. ONE visual feature - OBSERVATION ONLY.`
- **Why:** The block header says 60-90 while the JSON contract at line 180 and the per-block sum in `free_schema.py:34` both say 80-120, so the model receives contradictory budgets for the longest block and truncates mid-thought. Truncation is where the clipped, telegraphic sentences come from.

### F-103 `pipeline/free_prompt.py:62` — the observation formula
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `- THE OBSERVATION FORMULA: a visible detail -> what it may say about the CHILD -> how the parent can understand and support that.`
- **REPLACE WITH:** `- THE OBSERVATION FORMULA: a visible detail -> what it may say about the CHILD -> how the parent can understand and support that. This is the logic of the reading, not a sentence pattern: do not run the three steps in the same order in every block, do not signpost them, and never chain them into one sentence held together by dashes.`
- **Why:** Stated as a formula, the model renders it literally — "detail — what it may mean — what you can do" — so every reading carries the same three-beat em-dash sentence in every block. The addition keeps the reasoning and removes the visible template.

### F-104 `pipeline/free_prompt.py:63` — the mandatory opener
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `- OPEN UP WHAT IS NOT OBVIOUS with turns like "Notice how...", "Look at the way...", "What matters here is...", "It's interesting that...". At least one such turn is required.`
- **REPLACE WITH:** `- OPEN UP WHAT IS NOT OBVIOUS: point the parent at something they would otherwise walk past. "Notice how...", "Look at the way...", "What matters here is..." are examples of the move, NOT phrases to reuse - use at most one of them in the whole analysis, and prefer your own wording. Never begin two sentences in the analysis with the same word.`
- **Why:** "At least one such turn is required" makes a canned opener mandatory, so nearly every reading contains "Notice how…". A parent who reads two readings sees the template immediately.

### F-105 `pipeline/free_prompt.py:66`
- **Severity:** optional · **Type:** prompt-instruction
- **CURRENT:** `- RESTRAINT WITH SUPERLATIVES: 1-2 sincere warm notes in the whole analysis, the rest a calm expert tone. A high density of enthusiasm turns observation into advertising and lowers trust.`
- **REPLACE WITH:** `- RESTRAINT WITH SUPERLATIVES: one or two genuinely warm sentences in the whole analysis, the rest a calm expert tone. Piled-up enthusiasm reads as advertising and costs you the parent's trust.`
- **Why:** "sincere warm notes" and "a high density of enthusiasm" are literal translations; instructions written in that register set the register of the answer.

### F-106 `pipeline/free_prompt.py:84`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `Distinguish them from the legitimate language of the BOUNDARY in block 5: "from one drawing there is no way to tell whether this is settled" is about the limit of our knowledge, not about the child being fine.`
- **REPLACE WITH:** `Distinguish them from the legitimate language of the BOUNDARY in block 5: "one drawing can't show whether this is something she comes back to" is about the limit of what we can see, not about the child being fine.`
- **Why:** The sanctioned boundary phrasing is itself translationese — "whether this is settled" has no clear referent in English — and it is the phrasing the model copies into the final block of every reading.

### F-107 `pipeline/free_prompt.py:98` — the block-1 example
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `Good: "The first thing you notice is these two standing right next to each other, almost touching. One figure is small, with a smile and star-shaped eyes. The other is noticeably bigger, with an open mouth and a lot of hands. Sophie drew them both with one dark pencil, quickly, barely lifting her hand from the page."`
- **REPLACE WITH:** `Good: "The first thing you see is two figures standing shoulder to shoulder, almost touching. The small one has a smile and star-shaped eyes. The bigger one has its mouth open and more hands than it needs. Sophie drew them both in one dark pencil, fast, barely lifting her hand off the paper."`
- **Why:** This is the only model of block 1 the model has, and its shape — "is these two standing", "a lot of hands", two identically built "One figure is… The other is…" sentences — is exactly the stiffness being complained about. A native-sounding example with varied sentence shapes is the cheapest fix in the file.

### F-108 `pipeline/free_prompt.py:105` — the preferred attribution phrasing
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `An unnamed generic form - "in the tradition of reading children's drawings this is sometimes associated with...", "in the analysis of children's drawings this is sometimes read as..." - is FULLY VALID and preferred.`
- **REPLACE WITH:** `An unnamed generic form is FULLY VALID and preferred, but rotate the wording so that two readings never open the same way: "people who study children's drawings often link this to...", "in the research on children's art this tends to show up when...", "one common reading of this is...".`
- **Why:** "In the tradition of reading children's drawings" is «в традиции чтения детских рисунков» word for word, and because it is the *preferred* form it appears verbatim in the interpretation block of essentially every reading. This single phrase is the loudest translated-text signal in the product. The matching phrase in the YES example on line 130 must be updated too, and it is also the label at `templates/free_result.html:51` (F-093).

### F-109 `pipeline/free_prompt.py:106` — the hedge list
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `2. A HYPOTHESIS, NOT A CONCLUSION: "may speak of", "is sometimes associated with", "can be read as", "looks like". Never "this means".`
- **REPLACE WITH:** `2. A HYPOTHESIS, NOT A CONCLUSION: "may point to", "often goes with", "can be a sign that", "reads like". Do not use "may speak of" - it is not idiomatic American English. Never "this means".`
- **Why:** "may speak of" is «может говорить о» and, being listed first among mandatory hedges, lands in the hypothesis sentence of nearly every reading. ⚠️ **`pipeline/free_lint.py` checks the same hedge list and must be updated in the same commit**, or the linter will strip the new hedges and force a repair loop.

### F-110 `pipeline/free_prompt.py:141`
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `phrase - one or two sentences of the interpretation itself with a hypothesis hedge ("may speak of", "is sometimes associated with");`
- **REPLACE WITH:** `phrase - one or two sentences of the interpretation itself with a hypothesis hedge ("may point to", "often goes with", "can be a sign that");`
- **Why:** Second occurrence of the "may speak of" calque; leaving it here re-anchors the phrase even after F-109 is applied.

### F-111 `pipeline/free_prompt.py:128` — the negation ban is too narrow
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `THE NEGATION CONSTRUCTION IS FORBIDDEN. You may not write "this can be read NOT AS a reflection of an inner state BUT AS learning a task": to reject the state you have to name it, and what stays in the parent's head is exactly that. Write WHAT IT IS, and never what it is not.`
- **REPLACE WITH:** `THE NEGATION CONSTRUCTION IS FORBIDDEN. You may not write "this can be read NOT AS a reflection of an inner state BUT AS learning a task": to reject the state you have to name it, and what stays in the parent's head is exactly that. Write WHAT IT IS, and never what it is not. This is also a blanket style rule for all five blocks: no "not X, but Y", no "it isn't about X, it's about Y", no "less X than Y" anywhere in the analysis, even where nothing psychological is being denied - that shape is the clearest single sign of machine-written text.`
- **Why:** The ban currently covers only *psychological* negation, so the model still produces "This isn't an inventory of objects, it's a story" in the other four blocks. The prompt is itself saturated with the construction (lines 109, 120, 163, 167, 226) and the model absorbs the pattern from the instructions it is reading.

### F-112 `pipeline/free_prompt.py:145` — the portrait block
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `What THIS page says about the child themselves: which theme is holding them right now, what matters to them, how they go about things. Lean on visible choices - what they put at the centre, what they gave room to, what they decided not to draw.`
- **REPLACE WITH:** `What THIS page says about the child themselves: what they are into right now, what matters to them, how they go about things. Say it in your own words - "the theme holding her right now" is a stock phrase, do not use it. Lean on visible choices - what they put in the middle of the page, what they gave room to, what they left out.`
- **Why:** "the theme holding them" is «тема, которая его держит» and is repeated in the block spec, the example (line 147) and the JSON contract (line 181), so it appears near-verbatim in the portrait block of every reading — the block the parent actually cares about. `centre` is also British.

### F-113 `pipeline/free_prompt.py:146`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `The frame is required and there is no diagnosis - but A COOL TONE HERE IS A DEFECT. Write so that the parent recognizes their child and wants to repeat it.`
- **REPLACE WITH:** `The frame is required and there is no diagnosis - but A DETACHED, CLINICAL TONE HERE IS A DEFECT. Write so the parent recognizes their child and wants to repeat the sentence to someone.`
- **Why:** In US English "a cool tone" reads first as color temperature, so the instruction meant to force warmth is the one the model is most likely to misread — and the block comes back in the flat register being complained about.

### F-114 `pipeline/free_prompt.py:147` — the portrait example
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `The level to aim for: "It looks like the theme holding her right now is 'big and small' - who is stronger, who protects, who is close by. She put these two right next to each other, with no background and no other characters: the whole page is about the two of them. For five years old that is a very whole statement."`
- **REPLACE WITH:** `The level to aim for: "Right now she seems to be working on something like 'big and small': who is stronger, who looks after whom. She put these two right next to each other, with no background and nobody else on the page, so the whole drawing is about the pair of them. That is a lot to hold together at five."`
- **Why:** "For five years old that is a very whole statement" is «очень цельное высказывание» rendered literally and is ungrammatical in English, and the rule-of-three list is copied straight into output. This example sets the register for the block the product is judged on.

### F-115 `pipeline/free_prompt.py:149`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `BLOCK 4 - question_to_child. 25-40 words. EXACTLY ONE open question - one "?" in the whole block - plus one sentence about the child's answer being more accurate than any adult guess.`
- **REPLACE WITH:** `BLOCK 4 - question_to_child. 25-40 words. EXACTLY ONE open question - one "?" in the whole block - plus one sentence saying the child's own answer beats any adult guess. Word that second sentence differently every time; do not reuse the example below.`
- **Why:** A mandated closing sentence with a fixed meaning and a single example produces the identical sentence in every reading.

### F-116 `pipeline/free_prompt.py:150`
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `YES: "Tell me, who are these two and what's happening between them? What she tells you herself will be more accurate than any adult's guess."`
- **REPLACE WITH:** `YES: "Who are these two, and what's going on between them? Whatever she tells you will be closer to the truth than anything an adult can guess."`
- **Why:** "Tell me, who are these two" is the «Расскажи, кто эти двое» imperative opener, and "What she tells you herself will be more accurate" is a calque. As the only example for the block it is reproduced almost verbatim every time.

### F-117 `pipeline/free_prompt.py:155`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `"Whether Sophie comes back to this pair again, who is usually big and who is small in her drawings - one page does not show that."`
- **REPLACE WITH:** `"One page can't show whether Sophie comes back to this pair, or who is usually the big one in her drawings."`
- **Why:** Russian topic-comment inversion — long subject clause, dash, "one page does not show that" — which English readers parse as broken. The model reproduces the inversion in the closing block of every reading.

### F-118 `pipeline/free_prompt.py:158`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `The right length: "From one page there is no telling whether this is a habit or one evening's decision. Other drawings would show whether this way of building an image comes back."`
- **REPLACE WITH:** `The right length: "There's no way to tell from one page whether this is a habit or just how she felt like drawing that evening. Other drawings would show whether she builds a picture this way again."`
- **Why:** "one evening's decision" and "this way of building an image comes back" are translated constructions — and they are the last words of the free reading, immediately before the paid upsell.

### F-119 `pipeline/free_prompt.py:175` — ⭐ the highest-leverage change in this report
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `TECHNICAL: no emoji or decorative symbols. American English. A calm, warm tone, without exclamations or superlatives.`
- **REPLACE WITH:**
```
TECHNICAL: no emoji or decorative symbols. A calm, warm tone, without exclamations or superlatives.

HOW THE ENGLISH MUST SOUND (graded as hard as the content):
- Contemporary American English, the way one parent talks to another: American spelling (color, analyze, gray, toward), American words (mom, crayon, marker), contractions where they fall naturally (it's, doesn't, there's, can't).
- Vary sentence length. Put a short sentence next to a long one. If three sentences in a row have the same length or the same shape, rewrite one.
- Never start two consecutive sentences with the same word, and do not open more than one block with the child's name or with "The first thing".
- No em dashes holding a sentence together. Use a period or a comma. At most one dash in the whole analysis.
- No three-item lists as a default rhythm ("curious, focused and determined"). Two items, or one specific item, is almost always better.
- Banned vocabulary, all of it marks machine-written text: delve, tapestry, testament, journey, realm, landscape, unlock, harness, foster, nurture, showcase, boasts, vibrant, rich inner world, speaks volumes, it's worth noting, at its core, serves as, plays a crucial role, truly, simply put.
- Nothing from consulting or marketing language (insights, leverage, key takeaway, holistic) and nothing from the clinic (presents with, exhibits, indicative of, demonstrates a capacity for, the subject). You are describing a kid's drawing to their mother.
- Before you answer, read the text back as the parent. If a sentence sounds translated, or sounds like a report, rewrite it.
```
- **Why:** Two words — "American English" — buried in a technical line are the prompt's entire defense against the failure being reported. The model therefore defaults to its house style: even sentence lengths, em-dash clauses, three-item lists, "vibrant"/"journey" vocabulary. Everything else in §1d is worth doing, but this is the change that moves the output the furthest.

### F-120 `pipeline/free_prompt.py:169`
- **Severity:** optional · **Type:** prompt-instruction
- **CURRENT:** `Move "one detail" to the line, the placement, the use of the page.`
- **REPLACE WITH:** `Move "one detail" to line quality, placement, and how the page was used.`
- **Why:** The definite-article chain is a Russian pattern; the model mirrors it as "the line is confident, the placement is central".

### F-121 `pipeline/free_prompt.py:167`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `So here it is shorter and less: a warm opening, ONE observation about how the child handles colour and borders, one question, the honest gap.`
- **REPLACE WITH:** `So this one is shorter and does less: a warm opening, ONE observation about how the child handles color and staying inside the lines, one question, the honest gap.`
- **Why:** "shorter and less" is ungrammatical, and `borders` is «границы» — an American parent calls them *the lines* of a coloring page. Both surface in the coloring-page reading, a high-traffic path.

### F-122 `pipeline/free_prompt.py:171` — the rejection text
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `return insufficient_input=true, a reason_key from the list (photo_poor / not_a_drawing / blank / other) and a polite insufficient_reason.`
- **REPLACE WITH:** `return insufficient_input=true, a reason_key from the list (photo_poor / not_a_drawing / blank / other) and an insufficient_reason. The parent reads insufficient_reason word for word, on the page and in the email, so write it as plain American English addressed to them: one or two sentences, second person, say what you could not see and what to send instead - "The photo cuts off the bottom of the page, so I can't see how Sophie used the space. Send one more shot with the whole sheet in frame and I'll take another look." No apology boilerplate, no "unfortunately", and no technical words like input, image quality or analysis.`
- **Why:** `insufficient_reason` renders verbatim to the visitor (`templates/free_result.html:12` and `templates/email/insufficient.html:10`), yet the only guidance is the word *polite*. The model currently returns stiff, apologetic, machine-sounding rejection text on the one path where the visitor gets nothing else — and for a bounced visitor it is the first English they read from the product.

### F-123 `pipeline/free_prompt.py:181` — the JSON contract
- **Severity:** must-fix · **Type:** prompt-instruction
- **CURRENT:** `  "portrait_hint": "50-70 words: what this page says about the child themselves - the theme holding them, what matters to them. Warm, in frame, no diagnosis.",`
- **REPLACE WITH:** `  "portrait_hint": "50-70 words: what this page says about the child themselves - what they are into right now, what matters to them. Warm, in frame, no diagnosis.",`
- **Why:** The JSON contract is the last thing the model reads before generating, so leaving "the theme holding them" here re-installs the stock phrase even after F-112 is applied.

### F-124 `pipeline/free_prompt.py:182`
- **Severity:** optional · **Type:** prompt-instruction
- **CURRENT:** `"phrase": "the interpretation itself, in a hypothesis form"`
- **REPLACE WITH:** `"phrase": "the interpretation itself, worded as a hypothesis"`
- **Why:** "in a hypothesis form" is not English, and it sits in the field spec for the sentence the parent reads as *the* interpretation.

### F-125 `pipeline/free_schema.py:40`
- **Severity:** should-fix · **Type:** prompt-instruction
- **CURRENT:** `FREE_MAX_WORDS = 420`
- **REPLACE WITH:** `FREE_MAX_WORDS = 420  # keep the number quoted in free_prompt.py line 55 identical to this`
- **Why:** Documents the F-101 conflict at the second of the three places it is stated, so the next edit doesn't re-open it. (No visitor-facing fixed strings exist elsewhere in this file — every literal is a validator message or a comment.)

### F-126 `pipeline/free_schema.py:214`
- **Severity:** optional · **Type:** fixed-string
- **CURRENT:** `                f"the analysis is shorter than {floor} words ({n}) - it needs a warm "
                f"opening, a detail in frame, a question and an honest gap")`
- **REPLACE WITH:** `                f"the analysis is shorter than {floor} words ({n}) - add substance, not "
                f"padding: more of what is actually visible on the page, not longer sentences "
                f"about the same thing")`
- **Why:** This is what the model sees when it regenerates a short analysis. Listing the four blocks it already knows about invites it to inflate each one with filler; asking for more observed detail produces length worth reading.

---

# §2 — Public pages

## §2a — `templates/home.html`

### F-127 `templates/home.html:18`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `No card, no account.`
- **REPLACE WITH:** `No credit card. No account.`
- **Why:** Bare *card* is ambiguous in US usage (loyalty card, library card); *no credit card* is the standard reassurance. Same fix at line 46 and `landing.html:280` and `free_texts.py:364`.

### F-128 `templates/home.html:39`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `starting from what’s actually visible on the page.') }}</p>`
- **REPLACE WITH:** `starting with what’s actually on the page.') }}</p>`
- **Why:** *Starting from* is a calque; a native says *starting with*, and "visible on the page" doubles a word the sentence already carries.

### F-129 `templates/home.html:46`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `{{ _('No payment · No account · Photo can come later') }}`
- **REPLACE WITH:** `{{ _('No credit card · No account · Photo can wait') }}`
- **Why:** "No payment" reads like a system status, and "Photo can come later" is missing its article.

### F-130 `templates/home.html:62`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `Or nothing worries you at all and you’re simply curious about`
- **REPLACE WITH:** `Or maybe nothing worries you and you’re just curious about`
- **Why:** "Or nothing worries you at all" is a literal Russian sentence opening, and *simply curious* is the formal register, not the phone-at-midnight one.

### F-131 `templates/home.html:78`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `What’s visible on the page — the medium, the scale, the details that are easy to miss`
- **REPLACE WITH:** `What’s on the page — what it’s drawn with, how big things are, the details that are easy to miss`
- **Why:** "the medium, the scale" is gallery-catalog register. The identical phrase is in `config/free_texts.py:359` (F-066) — change both.

### F-132 `templates/home.html:79`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `One detail worth a second look — and what it may mean, offered as a suggestion grounded in developmental and art-education research`
- **REPLACE WITH:** `One detail worth a second look — and what it may mean, as a suggestion, grounded in developmental and art-education research`
- **Why:** "offered as a suggestion grounded in" stacks three abstract nouns in one clause; trimming keeps the identical sourcing claim.

### F-133 `templates/home.html:80`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `A short portrait: what’s got your child’s attention right now, read through their own choices`
- **REPLACE WITH:** `A short portrait: what has your child’s attention right now, based on the choices they made`
- **Why:** "read through their own choices" doesn't parse on first pass, and *what's got* is the have-got construction the copy standard bans.

### F-134 `templates/home.html:85`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `Educational observation, never a diagnosis. We don’t detect`
- **REPLACE WITH:** `Educational observation, not a diagnosis. We don’t detect`
- **Why:** The site's fixed framing everywhere else is *not a diagnosis*; the *never* variant is the emphatic-contrast tic and breaks consistency with the footer and `order.html:85`.

### F-135 `templates/home.html:103`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `Before any photo: what your answers and your child’s age can honestly tell you, and one thing to check on your own.`
- **REPLACE WITH:** `Before you upload anything: what your answers and your child’s age already tell you, plus one thing to look for yourself.`
- **Why:** "Before any photo" is a compressed noun phrase where English uses a clause, and "can honestly tell you" hedges defensively.

### F-136 `templates/home.html:108`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `Take a photo of the whole sheet in normal daylight. You’ll get it in about a minute — here and by email.`
- **REPLACE WITH:** `Take a photo of the whole sheet in daylight if you can. Your reading comes back in about a minute — here and by email.`
- **Why:** *It* has no antecedent but the photo the parent just took, so the sentence reads as if we send the photo back; "normal daylight" is a calque.

### F-137 `templates/home.html:125`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `The full report reads 1–3 drawings together across seven areas, with a chapter`
- **REPLACE WITH:** `The full report looks at up to three drawings together, across seven areas, with a chapter`
- **Why:** Three specs in one clause, and "full picture / full report" land in consecutive sentences.

## §2b — `templates/landing.html` (the paid product page)

### F-138 `templates/landing.html:8`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `A photo-based educational report on your child’s drawing: strengths, interests, emerging skills, and simple activities for home.`
- **REPLACE WITH:** `An educational report from a photo of your child’s drawing: strengths, interests, emerging skills, and simple activities to try at home.`
- **Why:** "photo-based" is an invented compound and "activities for home" is a literal rendering. This is the page's meta description.

### F-139 `templates/landing.html:12` and `:19`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `and simple activities for home. No diagnoses, no scary interpretations.`
- **REPLACE WITH:** `and simple activities to try at home. No diagnoses, nothing scary.`
- **Why:** Same "for home" calque, and "scary interpretations" is an abstract noun where plain English says *nothing scary*. Line 19 has the third instance of "activities for home".

### F-140 `templates/landing.html:44`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{{ _('Children often say in their drawings what they can’t yet put into words.') }}`
- **REPLACE WITH:** `{{ _('Children often say things in a drawing that they can’t yet put into words.') }}`
- **Why:** "say in their drawings what they…" is Russian word order; English keeps the object next to the verb.

### F-141 `templates/landing.html:46`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `{{ _('we’ll show you their strengths, what to nurture, and how to support them at home, drawing on the developmental stages of children’s art.') }}`
- **REPLACE WITH:** `{{ _('we’ll show you their strengths, what to nurture, and how to support them at home, based on how children’s art develops with age.') }}`
- **Why:** The trailing participial phrase ends the sentence weakly, and "drawing on… children's art" is an accidental pun on the product.

### F-142 `templates/landing.html:59`
- **Severity:** optional · **Type:** error
- **CURRENT:** `<span class="chip">{{ _('No diagnoses') }}</span><span class="chip">{{ _('Only you see the drawings') }}</span>`
- **REPLACE WITH:** `<span class="chip">{{ _('no diagnoses') }}</span><span class="chip">{{ _('only you see the drawings') }}</span>`
- **Why:** The neighboring chips ("about 8 pages", "7 areas") are lowercase, so the row renders with mixed capitalization.

### F-143 `templates/landing.html:71`
- **Severity:** optional · **Type:** error
- **CURRENT:** `The report reads your child as a person, through their drawing.`
- **REPLACE WITH:** `The report reads your child as a person, through what they draw.`
- **Why:** The comma sets off a bare prepositional phrase echoing the noun before it; naming what the child draws earns the pause.

### F-144 `templates/landing.html:75`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{{ _('Their character, read through choices they make themselves: how heavy the line is, how big things get on the page') }}`
- **REPLACE WITH:** `{{ _('Their character, read through the choices they make: how hard they press, how much space they take up on the page') }}`
- **Why:** "choices they make themselves" and "how big things get on the page" are literal renderings; the replacement names the same visible cues the way a parent would.

### F-145 `templates/landing.html:76`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{{ _('The mood their drawings carry, offered as a suggestion to explore') }}`
- **REPLACE WITH:** `{{ _('The mood their drawings carry, offered as a suggestion to explore with them') }}`
- **Why:** "a suggestion to explore" has no owner and reads as an abstraction; *with them* keeps the hedge and makes it concrete.

### F-146 `templates/landing.html:77`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `and what that hints about how they see the world`
- **REPLACE WITH:** `and what that suggests about how they see the world`
- **Why:** *Hint* takes *at*, not *about* — a preposition error a native reader catches immediately.

### F-147 `templates/landing.html:82`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `four about your child as a person and three about drawing skills, each with a clear explanation.`
- **REPLACE WITH:** `four about your child as a person, three about drawing skills, each with a plain-language explanation.`
- **Why:** As written, "each with a clear explanation" attaches only to the second group; *plain-language* is the wording used in the FAQ and pricing card.

### F-148 `templates/landing.html:89`
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `<h2 class="reveal">{{ _('How the conclusion is built') }}</h2>`
- **REPLACE WITH:** `<h2 class="reveal">{{ _('How each observation is built') }}</h2>`
- **Why:** *Conclusion* is a calque of «заключение» (a written finding); in US English it means the closing paragraph, so the heading misdescribes its own section.

### F-149 `templates/landing.html:90`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `{{ _('Every observation starts from something visible in the drawing,`
- **REPLACE WITH:** `{{ _('Every observation starts with something visible in the drawing,`
- **Why:** English idiom is *starts with*; *starts from* is a preposition transfer.

### F-150 `templates/landing.html:94`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `<p>{{ _('A warm little bird flies through a darker sky, drawn with care.') }}</p>`
- **REPLACE WITH:** `<p>{{ _('A small bird, drawn with care, flying through a dark sky.') }}</p>`
- **Why:** As written, the modifier "drawn with care" attaches to *sky*, not the bird.

### F-151 `templates/landing.html:99`
- **Severity:** optional · **Type:** error
- **CURRENT:** `We offer it as a hypothesis, and hold it lightly.`
- **REPLACE WITH:** `We offer it as a hypothesis and hold it lightly.`
- **Why:** No comma before *and* when the two verbs share one subject.

### F-152 `templates/landing.html:116`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `<h2 class="reveal">{{ _('See the kind of observations parents get') }}</h2>`
- **REPLACE WITH:** `<h2 class="reveal">{{ _('See the kind of observations you’ll get') }}</h2>`
- **Why:** The page speaks to one parent throughout; "parents get" switches to third person and sounds like a brochure.

### F-153 `templates/landing.html:117`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `you’ll see the drawing, the context, strengths, observations, and activities for parents.`
- **REPLACE WITH:** `you’ll see the drawing, the context, strengths, observations, and activities to try at home.`
- **Why:** The activities are things a parent does *with the child*, so "activities for parents" misnames them.

### F-154 `templates/landing.html:148`
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `An average score doesn’t mean a problem; sometimes a direction is simply less visible in the chosen subject.`
- **REPLACE WITH:** `An average score doesn’t mean something is wrong; sometimes an area just doesn’t show up much in the subject your child picked.`
- **Why:** *A direction* is a calque of «направление» (an area) and "the chosen subject" is an agentless passive. The same calque runs through `pipeline/render.py` (F-196 to F-200) — fix them as one vocabulary decision.

### F-155 `templates/landing.html:155`
- **Severity:** optional · **Type:** translationese
- **CURRENT:** `<h2 class="reveal">{{ _('No myths, no scary interpretations') }}</h2>`
- **REPLACE WITH:** `<h2 class="reveal">{{ _('No myths, nothing scary') }}</h2>`
- **Why:** "scary interpretations" is a heavy abstract noun where the plain phrase carries the same promise.

### F-156 `templates/landing.html:156`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `{{ _('We read your child carefully and seriously, grounded in developmental and art-education research, and offer what we see as a suggestion.') }}`
- **REPLACE WITH:** `{{ _('We read your child’s drawing carefully, using developmental and art-education research, and we offer what we notice as a suggestion.') }}`
- **Why:** "grounded in…" dangles off *we*, and "offer what we see as a suggestion" can be misread as *we regard it as a suggestion*.

### F-157 `templates/landing.html:172`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{{ _('we offer careful, research-grounded pointers — anchored to what’s visible, and turned back to the child') }}`
- **REPLACE WITH:** `{{ _('we offer careful, research-grounded observations, anchored to what’s visible and turned back to your child') }}`
- **Why:** *Pointers* means quick tips in US English, and the em dash plus two stacked participles overloads a bullet.

### F-158 `templates/landing.html:173`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{{ _('we point out strengths and growth areas, with simple activities for home') }}`
- **REPLACE WITH:** `{{ _('we point out strengths and growth areas, with simple activities to try at home') }}`
- **Why:** Same "for home" calque as the meta descriptions.

### F-159 `templates/landing.html:177`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `It’s a way to understand your child through their drawing: careful pointers drawn from the research, always offered as a suggestion.`
- **REPLACE WITH:** `It’s a way to understand your child through their drawing: careful observations grounded in research, always offered as a suggestion.`
- **Why:** "pointers drawn from the research" mixes register with a definite article English doesn't use for research in general, and *drawn* puns on drawings.

### F-160 `templates/landing.html:187`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `<p>{{ _('1–3 drawings your child already made work fine. Nothing has to be drawn just for this.') }}</p>`
- **REPLACE WITH:** `<p>{{ _('Use 1–3 drawings your child has already made. Nothing needs to be drawn just for this.') }}</p>`
- **Why:** "already made work fine" is a garden-path sentence — the reader parses *made work* before recovering — and the tense should be present perfect.

### F-161 `templates/landing.html:188`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `<p>{{ _('Age, materials, the subject and any prompt. The form takes 2–3 minutes.') }}</p>`
- **REPLACE WITH:** `<p>{{ _('Age, what they drew with, the subject, and whether anyone suggested it. The form takes 2–3 minutes.') }}</p>`
- **Why:** *Materials* and *any prompt* are form-jargon nouns, and the list is missing the serial comma used elsewhere on the page.

### F-162 `templates/landing.html:198`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `{{ _('These aren’t real clients; they’re examples of what the report can do.') }}`
- **REPLACE WITH:** `{{ _('These aren’t real families; they’re examples of what the report can do.') }}`
- **Why:** *Clients* reads clinical or B2B on a page written to a worried parent.

### F-163 `templates/landing.html:216` and `:279`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `{{ _('Read a drawing free') }}`
- **REPLACE WITH:** `{{ _('Get a free reading') }}`
- **Why:** See F-007 — six instances of this CTA across the site, all of which should match.

### F-164 `templates/landing.html:226`
- **Severity:** should-fix · **Type:** britishism
- **CURRENT:** `{{ _('If the report isn’t for you, write within 7 days and we’ll refund you — no fuss.') }}`
- **REPLACE WITH:** `{{ _('If the report isn’t for you, write to us within 7 days and we’ll refund you — no hassle.') }}`
- **Why:** Intransitive *write* is British usage, and *no fuss* is a British tag where US copy says *no hassle*. Same phrase at `app/content.py:42` and `app/legal.py:81`.

### F-165 `templates/landing.html:227`
- **Severity:** optional · **Type:** ai-tell
- **CURRENT:** `{{ _('Your child’s work is never published, never used in ads, and never shared with third parties.') }}`
- **REPLACE WITH:** `{{ _('We never publish your child’s work, use it in ads, or share it with third parties.') }}`
- **Why:** Triple *never* plus triple passive is the repeated-negation cadence; the active version says the same thing and names who is responsible.

### F-166 `templates/landing.html:238`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `<h2 class="reveal">{{ _('Choose your report') }}</h2>`
- **REPLACE WITH:** `<h2 class="reveal">{{ _('The report') }}</h2>`
- **Why:** Only one product is enabled, so *Choose* sits above a single card and reads as a missing option.

### F-167 `templates/landing.html:260`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `<p class="p-note">{{ _('Not what you hoped for? We refund within 7 days.') }}</p>`
- **REPLACE WITH:** `<p class="p-note">{{ _('Not what you hoped for? Ask within 7 days and we’ll refund you.') }}</p>`
- **Why:** Reads as the payout speed rather than the window in which the buyer can ask. Same string in `config/free_texts.py:292` (F-060).

### F-168 `templates/landing.html:276`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `it, and almost never the thing parents fear.`
- **REPLACE WITH:** `it, and it’s rarely the thing parents fear.`
- **Why:** "almost always X, almost never Y" is the mirrored-negation contrast, immediately after a similar construction in the same block.

### F-169 `templates/landing.html:280`
- **Severity:** optional · **Type:** error
- **CURRENT:** `{{ _('Free, about a minute, no card and no account.') }}`
- **REPLACE WITH:** `{{ _('Free, about a minute, no credit card and no account.') }}`
- **Why:** See F-127.

## §2c — `app/content.py` (FAQ + illustrative scenarios)

### F-170 `app/content.py:16`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `"No. This is an educational observation of the skills visible in a drawing, set "`
- **REPLACE WITH:** `"No. This is an educational observation of what’s visible in a drawing, set "`
- **Why:** The landing page promises a reading of the child as a person with skills as support, so "the skills visible" narrows the product against its own page. Same narrowing at line 23 and `templates/email/_email_base.html:12` and `pipeline/render.py:82`.

### F-171 `app/content.py:18`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"judgment of your child’s personality or state."),`
- **REPLACE WITH:** `"judgment of your child’s personality or how they’re feeling."),`
- **Why:** *State* is a bare calque of «состояние»; the replacement keeps the disclaimer's scope in natural English.

### F-172 `app/content.py:23`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `"Roughly ages 3 to 12. The report reads skills against what’s typical for your "`
- **REPLACE WITH:** `"Roughly ages 3 to 12. The report reads the drawing against what’s typical for your "`
- **Why:** Same skills-only narrowing, and "reads skills" is an odd collocation.

### F-173 `app/content.py:26`
- **Severity:** optional · **Type:** ai-tell
- **CURRENT:** `"1 to 3 drawings from the same period. They’re combined into one consolidated report, "`
- **REPLACE WITH:** `"1–3 drawings from the same period. They all go into one report, "`
- **Why:** "one consolidated report" doubles the same idea, and the rest of the site writes the range as 1–3.

### F-174 `app/content.py:31`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `"A warm, personal PDF (about 8 pages): your child’s strengths, how they work with color, "`
- **REPLACE WITH:** `"A warm, personal PDF (about 8 pages): your child’s strengths; how they work with color, "`
- **Why:** The answer nests a comma list inside a comma list, so the top-level items need semicolons. The two continuation lines need matching semicolons before *scores* and before *and simple activities*, and a serial comma in "form, detail, and story".

### F-175 `app/content.py:34`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `("Do you read emotions or hidden meanings from the colors?",`
- **REPLACE WITH:** `("Do you read emotions or hidden meanings into the colors?",`
- **Why:** The English idiom is *read something into*; "read from the colors" is a preposition transfer.

### F-176 `app/content.py:42`
- **Severity:** should-fix · **Type:** britishism
- **CURRENT:** `"Write to us within 7 days and we’ll refund you — no fuss."),`
- **REPLACE WITH:** `"Write to us within 7 days and we’ll refund you — no hassle."),`
- **Why:** See F-164; must match the landing page.

### F-177 `app/content.py:44-45`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `"A photo of 1–3 drawings your child already made, plus a short bit of context (age, what "
         "they drew with, the subject); it’s a 2-3 minute form. Nothing has to be drawn just for this."),`
- **REPLACE WITH:** `"Photos of 1–3 drawings your child has already made, plus a little context (age, what "
         "they drew with, the subject); the form takes 2–3 minutes. Nothing needs to be drawn just for this."),`
- **Why:** One photo cannot show three drawings; the tense should be present perfect; "a short bit of context" is a non-native quantifier stack; and "2-3 minute form" uses a hyphen where the same sentence uses an en dash.

### F-178 `app/content.py:60-62` — scenario 1
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"shows what actually keeps recurring across their drawings (say, space or dragons), "`
- **REPLACE WITH:** `"shows what keeps coming back across their drawings (space, say, or dragons), "`
- **Why:** "actually keeps recurring" is a Latinate double-up and mid-list *say,* is misplaced in US usage. Line 62 also needs "what to ask **your** child" and "the drawings that come next" for "in the next drawings" (a rendering of «следующих рисунках»), plus "Nothing scary." for "No scary readings."

### F-179 `app/content.py:65` — scenario 2
- **Severity:** optional · **Type:** error
- **CURRENT:** `"that house: their own world, a sense of safety, the people they love nearby. And how to "`
- **REPLACE WITH:** `"that house: their own world, a sense of safety, the people they love nearby — and how to "`
- **Why:** "And how to ask about it gently." is a stranded fragment; joining it fixes the sentence without losing the beat.

### F-180 `app/content.py:67` — scenario 3
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `"There’s almost always a single character and no other people. We don’t jump to “your child "`
- **REPLACE WITH:** `"Your child’s drawings almost always have one character and no one else. We don’t jump to “your child "`
- **Why:** The other three scenarios open by naming who is doing what; this one opens with *There's* and no referent, so the reader can't tell whose drawings are meant.

### F-181 `app/content.py:68`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"isn’t social.” We show that this can simply be a feature of the chosen subject, and "`
- **REPLACE WITH:** `"isn’t social.” We show that this is often just what the subject called for, and "`
- **Why:** "a feature of the chosen subject" is nominalized bureaucratic phrasing with an agentless passive.

### F-182 `app/content.py:69`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `"suggest how to support the child’s interest in stories with several characters.",`
- **REPLACE WITH:** `"suggest how to grow their interest in stories with more than one character.",`
- **Why:** *The child* drops out of second person mid-scenario, and "several characters" is stiffer than the spoken alternative.

### F-183 `app/content.py:70` — scenario 4
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `"You send three drawings from different days. We show what repeats from work to work (the "`
- **REPLACE WITH:** `"You send three drawings from different days. We show what repeats from one drawing to the next (the "`
- **Why:** "from work to work" is «от работы к работе» word for word; in English *work* here reads as employment.

### F-184 `app/content.py:71`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `"steadier traits) and what appeared just once (a moment’s mood), something a single "`
- **REPLACE WITH:** `"steadier traits) and what shows up just once (a passing mood) — something a single "`
- **Why:** The tense jumps from present *repeats* to past *appeared*, and the trailing appositive needs a dash to attach cleanly.

## §2d — `config/products.json`, `app/samples.py`, the shipped sample report

### F-185 `config/products.json:9`
- **Severity:** optional · **Type:** error
- **CURRENT:** `"A warm, personal PDF, about 8 pages",`
- **REPLACE WITH:** `"A warm, personal PDF of about 8 pages",`
- **Why:** Three commas in a five-word bullet make the length read as a fourth adjective rather than a measurement.

### F-186 `config/products.json:12`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `"Things to try at home, after every area",`
- **REPLACE WITH:** `"Things to try at home after each area",`
- **Why:** The comma wrongly separates the prepositional phrase from what it modifies, and *each* is the US choice with a countable set of seven.

### F-187 `app/samples.py:35`
- **Severity:** must-fix · **Type:** britishism
- **CURRENT:** `caption='"My house", Liam, age 6', hero=True, n_drawings=1),`
- **REPLACE WITH:** `caption='“My House,” Liam, age 6', hero=True, n_drawings=1),`
- **Why:** The comma sits outside the quotes (British convention) and the quotes are straight while the site is curly. This string renders in the `<h1>` and meta description of `/en/sample/sample-liam`.

### F-188 `pipeline/samples/sample_report.json` — global
- **Severity:** must-fix · **Type:** britishism
- **Where:** lines 14, 15, 17, 19, 40, 52, 62, 92, 93, 98, 109, 113
- **CURRENT (example, line 14):** `You might ask Liam, 'Who is the person standing outside? Where are they going?'`
- **REPLACE WITH:** `You might ask Liam, “Who is the person standing outside? Where are they going?”`
- **Why:** Single quotes as quotation marks are British; US English uses double quotes. Curly “ ” need no JSON escaping, unlike `\"`. All 47 apostrophes in this file are also straight (F-002).

### F-189 `pipeline/samples/sample_report.json:4`
- **Severity:** optional · **Type:** error
- **CURRENT:** `"age_display": "6 years 2 months"`
- **REPLACE WITH:** `"age_display": "6 years, 2 months"`
- **Why:** English needs the comma between units; this renders on the sample card and in the report header.

### F-190 `pipeline/samples/sample_report.json:6`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"context_summary": "Liam drew this scene at home on a weekend, entirely by his own choice, using markers on plain paper. He worked for about 15 minutes and declined any help.",`
- **REPLACE WITH:** `"context_summary": "Liam drew this scene at home over the weekend, entirely by his own choice, using markers on plain paper. He worked for about 15 minutes and didn’t want any help.",`
- **Why:** "on a weekend" is a non-US preposition choice and "declined any help" is a formal register no one uses about a six-year-old.

### F-191 `pipeline/samples/sample_report.json:7`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `What makes this drawing worth looking at carefully is not just what Liam drew, but how he chose to organize it: who gets to stand outside, what belongs together, what the day feels like.`
- **REPLACE WITH:** `What makes this drawing worth a closer look is how Liam chose to organize it: who stands outside, what belongs together, what kind of day it is.`
- **Why:** "not just X, but Y" followed by a three-item list is the exact contrast-plus-triad cadence being flagged. The same paragraph's third sentence ("Approached as an educational observation — not a clinical assessment — this scene offers a window into…") carries a third em-dash pair plus the "offers a window into" cliché and should become "Read as an educational observation, not a clinical assessment, this scene shows…".

### F-192 `pipeline/samples/sample_report.json:8`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `At 6, children who organize a scene this deliberately — everything in its place, everything accounted for — are often, in the developmental tradition, children who find safety and pleasure in knowing how things fit together.`
- **REPLACE WITH:** `At 6, children who organize a scene this deliberately, with everything in its place, are often described in the developmental tradition as children who find safety and pleasure in knowing how things fit together.`
- **Why:** Two nested interruptions push the verb 20 words from its subject, and "children who… are… children who" repeats the head noun.

### F-193 `pipeline/samples/sample_report.json` — the "You could / You might" opener
- **Severity:** should-fix · **Type:** ai-tell
- **Where:** all 15 activity bullets (lines 17, 19, 40, 62, 74, 92, 96, 97, 103 and others)
- **CURRENT (example, line 17):** `"You could ask Liam to tell you the 'story' of this scene`
- **REPLACE WITH:** `"Ask Liam to tell you the “story” of this scene`
- **Why:** Every activity bullet in the report opens with *You could* or *You might*, so the hedge stops softening and starts sounding evasive. Vary several to a direct imperative.

### F-194 `pipeline/samples/sample_report.json` — remaining prose fixes
- **Severity:** should-fix · **Type:** translationese / ai-tell / tone
- These are individually small; apply as one editing pass over the file.

| line | CURRENT | REPLACE WITH | why |
|---|---|---|---|
| 14 | `Liam chose to draw an entire small world — not just a house or just a person, but a scene with a human figure, a home, nature (the tree), weather (the sun), and ground (the grass).` | `Liam chose to draw an entire small world: a human figure, a home, a tree, the sun, and the grass they all stand on — a scene rather than a single object.` | another *not just X, but Y*; four parentheticals in one sentence |
| 19 | `You could look at illustrated picture books with him that show outdoor neighborhood or village scenes` | `You could look with him at picture books that show outdoor neighborhood or village scenes` | the relative clause strands after *with him* |
| 26 | `in the child's felt relationship with their own body and place in the world.` | `in how a child feels in their own body and in the world.` | four stacked abstract nouns; the hedge is untouched |
| 26 | `it is placed without apology: it takes up its own space and stands firmly on the ground line.` | `it takes up its own space and stands firmly on the ground line.` | "placed without apology" is a critic's flourish the clause then restates |
| 37 | `The overall register of this drawing is calm and sunny — not in a vague way, but in specific, visible terms:` | `The overall feel of this drawing is calm and sunny, in specific and visible ways:` | *register* is literary-critical jargon; flagged contrast pattern |
| 37 | `whether this calm register may reflect … one free Saturday morning` | `whether this calm reflects … one free weekend morning` | doubled modal *cannot … may*; **Saturday is invented** — the context says only "a weekend" |
| 40 | `Inviting him to describe the feeling of the scene, rather than its content, can open a conversation about mood that children often find easier through a drawing than through direct questions.` | `Asking how the scene feels, rather than what is in it, often opens up a conversation about mood, and children usually find that easier through a drawing than face to face.` | gerund subject plus a relative clause reaching back past two nouns |
| 48 | `creating a quiet narrative tension that is genuinely interesting. Something is in the middle of happening:` | `which leaves the scene in the middle of something:` | tells the reader it's interesting, then restates it |
| 48 | `his answer will likely surprise you.` | `his answer may surprise you.` | promises an outcome the report can't know |
| 59 | `the most universal symbols in early childhood drawing worldwide,` | `the most universal symbols in early childhood drawing,` | *universal* and *worldwide* say the same thing |
| 59 | `children at this stage often rely on known symbol-schemas as building blocks.` | `children at this stage often build from symbols they already know.` | untranslated academic jargon |
| 59 | `These are small but real authorial decisions within a conventional frame.` | `These are small but real choices of his own inside a familiar template.` | art-criticism register |
| 62 | `This invites the same organizational confidence he already has, but applied to a less familiar world.` | `That puts the organizing confidence he already has to work in a less familiar world.` | participle with nothing to attach to |
| 63 | `may appeal to Liam's existing visual sensibility.` | `may appeal to the way Liam already uses color.` | a critic's phrase about a six-year-old |
| 70 | `Composition shows an instinctive sense of horizontal organization … and handled capably here.` | `The composition shows an instinctive sense of horizontal organization … and handled well here.` | missing article (Slavic transfer); *capably* is flat officialese |
| 73 | `working on a non-white background often pushes children to make new color decisions` | `working on colored paper often pushes children to choose colors differently` | negated compound + nominalization |
| 74 | `"You might try a collaborative drawing sometime where you each add one element at a time, taking turns — it is low-pressure and often produces surprising compositions."` | `"Try drawing together sometime, taking turns to add one thing at a time — it’s low-pressure and often ends up somewhere surprising."` | clinical phrasing with a misused relative adverb |
| 81 | `a motor and spatial task that Liam handles adequately.` | `a hand-and-eye task that Liam handles well enough at this age.` | *adequately* is a cold verdict on the child |
| 81 | `fine motor precision is shown primarily through the management of basic geometric forms` | `his fine motor control shows mainly in how he handles basic shapes` | over-nominalized passive |
| 90 | `children often have complete stories attached to drawings that they simply haven't been asked to share. Listen without steering the narrative.` | `children often have a whole story in mind that no one has thought to ask about. Listen without steering the story.` | clause attaches to the wrong noun; register drift |
| 92 | `This simple invitation respects the fact that he knows more about his drawing than you do,` | `It treats him as the expert on his own drawing,` | hedging padding |
| 93 | `That kind of self-directed focus is worth noticing and naming warmly:` | `That kind of focus is worth saying out loud to him:` | parenting-coach jargon |
| 93 | `Pointing to the process — not just the result — helps him connect his effort to his own sense of capability.` | `Praising the effort rather than the picture helps him connect what he did with what he can do.` | *not just X* again + abstract psych-speak |
| 96 | `but adds a tactile, problem-solving dimension that children who like to organize scenes often find very satisfying.` | `but with scissors and glue it becomes a hands-on puzzle, which children who like organizing scenes often love.` | three abstractions doing one image's work |
| 97 | `(painting tissue paper with glue to create layered color sheets) could extend Liam's existing color confidence in a new direction.` | `(painting tissue paper with color, then cutting and gluing the pieces down) could take Liam’s color confidence somewhere new.` | **the parenthetical describes the method wrongly**; "extend in a new direction" is filler |
| 103 | `in a context where his independent working style would be genuinely valued — not as a concern, but as a natural next step` | `somewhere his independent way of working is genuinely valued, as a natural next step` | closes a 60-word sentence on two flagged patterns |
| 109, 113 | `…or engineering, as examples.` / `…or teaching, as examples.` | `…or engineering.` / `…or teaching.` | trailing "as examples" is a sentence-final «например» calque, redundant after "fields like" |
| 116 | `spent a free Saturday morning building … — no prompts, no help, no hesitation.` | `spent a free weekend morning building … , with no prompts and no help.` | Saturday invented again; *no X, no Y, no Z* triad |
| 116 | `That quality, more than any particular line or color, is what is worth noticing and holding onto.` | `That is the part worth holding on to.` | restates the previous sentence; *holding onto* → *holding on to* |

## §2e — remaining templates and `config/form_fields.py`

### F-195 `templates/_base.html:9`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `a PDF report on their development for parents. Not a diagnosis.`
- **REPLACE WITH:** `a PDF report for parents on how your child is developing. Not a diagnosis.`
- **Why:** "on their development for parents" stacks two modifiers so *their* reads as the drawing's. This is the site-wide default meta description.

### F-196 `templates/_header.html:10`
- **Severity:** optional · **Type:** translationese
- **CURRENT:** `alt="{{ site_name }} — a report on your child from their drawings">`
- **REPLACE WITH:** `alt="{{ site_name }} — a report about your child, based on their drawings">`
- **Why:** "a report on X from Y" chains two prepositions in a way that forces a re-read.

### F-197 `templates/_header.html:22`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `<a class="site-nav__login" href="{{ url_for('main.login') }}" data-goal="header_login">{{ _('Log in') }}</a>`
- **REPLACE WITH:** `<a class="site-nav__login" href="{{ url_for('main.login') }}" data-goal="header_login">{{ _('Sign in') }}</a>`
- **Why:** The page it links to is titled "Sign in" and the cabinet button says "Sign out", so the nav is the odd one out. The login email header says "login code" as well (F-215).

### F-198 `templates/order.html:79`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `<h3 style="margin-top:18px">{{ _('Delivery') }}</h3>`
- **REPLACE WITH:** `<h3 style="margin-top:18px">{{ _('Where to send it') }}</h3>`
- **Why:** *Delivery* suggests shipping a physical item; the section only collects an email address and a coupon.

### F-199 `templates/order.html:85`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `<p class="hint">{{ _('Educational observation, not a diagnosis. Money-back guarantee within 7 days.') }}</p>`
- **REPLACE WITH:** `<p class="hint">{{ _('Educational observation, not a diagnosis. 7-day money-back guarantee.') }}</p>`
- **Why:** US consumer copy fronts the period as a compound modifier; "guarantee within 7 days" reads as if the guarantee itself arrives within a week.

### F-200 `templates/cabinet.html:20`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `<p class="sub">{{ _('Nothing here yet — order your first report and it will show up in your account.') }}</p>`
- **REPLACE WITH:** `<p class="sub">{{ _('Nothing here yet — order your first report and it will show up right here.') }}</p>`
- **Why:** The parent is standing in the account, so telling her it will appear "in your account" restates the screen she is on.

### F-201 `templates/cabinet.html:34`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `<div class="hint">{{ _('order #%(id)s from %(date)s', id=o.id, date=o.date) }}</div>`
- **REPLACE WITH:** `<div class="hint">{{ _('order #%(id)s · %(date)s', id=o.id, date=o.date) }}</div>`
- **Why:** "order #12 from March 3" is the Russian «от» date construction; English uses *placed on* or just a separator.

### F-202 `templates/login.html:10`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{{ _('No passwords: we’ll email a 6-digit code to the address you used when ordering.') }}`
- **REPLACE WITH:** `{{ _('No password needed — we’ll email a 6-digit code to the address you used when you ordered.') }}`
- **Why:** Bare plural "No passwords" plus colon is a translated-label pattern, and "when ordering" is a gerund where English uses a clause.

### F-203 `templates/login.html:28`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `data-goal="login_request_code">{{ _('Get the code') }}</button>`
- **REPLACE WITH:** `data-goal="login_request_code">{{ _('Email me a code') }}</button>`
- **Why:** "Get the code" implies the code appears now; the button sends an email, and the definite article presumes a code already exists.

### F-204 `templates/login.html:35`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `<label for="code">{{ _('Code from the email for %(email)s', email=email) }}</label>`
- **REPLACE WITH:** `<label for="code">{{ _('Enter the code we sent to %(email)s', email=email) }}</label>`
- **Why:** "Code from the email for X" is a noun pile with an ambiguous *for*; the label should say what to do.

### F-205 `templates/login.html:52`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{{ _('your account opens automatically.') }}`
- **REPLACE WITH:** `{{ _('we’ll set up your account for you.') }}`
- **Why:** Accounts don't *open* themselves in English; the reflexive-automatic construction is a direct calque.

### F-206 `templates/sample.html:20`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `{{ _('This is what a warm, personal DrawReport looks like: scores across areas of development with clear explanations and ideas you can try at home. It’s an observation of what’s visible in the drawing — not a diagnosis.') }}`
- **REPLACE WITH:** `{{ _('This is what a report looks like: a score for each area of development, plain explanations, and ideas you can try at home. It’s an observation of what’s visible in the drawing — not a diagnosis.') }}`
- **Why:** Using the brand as a count noun ("a warm, personal DrawReport") plus self-praising adjectives is marketing register the voice guide rules out.

### F-207 `templates/sample.html:23`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `{% if s.n_drawings > 1 %}{{ _('example · %(n)s drawings', n=s.n_drawings) }}{% else %}{{ _('sample report') }}{% endif %}`
- **REPLACE WITH:** `{% if s.n_drawings > 1 %}{{ _('sample · %(n)s drawings', n=s.n_drawings) }}{% else %}{{ _('sample report') }}{% endif %}`
- **Why:** The same badge calls the same thing *example* in one branch and *sample* in the other, on a page whose heading says "Sample".

### F-208 `templates/sample.html:43`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `data-goal="sample_order">{{ _('Order a report on your own drawing') }}</a>`
- **REPLACE WITH:** `data-goal="sample_order">{{ _('Order a report on your child’s drawing') }}</a>`
- **Why:** "your own drawing" says the parent drew it, which inverts the entire product.

### F-209 `templates/sample.html:47`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{{ _('An educational observation grounded in the developmental stages of children’s art. Not a medical or psychological diagnosis.') }}`
- **REPLACE WITH:** `{{ _('An educational observation, based on what’s known about the developmental stages of children’s art. Not a medical or psychological diagnosis.') }}`
- **Why:** You cannot ground an observation *in stages*; English grounds it in knowledge or research about them.

### F-210 `templates/blog_post.html:40`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{{ _('Want a calm, educational look at your child’s drawings — from visible details, no diagnosis?') }}`
- **REPLACE WITH:** `{{ _('Want a calm, educational look at your child’s drawings — based on what’s on the page, not a diagnosis?') }}`
- **Why:** "from visible details, no diagnosis?" is a telegraphic tail with no verb.

### F-211 `templates/blog_post.html:44`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `data-goal="blogpost_order">{{ _('Get a report on a drawing') }}</a>`
- **REPLACE WITH:** `data-goal="blogpost_order">{{ _('Get a report on your child’s drawing') }}</a>`
- **Why:** "a drawing" is unowned and abstract at the exact point the reader has to decide it's about her kid.

### F-212 `templates/blog_post.html:45`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `data-goal="blogpost_sample_btn">{{ _('See an example') }}</a>`
- **REPLACE WITH:** `data-goal="blogpost_sample_btn">{{ _('See a sample analysis') }}</a>`
- **Why:** This button and the inline link five lines above point at the identical URL but are labelled differently, so they read as two destinations.

### F-213 `templates/error.html:8`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `{% if code == 404 %}{{ _('There’s no such page.') }}`
- **REPLACE WITH:** `{% if code == 404 %}{{ _('We couldn’t find that page.') }}`
- **Why:** "There's no such page" is «Такой страницы нет» word for word and lands as a flat contradiction of the visitor.

### F-214 `templates/error.html:11` (and `templates/stub.html:9`)
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `{{ _('Back to home') }}`
- **REPLACE WITH:** `{{ _('Back to the home page') }}`
- **Why:** "Back to home" drops the article the noun needs.

### F-215 `templates/checkout_stub.html:11`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `{{ _('This is a test checkout (no real charge). The PayPal checkout drops in here for launch.') }}`
- **REPLACE WITH:** `{{ _('This is a test checkout — no real charge. PayPal will go here.') }}`
- **Why:** "drops in here for launch" is developer shorthand exposed on a page a real customer could reach.

### F-216 `config/form_fields.py:16`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `"hint": "The name appears in the report - it's how we'll refer to the young artist"`
- **REPLACE WITH:** `"hint": "We'll use this name throughout the report"`
- **Why:** "the young artist" is arch in a way the rest of the site never is, and the ASCII hyphen renders as a hyphen (F-003).

### F-217 `config/form_fields.py:19`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"hint": "So we refer to your child correctly in the report"`
- **REPLACE WITH:** `"hint": "So we get your child's pronouns right in the report"`
- **Why:** "So we refer to X correctly" is stilted and vague; naming pronouns says exactly what the field controls.

### F-218 `config/form_fields.py:22`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `"hint": "Skills are judged relative to age - this is key information"`
- **REPLACE WITH:** `"hint": "Every skill is read against your child's age, so this one matters"`
- **Why:** *Judged* is a verdict word aimed at a worried parent, and "this is key information" is flat translated filler.

### F-219 `config/form_fields.py:28`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `{"key": "theme", "label": "What was asked / subject of the drawing", "type": "combo",`
- **REPLACE WITH:** `{"key": "theme", "label": "Subject of the drawing", "type": "combo",`
- **Why:** The slash label asks two questions in one line; the hint below already draws out whether it was assigned or chosen.

### F-220 `config/form_fields.py:31-33` — the preset list
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"presets": ["Free choice - drew whatever they wanted", "Draw the family",
                "Draw a person", "A favorite character or cartoon hero",
                "An animal", "A house", "Nature, a landscape",
                "A school or daycare assignment", "Copied from a model or from life"],`
- **REPLACE WITH:** `"presets": ["Their own idea — drew whatever they wanted", "Draw the family",
                "Draw a person", "A favorite character from a show, game, or book",
                "An animal", "A house", "A landscape or nature scene",
                "A school or daycare assignment", "Copied from a picture, or drawn from life"],`
- **Why:** "Free choice" is survey-instrument vocabulary; "cartoon hero" is «мультгерой» word for word; "Nature, a landscape" is two half-labels joined by a comma; "from a model" is studio-art vocabulary a parent won't map onto *copied a picture off the iPad*.

### F-221 `config/form_fields.py:39`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"hint": "The material shapes the lines - without it we might judge the tool instead of the child"`
- **REPLACE WITH:** `"hint": "What they drew with changes the line — without it, we might end up describing the marker instead of your child"`
- **Why:** Over-nominalized subject, the verdict word *judge* again, and the hyphen-as-dash.

### F-222 `config/form_fields.py:42-47`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `"options": [("under 5 minutes", "under 5 minutes"),`
- **REPLACE WITH:** `"options": [("under 5 minutes", "Under 5 minutes"),`
- **Why:** These are the only lowercase select options on the form (Girl/Boy and the presets are capitalized), so the dropdown looks unfinished. Applies to all six options.

### F-223 `config/form_fields.py:48`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"hint": "5 rushed minutes and half an hour of absorbed work are different stories"`
- **REPLACE WITH:** `"hint": "Five rushed minutes and half an hour of absorbed work tell us different things"`
- **Why:** "are different stories" is «разные истории»; US English says two things *tell you different things*.

### F-224 `config/form_fields.py:51`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `"hint": "\"First time\" is especially valuable: new details mark emerging skills"`
- **REPLACE WITH:** `"hint": "\"First time\" is worth a lot - a new detail usually means a new skill"`
- **Why:** "new details mark emerging skills" is clinical nominalization in a hint meant to coax an anecdote out of a parent.

### F-225 `config/form_fields.py:52-54`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `{"key": "extra", "label": "Any other context", "type": "textarea",` … `"hint": "Context changes the read: drew from life, was in a hurry, left-handed, just started drawing..."`
- **REPLACE WITH:** `{"key": "extra", "label": "Anything else we should know", "type": "textarea",` … `"hint": "Small things change the read - drew from life, was in a hurry, left-handed, only just started drawing"`
- **Why:** *Context* is analyst vocabulary repeated in label and hint; the trailing `...` is an ASCII ellipsis where the site uses a real one.

### F-226 `config/form_fields.py:58`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `"hint": "The PDF report and your account access go here"`
- **REPLACE WITH:** `"hint": "We'll send the PDF report here, along with the link to your account"`
- **Why:** "your account access go here" is a noun-phrase subject doing a verb's work, and *account access* is a system term rather than something a person receives.

### F-227 `config/form_fields.py:61`
- **Severity:** optional · **Type:** translationese
- **CURRENT:** `"hint": "The discount applies straight to the total"`
- **REPLACE WITH:** `"hint": "We'll take the discount off the total"`
- **Why:** "applies straight to" is a literal rendering; the active voice is clearer about who does what.

---

# §3 — Emails and PDF report strings

## §3a — transactional emails

### F-228 `templates/email/_email_base.html:12`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `This is an educational observation of the skills visible in a drawing,`
- **REPLACE WITH:** `This is an educational observation of what is visible in a drawing,`
- **Why:** Philosophy 2.3 reads the child *through* the drawing with skills as support, so "the skills visible" undersells it. The not-a-diagnosis claim is untouched.

### F-229 `templates/email/_email_base.html:14`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `Questions? Just reply to this email - we're happy to help.`
- **REPLACE WITH:** `Questions? Just reply to this email. We’re happy to help.`
- **Why:** Spaced ASCII hyphen as a dash reads as a typo; splitting the sentence avoids adding to the site's em-dash count.

### F-230 `templates/email/free_ready.html:7`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `It's a reading of one page: what's visible,`
- **REPLACE WITH:** `It’s a reading of one drawing: what’s visible,`
- **Why:** "a reading of one page" is ambiguous between *one sheet of paper* and *a one-page reading*, and the parent sent a drawing.

### F-231 `templates/email/free_ready.html:14`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `Read it</a>`
- **REPLACE WITH:** `Open your reading</a>`
- **Why:** "Read it" leaves the antecedent to the reader; the button should name what opens.

### F-232 `templates/email/free_ready.html:17`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `This is educational observation, not a diagnosis. We keep the photo for 90 days and then`
- **REPLACE WITH:** `This is an educational observation, not a diagnosis. We keep the photo for 90 days and then`
- **Why:** Missing article — *educational observation* is a count noun here, and every other instance on the site has *an*.

### F-233 `templates/email/free_ready.html:18`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `delete it; the reading stays at your link.`
- **REPLACE WITH:** `delete it; your reading stays at the link above.`
- **Why:** "stays at your link" is a calque; *your* belongs on the reading, not the link.

### F-234 `templates/email/free_save_place.html:8`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `Whenever you find a drawing, open this link and add the photo. You won't have to answer`
- **REPLACE WITH:** `Whenever you find a drawing, open this link and add a photo of it. You won’t have to answer`
- **Why:** Definite-article misuse — no specific photo exists yet. Same problem in the button on line 15 ("Add the drawing" → "Add your drawing").

### F-235 `templates/email/free_save_place.html:18`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `A reading of one drawing is free while we're launching.`
- **REPLACE WITH:** `A reading of one drawing is free during our launch.`
- **Why:** "while we're launching" describes an action in progress rather than a period. The free-during-launch claim is unchanged.

### F-236 `templates/email/insufficient.html:6`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `We looked at what you sent, but unfortunately we can't put together a full report from it yet.`
- **REPLACE WITH:** `We looked at what you sent, but we can’t put together a full report from it yet.`
- **Why:** Mid-sentence *unfortunately* is the stock translation of «к сожалению» and adds hedging the apology headline already covers.

### F-237 `templates/email/insufficient.html:14-15`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `re-run the analysis <b>for free</b>. If you'd prefer, we'll refund you in full - also by
replying to this email.`
- **REPLACE WITH:** `re-run the analysis <b>for free</b>. If you’d rather have a refund, just say so in your reply and
we’ll refund you in full.`
- **Why:** "also by replying to this email" dangles off the end with no verb to attach to. The full-refund offer is preserved.

### F-238 `templates/email/login_code.html:4`
- **Severity:** optional · **Type:** microcopy
- **CURRENT:** `<h2 style="font-size:22px; margin:0 0 14px">Your login code</h2>`
- **REPLACE WITH:** `<h2 style="font-size:22px; margin:0 0 14px">Your sign-in code</h2>`
- **Why:** The next sentence and the site page both say *sign in*, so *login* here is a third term for one thing (see F-197).

### F-239 `templates/email/login_code.html:6-7`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `It's valid for {{ ttl_minutes }} minutes` … `and works only once.`
- **REPLACE WITH:** `It’s good for {{ ttl_minutes }} minutes` … `and can only be used once.`
- **Why:** "valid for" is formal-legal register for a short note, and a code is *used* once, not *works* once. The expiry is unchanged.

### F-240 `templates/email/login_code.html:14`
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `If you didn't request a sign-in, just ignore this email.`
- **REPLACE WITH:** `If you didn’t try to sign in, you can ignore this email.`
- **Why:** "request a sign-in" is nominalized system language; the recipient thinks of it as *trying to sign in*.

### F-241 `templates/email/payment_received.html:6-7`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `Thank you! Your payment went through - we're already preparing the report.` … `It will arrive at this address in a separate email, usually within 10-15 minutes.`
- **REPLACE WITH:** `Thank you! Your payment went through, and we’re already working on your report.` … `We’ll send it to this address in a separate email, usually within 10-15 minutes.`
- **Why:** Hyphen-as-dash, "the report" should be "your report" for a message to one buyer, and "It will arrive at this address in a separate email" inverts agent and object the way a Russian impersonal does. Timing claim unchanged.

### F-242 `templates/email/payment_received.html:10-11`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `The report will always be available in your account. To open it any time, from any` … `device, sign in with this same email address - a login code will be sent to your inbox:`
- **REPLACE WITH:** `Your report also stays in your account. To open it anytime, from any` … `device, sign in with this same email address and we’ll email you a code:`
- **Why:** "will always be available" is SaaS register and an open-ended promise; US usage is the single word *anytime*; and the passive "a login code will be sent" hides who does it in a message that is otherwise first person.

### F-243 `templates/email/report_ready.html:4`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `<h2 style="font-size:22px; margin:0 0 14px">Your report is ready: {{ child_name }}</h2>`
- **REPLACE WITH:** `<h2 style="font-size:22px; margin:0 0 14px">{{ child_name }}’s report is ready</h2>`
- **Why:** "Label: value" reads like a database record; leading with the child's name is warmer and more natural.

### F-244 `templates/email/report_ready.html:7`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `prepared a warm, personal report: what's visible in`
- **REPLACE WITH:** `put together your report: what’s visible in`
- **Why:** The email should not grade its own tone; "warm, personal" is the self-praising adjective pair a parent reads as marketing.

### F-245 `templates/email/report_ready.html:9`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `can support at home. The PDF is attached to this email, and the online version is one click away:`
- **REPLACE WITH:** `can encourage at home. The PDF is attached to this email, and you can read it online too:`
- **Why:** "what you can support at home" has no object you can support, and "one click away" is a marketing cliché in a delivery email.

### F-246 `app/mailer.py:189` and `:197` — subject lines
- **Severity:** should-fix · **Type:** microcopy
- **CURRENT:** `    return send_email(to, f"Your place is saved - {settings.SITE_NAME}", html,` and `    return send_email(to, f"{name}'s drawing - your reading is ready", html,`
- **REPLACE WITH:** `    return send_email(to, "Your place is saved", html,` and `    return send_email(to, f"{name}'s drawing: your reading is ready", html,`
- **Why:** The spaced hyphen reads as a typo in an inbox list, and the brand already shows in the From name, so appending it makes the subject look like a mailing-list blast.
- **⚠️ Note:** the subject lines for the login-code, payment-received, report-ready and insufficient emails are **not** in `mailer.py` or the templates — they are set at the call sites (worker / auth / payments), which were outside this audit. Worth a follow-up pass.

## §3b — `pipeline/render.py` (fixed PDF labels) and `config/report_texts.json`

**One vocabulary decision governs most of this file:** `direction` as a translation of «направление» appears at lines 43, 46, 51, 53 and 67, plus `templates/landing.html:148` (F-154). English calls these **areas**. Decide once, apply everywhere.

### F-247 `pipeline/render.py:44`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `More on this in “How to read the scores in this report” at the end of the PDF.`
- **REPLACE WITH:** `More on this in “How to read the scores in this report” at the end of this report.`
- **Why:** The same string renders in the hosted HTML report at `/r/<token>`, where there is no PDF for the reader to look at.

### F-248 `pipeline/render.py:43`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `sometimes a direction is simply less visible in the chosen subject. `
- **REPLACE WITH:** `sometimes an area simply shows up less in the subject the child chose. `
- **Why:** The «направление» calque plus an agentless "the chosen subject".

### F-249 `pipeline/render.py:46`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `        "h_dimensions": "Direction by direction",`
- **REPLACE WITH:** `        "h_dimensions": "A closer look at each area",`
- **Why:** "Direction by direction" is not English for walking through the scored areas.

### F-250 `pipeline/render.py:47`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `        "activities_label": "How to develop this:",`
- **REPLACE WITH:** `        "activities_label": "Ways to build on this:",`
- **Why:** A direct rendering of «как это развивать» that lands as an instruction rather than a suggestion, which the report's voice avoids.

### F-251 `pipeline/render.py:51`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `Optional resources, not a sign that anything is wrong — just where to look if you'd like to explore a direction further.`
- **REPLACE WITH:** `Optional resources, not a sign that anything is wrong. This is simply where to look if you’d like to go further with one of these areas.`
- **Why:** Repeats the «направление» calque, and splitting the sentence removes one of four em dashes crowded into this block.

### F-252 `pipeline/render.py:53`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `        "h_directions": "Where to grow your child's strengths",`
- **REPLACE WITH:** `        "h_directions": "Ways to build on your child's strengths",`
- **Why:** "Where to grow strengths" pairs a locative *where* with a verb that takes no place, so the heading reads half-translated.

### F-253 `pipeline/render.py:54`
- **Severity:** must-fix · **Type:** ai-tell
- **CURRENT:** `Not a prediction of who your child will become — a hint of which directions may be joyful to grow in. Any fields named are examples, not a forecast.`
- **REPLACE WITH:** `These are areas that might be fun for your child to explore, not a prediction of who they will become. Any fields we name here are just examples.`
- **Why:** This is the "and a hint" artifact the V0.032 copy pass removed from the landing page, still live in the PDF — plus a not-X/dash construction and "joyful to grow in", which is not English. Both original claims (no prediction, examples only) are preserved.

### F-254 `pipeline/render.py:59`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `They are not a rating of the child as a person, not a school grade, and not a psychological diagnosis.`
- **REPLACE WITH:** `They are not a rating of the child as a person, a school grade, or a psychological diagnosis.`
- **Why:** Triple "not a…" parallelism is the repeated-negation tell; the single negation with a three-item series excludes exactly the same three things.

### F-255 `pipeline/render.py:67`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `“story & characters” direction may come through less. That doesn't mean `
- **REPLACE WITH:** `“story & characters” area may score lower. That doesn’t mean `
- **Why:** Same calque, and "come through less" is vague where *score lower* is what actually happened.

### F-256 `pipeline/render.py:70`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `It can mean the skill was only partly shown, or that the chosen subject gave less to observe.`
- **REPLACE WITH:** `It can mean the skill only partly showed up, or that the subject the child picked gave less to look at.`
- **Why:** "the chosen subject gave less to observe" is nominalized and passive in a way English does not build.

### F-257 `pipeline/render.py:73`
- **Severity:** must-fix · **Type:** translationese
- **CURRENT:** `A confident line, a large scale, neat filling, or a thought-out composition can all reflect well-developed graphic skills.`
- **REPLACE WITH:** `A confident line, drawing big, careful coloring in, or a well-planned composition can all reflect strong drawing skills.`
- **Why:** "neat filling" and "graphic skills" are word-for-word renderings a US parent will not recognize as descriptions of a child's drawing.

### F-258 `pipeline/render.py:76`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `A series of drawings from different periods gives a fuller picture — especially if you keep the works with their dates.`
- **REPLACE WITH:** `Several drawings made at different times give a fuller picture, especially if you write the date on the ones you keep.`
- **Why:** "from different periods" and "keep the works with their dates" is gallery phrasing for a child's drawings (F-006); the comma removes another em dash.

### F-259 `pipeline/render.py:78-79`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `("The point of the report isn't to assign a score,` … `"but to point out what's already going well and which simple activities you could `
- **REPLACE WITH:** `("The report isn't a scorecard.` … `"It's here to show what's already going well and to suggest a few simple things you could `
- **Why:** The bolded term cell ends mid-sentence on a comma, so the isn't-X-but-Y contrast is split across two visual elements and reads as a broken line as well as a flagged pattern.

### F-260 `pipeline/render.py:82`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `This report is a calm, educational observation of the skills visible in a drawing.`
- **REPLACE WITH:** `This report is an educational observation of what is visible in a drawing.`
- **Why:** *Calm* is the report describing its own manner, which native disclaimer copy does not do. The educational-observation framing is intact.

### F-261 `pipeline/render.py:84` **and** `config/report_texts.json:7`
- **Severity:** must-fix · **Type:** britishism
- **CURRENT:** `your child's wellbeing, behavior, or `
- **REPLACE WITH:** `your child's well-being, behavior, or `
- **Why:** Unhyphenated *wellbeing* is the British form; US style is *well-being*, and the neighboring *behavior* is already US spelling. Both files carry the same sentence.

### F-262 `config/report_texts.json:3` — the 1-drawing upsell
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `This portrait is built from a single drawing - an honest snapshot of one moment. From one drawing it isn't possible to tell a stable trait from a particular day's mood. If you'd like to see what repeats from drawing to drawing (and what was a one-off), send 2-3 works from different days - a series makes the picture far clearer than a single sheet.`
- **REPLACE WITH:** `This portrait comes from a single drawing: an honest snapshot of one moment. One drawing can't tell you whether something is a lasting trait or just that day's mood. If you'd like to see what repeats from drawing to drawing, and what was a one-time thing, send two or three drawings from different days. A series shows far more than a single sheet.`
- **Why:** Two hyphens as dashes, the impersonal "From one drawing it isn't possible to tell" is a direct Russian construction, and *works* is gallery register.

### F-263 `config/report_texts.json:4` — the 2-drawing upsell
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `This portrait is built from two drawings - already enough to see what repeats and what was a one-off. A third work from another day would make the picture of stable traits even more reliable.`
- **REPLACE WITH:** `This portrait comes from two drawings, which is already enough to see what repeats and what was a one-time thing. A third drawing from another day would make that picture even more reliable.`
- **Why:** Hyphen-as-dash, "A third work" again treats a child's drawing as an artwork, and "the picture of stable traits" is an over-nominalized noun stack.

### F-264 `config/report_texts.json:7` — the main disclaimer
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `is a suggestion grounded in the developmental and art literature, best explored in conversation with the child`
- **REPLACE WITH:** `is a suggestion grounded in research on child development and children's art, and something to explore in conversation with your child`
- **Why:** "the developmental and art literature" is an unidiomatic compressed noun phrase, and the sentence switches from *your child* to *the child* mid-clause. **The suggestion/hypothesis framing is preserved word for word** — this is the sentence the philosophy 2.3 safety frame rests on, so change only the wording flagged here.

### F-265 `config/report_texts.json:7`
- **Severity:** optional · **Type:** ai-tell
- **CURRENT:** `and a warm portrait of the child through their work`
- **REPLACE WITH:** `and a portrait of your child, seen through what they drew`
- **Why:** *Warm* is the report praising its own tone, and *their work* is the same gallery register as the upsell blocks.

### F-266 `config/report_texts.json:9`
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** ` Remember: this is a reading of one drawing - one moment, not the full picture of a child's development.`
- **REPLACE WITH:** ` Keep in mind that this is a reading of one drawing: one moment, not the full picture of a child's development.`
- **Why:** *Remember:* is the command tone the brand rules ban, and the hyphen is standing in for a dash. **Keep the leading space** — this string is appended to the main disclaimer.

---

# §4 — Blog posts and legal pages

## §4a — `content/en/blog/is-a-childs-drawing-a-diagnosis.md`

### F-267 line 2 — title
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `title: Is a child’s drawing a diagnosis? (No — and here’s what it actually shows)`
- **REPLACE WITH:** `title: Is a child’s drawing a diagnosis? (No. Here’s what it does show.)`
- **Why:** Question-plus-em-dash-parenthetical is a stock AI headline shape, and *actually* is filler in a title that already answers itself. This string renders in the landing carousel and in search results.

### F-268 line 3 — description
- **Severity:** optional · **Type:** ai-tell
- **CURRENT:** `description: A child’s drawing isn’t a psychological test. Here’s the honest, educational way to read one — by what’s visible on the page.`
- **REPLACE WITH:** `description: A child’s drawing isn’t a psychological test. Here’s the honest way to read one: by what’s visible on the page.`
- **Why:** "honest, educational" stacks two self-praising adjectives and the em dash does a colon's job.

### F-269 line 11
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `children's drawing actually works.`
- **REPLACE WITH:** `children's drawings actually work.`
- **Why:** "children's drawing" as an uncountable field term is academic register lifted from the source; a US parent reads *drawings*.

### F-270 line 16
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `mean sadness. One dark picture doesn't reveal a hidden problem. Real child psychologists are`
- **REPLACE WITH:** `mean sadness. One dark picture doesn't reveal a hidden problem. Child psychologists are`
- **Why:** *Real* implies the ones the reader has read are fakes — a defensive swipe the calm voice doesn't need.

### F-271 line 17
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `careful here for a good reason: reading emotions or diagnoses from a picture isn't supported`
- **REPLACE WITH:** `careful here for a good reason: reading a child's feelings, or a diagnosis, from a picture isn't supported`
- **Why:** You can read emotions from a picture but you cannot *read diagnoses* from one — the coordination forces a wrong collocation.

### F-272 line 22
- **Severity:** optional · **Type:** ai-tell
- **CURRENT:** `What a drawing *does* show — clearly and usefully — is **skills**. How a child uses the page.`
- **REPLACE WITH:** `What a drawing *does* show, clearly and usefully, is **skills**. How a child uses the page.`
- **Why:** This post already carries em dashes on lines 31 and 35; commas here cut the density.

### F-273 line 23
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `How confidently the line moves. Whether shapes hold together. How color is chosen and applied.`
- **REPLACE WITH:** `How steady the lines are. Whether shapes hold together. How your child picks and puts down color.`
- **Why:** "the line moves" makes the line the actor and "is chosen and applied" is agentless passive — both are art-criticism phrasing rather than how a US writer describes a kid drawing.

### F-274 line 24
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `Whether there's a story. These are visible, real, and they develop in fairly predictable`
- **REPLACE WITH:** `Whether there's a story. All of it is visible and real, and it develops in fairly predictable`
- **Why:** "visible, real, and they develop" coordinates two adjectives with a full clause — faulty parallelism.

### F-275 line 29
- **Severity:** optional · **Type:** translationese
- **CURRENT:** `The approach we take is simple: tie every observation to something **you can actually see**`
- **REPLACE WITH:** `Our approach is simple: tie every observation to something **you can actually see**`
- **Why:** "The approach we take is" is a five-word wind-up where English uses a possessive.

### F-276 line 31
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `a thoughtful layout, careful filling — these point to developing graphic skills, not to a`
- **REPLACE WITH:** `a thoughtful layout, neat coloring-in: these point to developing drawing skills rather than to a`
- **Why:** "careful filling" and "graphic skills" are calques of art-school terms. Same pair as `pipeline/render.py:73` (F-257) — fix consistently.

### F-277 line 32
- **Severity:** optional · **Type:** ai-tell
- **CURRENT:** `diagnosis. From there, the useful question isn't "what's wrong?" but "what's already going`
- **REPLACE WITH:** `diagnosis. From there, the useful question is "what's already going`
- **Why:** Fourth not-X-but-Y construction in this post, and the piece has already made the "not wrong" point twice.

### F-278 line 35
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `That's the whole idea: a calm, educational look at what your child can do — not a verdict on`
- **REPLACE WITH:** `That's the whole idea: a calm look at what your child can do, not a verdict on`
- **Why:** A closing paragraph that restates the article plus an em-dash contrast is the classic AI sign-off.

## §4b — `content/en/blog/my-child-only-draws-in-black.md`

### F-279 line 3 — description
- **Severity:** optional · **Type:** tone
- **CURRENT:** `description: A calm, evidence-based take on the “black drawings” worry, and what a single color choice really tells you.`
- **REPLACE WITH:** `description: Why a one-color phase is almost never a warning sign, and what a color choice really does tell you.`
- **Why:** "a take on the worry" is bloggy meta-writing and "evidence-based" is researcher vocabulary aimed at a parent scanning search results.

### F-280 line 16
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `right now — a normal stage where the shape of things matters more than filling them with color.`
- **REPLACE WITH:** `right now — a normal stage where the shapes of things matter more than filling them in with color.`
- **Why:** Singular *the shape* cannot be the antecedent of *them*, and the idiom is *filling them in*.

### F-281 line 17
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `Sometimes it's simply the pen that was closest.`
- **REPLACE WITH:** `Sometimes it's just whichever marker was closest.`
- **Why:** Present-tense *it's* clashes with past *that was*, and the paragraph has been talking about markers, not pens.

### F-282 line 22
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `myth — it isn't supported by careful research, and treating it as a signal tends to create worry`
- **REPLACE WITH:** `myth. The research doesn't support it, and treating it as a signal tends to create worry`
- **Why:** "careful research" is a literal rendering of the Russian collocation for serious studies.

### F-283 line 23
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `where there's none. We never interpret a child's feelings from their palette.`
- **REPLACE WITH:** `where there's none. We never read a child's feelings from their color choices.`
- **Why:** *Palette* is fine-art vocabulary for a box of markers, and *interpret* is stiff next to the rest of the post.

### F-284 line 27
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `If you're curious, look at the **skills**: Is the line confident? Are shapes holding together?`
- **REPLACE WITH:** `If you're curious, look at the **skills**: Are the lines steady? Do the shapes hold together?`
- **Why:** "Are shapes" is missing its article, and "Is the line confident?" personifies the line the way the source language does.

### F-285 line 30
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `in this house?" — and offer a few colors nearby, no pressure.`
- **REPLACE WITH:** `in this house?" Leave a few other colors within reach, and let it go at that.`
- **Why:** An imperative is grafted by em dash onto a sentence whose subject is "the gentlest nudge", so the clause has no grammatical anchor.

### F-286 line 32
- **Severity:** optional · **Type:** error
- **CURRENT:** `More often than not, the colors come back on their own.`
- **REPLACE WITH:** `More often than not, the other colors come back on their own.`
- **Why:** Black is a color too, so without *other* the closing line contradicts the premise.

## §4c — `content/en/blog/what-you-can-learn-from-a-drawing.md`

### F-287 line 3 — description
- **Severity:** should-fix · **Type:** tone
- **CURRENT:** `description: Beyond “a house and a sun” — the visible skills a drawing reveals, and simple ways to support them at home.`
- **REPLACE WITH:** `description: Beyond “a house and a sun”: the visible skills a drawing shows, and simple ways to support them at home.`
- **Why:** The sibling post attacks the claim that a drawing *reveals* things, so using that verb in a carousel blurb undercuts the site's own position.

### F-288 lines 14-19 — the skills list
- **Severity:** should-fix · **Type:** translationese
- Apply as one pass; every bullet hides the child behind an agentless passive or an abstraction.

| line | CURRENT | REPLACE WITH |
|---|---|---|
| 14 | `- **Creativity & imagination** — unusual choices, going beyond the template.` | `- **Creativity & imagination** — unusual choices that go past the usual house and sun.` |
| 15 | `- **Color & light** — how colors are chosen, combined, and applied.` | `- **Color & light** — how your child picks colors and puts them down.` |
| 16 | `- **Composition & space** — how the page is used and how elements hold together.` | `- **Composition & space** — how much of the page gets used and how the parts fit together.` |
| 17 | `- **Technique & materials** — control of the pencil, marker, or paint.` | `- **Technique & materials** — how well your child handles a pencil, marker, or brush.` |
| 19 | `- **Form & proportions** — how the shape of things is rendered.` | `- **Form & proportions** — how close the shapes and sizes come to the real thing.` |

- **Why:** *the template*, *elements*, *is rendered*, *control of the pencil* — four abstractions and three agentless passives in a six-item list about a child.

### F-289 line 22
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `Each of these is **visible**. You're not inferring feelings — you're noticing what the hand and`
- **REPLACE WITH:** `Each of these is **visible**. You're not guessing at feelings. You're noticing what your child's hand and`
- **Why:** "the hand and eye" as free-floating body parts is a source-language construction, and the em-dash contrast repeats a pattern used in every post.

### F-290 lines 27-29
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `It's to notice a strength and offer a next step. Saw a` … `confident, large figure? Try a big sheet and "draw it in one line." Lots of careful little` … `patterns? Offer borders and decorative motifs. Only one character and no scene? Suggest a story`
- **REPLACE WITH:** `It's to notice a strength and offer a next step. See a` … `large, confident figure? Try a big sheet and "draw it in one line." Lots of careful little` … `patterns? Draw a frame around the page and let them fill it. Only one character and no scene? Suggest a story`
- **Why:** Three problems in one sequence: *Saw a* breaks the tenseless "See X? Try Y" pattern of the surrounding prompts; English adjective order puts size before opinion (*large, confident*, not *confident, large*); and "decorative motifs" is art-teacher vocabulary that leaves the parent with nothing to actually do.

### F-291 line 32
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `Small, specific, ten-minute invitations — that's how a quiet observation turns into real support.`
- **REPLACE WITH:** `A ten-minute invitation like that is usually all it takes.`
- **Why:** Rule-of-three fragment plus em dash plus an abstract-noun summary of the paragraph above it — the most recognizable AI closing line in the set.

## §4d — `app/legal.py` (privacy, terms, refund)

> These pages are marked DRAFT and have not been reviewed by counsel. **Every replacement below is a language fix that preserves the legal meaning exactly**; where a clause is load-bearing, the Why line says so. Nothing here is legal advice, and none of it substitutes for the counsel review already on the project's open-items list.

### F-292 `app/legal.py:17`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `DrawReport ("we") helps a parent or guardian receive an educational report about their`
- **REPLACE WITH:** `DrawReport ("we," "us") gives a parent or guardian an educational report about their`
- **Why:** "helps a parent receive" is indirect for a service that simply provides the report, and US policies define both *we* and *us* when both are used later.

### F-293 `app/legal.py:24`
- **Severity:** must-fix · **Type:** error
- **CURRENT:** `birth month/year) **on the child's behalf and with their consent as the child's parent**.`
- **REPLACE WITH:** `birth month/year) **on the child's behalf and, as that child's parent or guardian, consents to it**.`
- **Why:** *their consent* most naturally points back to the child, inverting the COPPA point this clause exists to make. The replacement keeps the same legal meaning with the parent unambiguously giving consent. ⚠️ Load-bearing — flag it in the counsel review.

### F-294 `app/legal.py:28`
- **Severity:** optional · **Type:** translationese
- **CURRENT:** `- Your email address (to deliver the report and provide account access).`
- **REPLACE WITH:** `- Your email address (so we can send you the report and let you sign in).`
- **Why:** "provide account access" is nominalized where plain-English consumer policies use verbs.

### F-295 `app/legal.py:29`
- **Severity:** should-fix · **Type:** britishism
- **CURRENT:** `- Payment is processed by **PayPal**; we do not receive or store your full card details.`
- **REPLACE WITH:** `- No card data: payment is handled by **PayPal**, and we do not receive or store your full card number.`
- **Why:** "card details" is UK/AU usage where US sites say *card number*, and as written the bullet sits under "What we collect" while describing something you do **not** collect.

### F-296 `app/legal.py:30-31`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `- Basic, privacy-preserving web analytics. For geography we derive only an approximate` / `  region from your IP address and store **only that derived label — never the IP itself**.`
- **REPLACE WITH:** `- Basic, privacy-friendly web analytics. To get a rough location, we work out an approximate` / `  region from your IP address and store **only that region name, never the IP address itself**.`
- **Why:** "For geography we derive" fronts an abstract noun the way the source language does, and "derived label" is internal engineering vocabulary. The commitment — region only, never the IP — is preserved exactly.

### F-297 `app/legal.py:36`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `and never sold or shared with third parties**, except service providers strictly necessary`
- **REPLACE WITH:** `and never sold or shared with third parties**, other than service providers that are strictly necessary`
- **Why:** "except service providers" needs *other than* / *except for* to attach to "third parties". ⚠️ Load-bearing carve-out — the exception's scope is unchanged.

### F-298 `app/legal.py:37`
- **Severity:** must-fix · **Type:** britishism
- **CURRENT:** `to run the service (e.g. the report-generation and email providers).`
- **REPLACE WITH:** `to run the service (for example, our report-generation and email providers).`
- **Why:** US style requires a comma after *e.g.*; spelling it out is cleaner in consumer-facing text.

### F-299 `app/legal.py:40`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `You may request deletion of your drawings, report, and account data at any time by replying`
- **REPLACE WITH:** `You can ask us to delete your drawings, report, and account data at any time by replying`
- **Why:** "request deletion of" is the nominalized register the rest of this policy avoids. The right being granted is identical.

### F-300 `app/legal.py:45`
- **Severity:** optional · **Type:** tone
- **CURRENT:** `Questions or deletion requests: reply to any email from us.`
- **REPLACE WITH:** `Questions, or want your data deleted? Just reply to any email from us.`
- **Why:** Repeats the instruction given five lines earlier in the same clipped noun-stack style.

### F-301 `app/legal.py:50`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `By using DrawReport you agree to these terms.`
- **REPLACE WITH:** `By using DrawReport, you agree to these terms.`
- **Why:** A fronted participial phrase takes a comma.

### F-302 `app/legal.py:54`
- **Severity:** optional · **Type:** translationese
- **CURRENT:** `set against the typical developmental stages of children's art. It is **not** a medical,`
- **REPLACE WITH:** `alongside the typical developmental stages of children's art. It is **not** a medical,`
- **Why:** "set against" reads as *in opposition to* as often as *compared with*, which is not the intended sense.

### F-303 `app/legal.py:56`
- **Severity:** should-fix · **Type:** ai-tell
- **CURRENT:** `generated with the help of AI and are intended as a warm, educational read — not a clinical`
- **REPLACE WITH:** `generated with the help of AI and are meant to be read as a warm, educational observation, not a clinical`
- **Why:** The em-dash not-X contrast restates the disclaimer made one sentence earlier. Both the AI disclosure and the not-clinical carve-out are intact.

### F-304 `app/legal.py:60`
- **Severity:** should-fix · **Type:** translationese
- **CURRENT:** `Access to your reports is by email sign-in (a one-time code). Keep access to your email secure.`
- **REPLACE WITH:** `You sign in to your reports with a one-time code sent to your email. Keep your email account secure.`
- **Why:** Both sentences turn actions into abstract nouns; the replacement states the same obligation directly.

### F-305 `app/legal.py:66`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `Upload only drawings you have the right to share, made by your own child or a child for whom`
- **REPLACE WITH:** `Upload only drawings that you have the right to share and that were made by your own child, or by a child for whom`
- **Why:** "made by your own child" dangles after a relative clause and can be misread as modifying *the right*. ⚠️ Load-bearing — both conditions keep the same force.

### F-306 `app/legal.py:71`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `liable for indirect or consequential damages. Nothing here limits rights that cannot be`
- **REPLACE WITH:** `liable for indirect or consequential damages. Nothing in these terms takes away rights that cannot be`
- **Why:** "Nothing here limits rights that cannot be limited" repeats *limit* against itself and reads as a tautology. ⚠️ Savings clause — same effect preserved.

### F-307 `app/legal.py:81`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `refund your payment — no fuss. Just reply to the email your report came in, or contact support.`
- **REPLACE WITH:** `refund your payment, no hassle. Just reply to the email your report arrived in, or contact support.`
- **Why:** "the email your report came in" is missing its complement and reads unfinished, and *no fuss* is the Britishism from F-164.

### F-308 `app/legal.py:83`
- **Severity:** should-fix · **Type:** error
- **CURRENT:** `### Couldn't make a report`
- **REPLACE WITH:** `### If we can't make a report`
- **Why:** A subjectless past-tense fragment as a rendered heading reads like a log entry, not a policy section.

### F-309 `app/legal.py:84`
- **Severity:** optional · **Type:** error
- **CURRENT:** `If we can't produce a meaningful report from the photos you sent (for example, the image isn't`
- **REPLACE WITH:** `If we can't produce a meaningful report from the photos you sent (for example, the photo isn't`
- **Why:** The sentence switches from *photos* to *the image* and back to *new photos*; use one noun throughout.

---

# Appendix A — How this was verified

Every claim in this report was checked against the source, not recalled:

1. **Quotes are verbatim.** `CURRENT` strings were copied from the staged files, not retyped. Curly vs. straight apostrophes in the quotes reflect what is actually in the file.
2. **The apostrophe and hyphen counts in §0 are measured**, not estimated — per-file counts of `'` vs `’` are in the F-002 table.
3. **The British-spelling list in F-004 is a grep result**, with line numbers, not an impression.
4. **The three conflicting word budgets (F-101, F-102, F-125) were confirmed** by reading all three sources: `free_prompt.py:55`, `free_prompt.py:100` vs `:180`, and `free_schema.py:34,40`.
5. **The missing article in the footer disclaimer (F-001) was confirmed in both files** — `_base.html:49` and `landing.html:327` — and its absence elsewhere (`order.html:85`, `order_success.html:14`, `app/routes.py:96` all correctly say "not a diagnosis").
6. **Rendered-vs-source discipline (UseCase #20) was respected**: findings are only included where the string actually reaches a visitor. Three candidate findings were **dropped** for failing this test:
   - `templates/landing.html:352` contains `behaviour` (British) — it is inside a JavaScript comment.
   - `app/mailer.py:187` contains `to hand` — it is inside a docstring.
   - `config/free_texts.py:253` contains `to hand` — it is inside a code comment.
   - `app/free.py` and `app/free_jobs.py` were checked and contain **no** visitor-facing English; all their text comes from `config/free_texts.py`.
7. **`templates/report.html` has no fixed English of its own** — every label comes from `REPORT_STRINGS`, so all PDF-label fixes live in `pipeline/render.py`.

# Appendix B — Cross-file couplings (apply these together or not at all)

| Change | Files that must move together |
|---|---|
| The hedge list `"may speak of"` → `"may point to"` | `pipeline/free_prompt.py:106`, `:141` **and `pipeline/free_lint.py`** — the linter checks the same list and will strip the new hedges if it isn't updated in the same commit |
| `"in the tradition of reading children's drawings"` | `pipeline/free_prompt.py:105`, `:130` **and** `templates/free_result.html:51` — the label and the generated sentence beneath it currently repeat the same calque |
| `direction` → `area` | `pipeline/render.py` 43, 46, 51, 53, 67 **and** `templates/landing.html:148` |
| The seven dimension names | `config/free_texts.py:273-278`, `pipeline/render.py`, `templates/report.html` — these three lists already disagree on case and connector (F-056). Reconcile in one pass or leave alone |
| The refund-window wording | `templates/landing.html:260` **and** `config/free_texts.py:292` |
| `"no fuss"` → `"no hassle"` | `templates/landing.html:226`, `app/content.py:42`, `app/legal.py:81` |
| The free CTA label | `templates/home.html:44,113`, `templates/_header.html:26`, `templates/landing.html:216,279`, `config/free_texts.py:371` |
| The "medium / scale" bullet | `templates/home.html:78` **and** `config/free_texts.py:359` |
| `wellbeing` → `well-being` | `pipeline/render.py:84` **and** `config/report_texts.json:7` |

# Appendix C — Out of scope, worth a follow-up

1. **`pipeline/prompt.py`** — the *paid* report prompt was not audited. Given what §1d found in the free prompt (British spellings, calqued examples, mandatory sentence templates, and no real English-voice instruction), the paid prompt is very likely carrying the same problems into the eight-page PDF that customers pay $29 for. **This is the single most valuable follow-up.** The `pipeline/samples/sample_report.json` findings in §2d are indirect evidence: that file is real output from this pipeline, and it contains "not just X, but Y" twice, `as examples` twice, `symbol-schemas`, `authorial decisions within a conventional frame`, and an invented Saturday.
2. **Email subject lines set at the call sites** (worker / auth / payments) — four subjects were not reachable from the audited files (see F-246).
3. **`pipeline/free_lint.py`** — not audited, but coupled to F-109 (see Appendix B).
4. **Admin UI** — deliberately excluded as internal.
5. **The `en` translation catalog is empty and uncompiled**, so every `_('...')` returns its msgid. All fixes above are therefore edits to the msgid itself. If a second locale is ever added, these strings become the source msgids and the fixes must land *before* extraction, or every catalog inherits the translated-sounding English.
