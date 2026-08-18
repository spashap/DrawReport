# TASK — paid report prompt **en-4.2**: move the report to the north star

**Target files:** `pipeline/prompt.py` (primary) · `pipeline/lint.py` · `pipeline/render.py` · `templates/report.html` · `static/css/report.css`
**Baseline:** `main` @ V0.036, `PROMPT_VERSION = "en-4.1"`
**Bump to:** `PROMPT_VERSION = "en-4.2"`, VERSION → 0.037

---

## 0. Read this before you start

**This task builds ON en-4.1. Do not redo it.** en-4.1 already added the `HOW THE ENGLISH MUST SOUND` section, de-templated the observation formula and the canned openers, killed the studio-critic vocabulary and the sentence-final "as examples" calque, and coupled `ATTRIBUTION` in `pipeline/lint.py`. All of that is working and stays.

**Owner's scope rule for the REPORT (differs from the website).** Inside a generated report, AI-style tells are accepted: em-dash density, "not X, but Y", occasional British spelling. The report is visibly machine-generated — nobody produces eight pages in two minutes — and no reader audits its prose style. **Professional and readable is the bar here.** Do not spend effort, prompt text, or linter rules on report prose style. The strict native-US-English standard applies to the WEBSITE front end, which is a different task and unaffected by this one.

**This task is about WHAT the report talks about, not how the English sounds.** One rule change here touches the safe frame (§3.6) and it only ADDS a ban. Nothing else in this task changes a zone, a score band, a frame condition, a disclaimer, or any legal wording.

**Do not touch, at all:**
- The 4-condition SAFE FRAME (`prompt.py:70-80`) and the gold-standard zone-3 sentence.
- The three zones (`prompt.py:65-68`) and their balance.
- The scoring bands and score-variety rules (`prompt.py:119-126`).
- Any "educational observation, not a diagnosis" wording anywhere.
- `ALWAYS FORBIDDEN` (`prompt.py:82-90`) — except to ADD one item, per §3.6.
- The 7 direction keys, titles, or order (`DIMENSIONS`, `prompt.py:42-52`). Their **weight** changes; their identity does not.

---

## 1. The north star this is moving toward

Owner's words, verbatim:

> A mother that buys this report gets the promise she will understand her child's inner world better. She doesn't pay to get information how to make her child better at drawing — she wants to get tools of how to develop it better. Speak emotions and inner world. Recommend good development ways using drawing. Discover potential, within the legal framework. Make it the best $29 investment a parent made.

Restated as a test for every sentence in the report: **does this sentence tell the mother something about her child, or does it tell her something about drawing?** The second kind is allowed as support and must never be the product.

---

## 2. Evidence — what two shipped en-4.1 reports actually do

Generated 2026-08-18 with en-4.1: `Alisia M., 4y4m` (1 drawing, 9 pages, 2,870 words) and `Dilan K., 6y5m` (3 drawings, 11 pages, 3,465 words).

| Measured | Alisia | Dilan | Verdict |
|---|---|---|---|
| Cyrillic footer lines in the PDF | 9 / 9 pages | 11 / 11 pages | **ship-blocker** |
| "Ways to build on this" bullets | 23 | 26 | too many, and drifting off-promise |
| Art-supply / material purchase suggestions | 5 | 7 | off north star |
| Explicit fine-motor drills (bead-stringing, dot-to-dot, origami, playdough) | 1 | 1 | off north star |
| Activities with a name / title | **0** | **0** | craft gap vs the Russian benchmark (8) |
| "You could" / "You might" openers | 9 | 13 | the prompt itself mandates this phrasing |
| Em dashes (en-4.1 rule: max 2) | 1 | **58** | *measurement only — style is accepted per §0. Kept here because it proves the point below.* |
| "not X, but Y" (en-4.1 banned) | 3 | 1 | *same — evidence, not a target* |
| Same observed fact reused as evidence across directions | `hair` ×16, `layer` ×10, `earrings` ×9 | — | padding; single-drawing structural failure |

**The two things this table says.** First: the off-north-star content is not model drift, it is **prescribed by the prompt** — lines 138, 143, 145, 195 and 199 all bake `"you could offer…"` and *materials* into the contract. Second, and this is the transferable lesson: the en-4.1 rules hold on a short report and collapse on a long one — 1 em dash vs 58, same prompt, same day. Nobody cares about the dashes (§0). What matters is that **a prompt rule with nothing enforcing it is a suggestion**, so the rules in this task that DO matter — no drills, no normality verdicts — get linter backing rather than more prompt text.

---

## 3. Prompt changes — `pipeline/prompt.py`

### 3.1 Activities must change something between parent and child

**`prompt.py:137-139`**

CURRENT:
```
HOW TO DEVELOP (activities inside a direction):
- 1-3 activities per direction, concrete and doable at home with ordinary materials, phrased "you could offer…". For the skill directions (5-7), keep them shorter.
- For the personality directions, activities can be about UNDERSTANDING the child (what to ask, what to notice), not only technique.
```

REPLACE WITH:
```
HOW TO DEVELOP (activities inside a direction):
- 1-2 activities per direction. Directions 6 and 7 get at most ONE, and it must be a shared activity, never an exercise.
- EVERY activity must change something BETWEEN the parent and the child: a question to ask, something to notice together, a story to make up, a moment to share. The parent bought this report to understand her child, not to improve the drawing.
- AT MOST ONE activity in the WHOLE report may suggest a material to buy or try (a different pen, bigger paper, pastels). If you have already used it, you have none left. A report that reads as a shopping list has failed.
- NEVER a skill drill. No fine-motor exercises, no bead-stringing, dot-to-dot, mazes, origami, playdough, tracing, graphic dictation, handwriting practice. Those belong in an occupational-therapy handout, not here.
- NAME EACH ACTIVITY. Open it with a short title in quotes, like a game the family can call by name, then one or two sentences of how it goes: "What happened next?", "Draw the feeling", "Tell me about this one". A named game is an invitation; an unnamed bullet is homework.
- Prefer a direct invitation over a hedge where the activity costs nothing: "Ask Dilan what the big bird was doing first", "Sit with her while she draws and say out loud what you notice". "You could" / "You might" stay available and are still required for anything involving a purchase or a claim. The ban on command tone (buy / you must / be sure to) is unchanged and absolute. No counting rule here — this is a preference, not a check.
```

### 3.2 Creative activities section — cap the materials

**`prompt.py:145`**

CURRENT:
```
art_recommendations — CREATIVE ACTIVITIES (the smaller other half): 2-3 items phrased "you could offer…": materials/techniques, an activity or mini-project, what to draw inspiration from (illustrators, folk art, patterns, picture-book art).
```

REPLACE WITH:
```
art_recommendations — CREATIVE ACTIVITIES (the smaller other half): 2-3 named items. At most ONE may be about materials, and only if you have not already spent the report's single materials suggestion inside a direction. The others are things done together: a mini-project the parent and child build, a book to look at side by side, a way to give the child's drawings a place in the house. Name each one, as in the directions.
```

### 3.3 Directions 6 and 7 shrink

**`prompt.py:134-135`**

CURRENT:
```
6. technique_and_materials — "Technique & materials" (zone 1, support): technique, color, composition, how carefully it is done, how well the child handles the tool — kept COMPACT. No longer the substance of the report.
7. fine_motor — "Fine motor & detail" (zone 1, support): fine motor control, precision of small movements, detailing, patterns.
```

REPLACE WITH:
```
6. technique_and_materials — "Technique & materials" (zone 1, support): technique, color, composition, how carefully it is done, how well the child handles the tool. HARD CAP: 2 sentences, one activity. This is credibility for the rest of the report, not the report.
7. fine_motor — "Fine motor & detail" (zone 1, support): fine motor control, precision of small movements, detailing, patterns. HARD CAP: 2 sentences, one activity. Say what the hand can already do and move on. Never turn this into an exercise plan.
```

### 3.4 Stop reusing the same fact as evidence everywhere

**Insert after `prompt.py:93`** (the PERSONALIZATION block), as its own paragraph:

```
NO RECYCLING: a visible fact may carry AT MOST TWO directions. If the hair took twenty minutes, that fact can anchor two observations — not seven. When a direction has no evidence of its own, say so in one honest sentence and keep it short; do not re-dress a fact you have already used. A report where the same three details reappear under seven headings reads as padding, and the parent feels it by the third section.
```

### 3.5 Length must follow the material, not the template

**Insert after `prompt.py:117`** (the end of the FOG block):

```
LENGTH FOLLOWS THE MATERIAL: one simple drawing by a young child does not contain seven sections' worth of evidence. Total observation text across the seven directions: about 550-750 words for ONE drawing, 900-1200 for two or three. Under-filling a direction honestly is correct; padding it is a failure. Never stretch to fill the structure.
```

### 3.6 Ban normality verdicts about the child — **legal, do not skip**

**Add to `ALWAYS FORBIDDEN`, after `prompt.py:87`:**

```
- Normality verdicts about THIS child: "this is normal and healthy for her", "your child is developing normally", "nothing here is a concern", "this is within the normal range". You may state a general developmental fact ("at four, drawing a face with no body is common"), because that is about children in general. The moment it becomes a judgment about the child in front of you, it is a screening claim, and this report does not screen. The same applies in the other direction: never imply a child should be seen by anyone because of what a drawing shows. The specialists field is an opportunity, never a finding.
```

**Reason:** en-4.1 output already produced *"which at this age is a normal and healthy part of how young children begin to understand identity"* (Alisia, About your child). Benign about earrings; the identical sentence shape becomes a reassurance verdict the moment the subject is a worry. This is the highest-consequence line in the task — false reassurance is the failure that could actually harm a child and the business.

### 3.7 Attribution wordings — **considered and deliberately dropped, do not do this**

An earlier draft of this task rewrote the five sanctioned attribution forms at `prompt.py:73`, because they are all variants of one construction ("in the <X> of reading children's drawings") and shipped output used three of them across two reports.

**Dropped by owner decision (§0): this is report prose style, which is accepted as-is.** It also carried real breakage risk — `ATTRIBUTION` in `pipeline/lint.py:111` matches those exact forms, so changing them without changing the linter in the same commit makes the linter flag correctly framed sentences and triggers pointless repair rounds.

Leave `prompt.py:73` and `lint.py:111` alone. Do not "improve" them while working nearby.

### 3.8 JSON contract must show the new shapes

**`prompt.py:195`** CURRENT: `"activities": ["you could offer … / you could ask … 1", "you might try … 2"]`
REPLACE WITH: `"activities": ["\"Short game name\": one or two sentences of how it goes, about the parent and the child together", "…at most 2 per direction, 1 for directions 6-7"]`

**`prompt.py:199`** CURRENT: `"art_recommendations": ["2-3 items about creative activities phrased 'you could offer': materials, an activity, what to draw inspiration from"]`
REPLACE WITH: `"art_recommendations": ["2-3 named items, at most one about materials; the rest are things done together"]`

**`prompt.py:198`** — leave `understanding_recommendations` as is. It is already the most on-north-star part of the report and it works.

---

## 4. Companion fixes (not the prompt)

### 4.1 🔴 The PDF footer is in Russian on every page — **ship-blocker**

`static/css/report.css:12`:
```css
content: "Голос рисунка · образовательное наблюдение, не диагностика · стр. " counter(page);
```

Every page of every English PDF a customer has ever received carries this. Fix it the i18n-correct way (UseCase #6 — content differs by locale, logic does not):

1. Add to `REPORT_STRINGS["en"]` in `pipeline/render.py`: `"page_footer": "DrawReport · educational observation, not a diagnosis · p. "`
2. In `templates/report.html`, emit an inline `@page { @bottom-center { content: "{{ S.page_footer }}" counter(page); … } }` block in the head, and delete the hardcoded `@bottom-center` content from `report.css` (keep the font/size/color declarations).
3. While you are in `report.css`, its header comment block is also Russian — translate it. Cosmetic, but the file is now English-only.

### 4.2 Enforce in the linter what the prompt cannot hold

`pipeline/lint.py`. The reason is measured: en-4.1 rules held on the short report and collapsed on the long one. Only the rules that carry product or legal weight go in — **no style checks** (§0).

Add mechanical checks over the interpretation fields, each raising a normal violation so the existing repair pass fixes it:
- the words `drill`, `dot-to-dot`, `bead-stringing`, `origami`, `playdough`, `tracing`, `handwriting practice` anywhere in `activities` or `art_recommendations` → violation
- `normal and healthy`, `developing normally`, `within the normal range`, `nothing to worry about`, `no cause for concern` in any interpretation field → **hard** violation (§3.6)

Do NOT add em-dash counting, "not X, but Y" detection, or any other prose-style check. Do NOT touch `ATTRIBUTION` (§3.7).

---

## 5. Acceptance — regenerate both samples and measure

Re-run the two 2026-08-18 inputs (Alisia 1 drawing, Dilan 3 drawings) through `scripts/generate_report.py` and check the produced JSON + PDF:

| # | Check | Pass |
|---|---|---|
| 1 | Cyrillic characters anywhere in the PDF | **0** |
| 2 | Suggestions to buy or try a material, whole report | ≤ 1 |
| 3 | Fine-motor drills / exercises | **0** |
| 4 | Activities opening with a quoted name | ≥ 90% |
| 5 | Any single visible fact used as evidence in > 2 directions | **0** |
| 6 | Directions 6 and 7 | ≤ 2 sentences, ≤ 1 activity each |
| 7 | Alisia total word count | 1,700-2,100 (was 2,870) |
| 8 | Normality verdicts about the child | **0** |
| 9 | Linter on both reports | 0 violations |
| 10 | Safe frame present on every zone-3 sentence | unchanged — re-verify manually |
| 11 | Embedded PDF fonts | only Caveat / Inter / Rubik subsets (UseCase #2, #18) |

Not checked, on purpose: em-dash count, "not X, but Y", British spelling, sentence-shape variety. Report prose style is accepted as-is per §0.

**The judgment check, after the counts pass.** Read the Alisia report as her mother. Is there a sentence she would read out loud to someone? Is there more about Alisia than about crayons? If both are no, the counts passed and the task did not.

---

## 6. Housekeeping

- `PROMPT_VERSION = "en-4.2"` with a changelog comment in the existing style, noting: activities re-pointed at parent-and-child, materials capped at one, drills banned, activities named, directions 6-7 capped, no-recycling and length-follows-material rules, normality verdicts added to ALWAYS FORBIDDEN, linter extended for drills and normality verdicts. NO prose-style changes in this version.
- Bump `VERSION` to 0.037.
- Add a `UseCasesData.md` entry: **a prompt rule with no linter behind it holds on short output and collapses on long output** — measured at 1 em dash vs 58 from the same prompt on two reports generated the same day. The dashes themselves don't matter (report prose style is accepted); the lesson is that any rule that DOES matter needs enforcement in `lint.py`, not more prompt text.
- Also record the scope split: **strict native-US-English applies to the website front end, not to generated report prose.**
- Append the session to `DevelopmentStatus.md` per convention.

## 7. Out of scope

Website copy (`/en/`, `/en/report`, the freemium wizard), `pipeline/free_prompt.py`, and the seven-direction taxonomy itself. If the report ends up with much thinner technique sections, `/en/report` and `config/products.json` still read true — but flag it to the owner rather than editing marketing copy in this task.
