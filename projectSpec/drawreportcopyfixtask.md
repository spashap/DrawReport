# Task: Copy edit — DrawReport `/en/` and `/en/report`

## Goal

Fix the English on two pages so they read as native US-American consumer copy, and remove the remaining "written by an LLM" tells. **Copy only.** Do not change layout, components, styling, routing, or logic. If the copy lives in i18n files, edit the `en` values and leave keys and all other locales untouched.

Two pages:

- `https://drawreport.com/en/` — the short free-reading landing page (footer shows `V0.027`)
- `https://drawreport.com/en/report` — the long paid-report page (footer shows `V0.028`)

## Ground rules

1. Preserve meaning and the existing voice: warm, calm, plain, parent-facing. Do not make it more corporate.
2. Do not lengthen the pages. Several fixes are deletions.
3. Keep contractions. The pages use them; stay consistent.
4. Where a replacement below is given, use it. Where a *direction* is given, exercise judgment but stay within the voice.
5. After editing, run the verification checklist at the bottom.

---

## Part 0 — Global fixes (both pages)

### 0.1 Typography normalization

Current state on `/en/report`: 33 curly apostrophes vs **25 straight**, 4 curly quotes vs **8 straight**, and **10 spaced hyphens (` - `) used as dashes** alongside 31 em dashes. `/en/` is nearly clean (1 straight apostrophe).

Normalize across both pages:

- All apostrophes → `’` (U+2019). Currently wrong in most FAQ answers, the "For example" blocks, and the pricing card.
- All quotation marks → `“ ”` (U+201C/U+201D). Currently wrong in `"hidden trauma"`, `"unsociable"`, `"black drawings"`, `"a house and a sun"`.
- All ` - ` used as a dash → ` — ` (spaced em dash, matching the rest of the page). 10 occurrences, all in the "For example" blocks and FAQ answers.
- Do **not** touch hyphens in compounds (`literature-grounded`, `plain-language`, `2-3 minute`, `4-year-old`) or the en dashes in ranges (`1–3`, `7 days`).

### 0.2 Remove the dev version string

`V0.027` and `V0.028` are rendered in the public footer. Hide them in production (env-gate or remove).

### 0.3 Footer disclaimer parity

`/en/` footer says **"Educational observation, not medical diagnosis"**.
`/en/report` footer says **"Educational observation, not medical or psychological diagnosis"**.

Use the longer version on both. The homepage leads with monsters, weapons, drawing alone, and pressing hard — the psychological disclaimer is the one that matters there.

### 0.4 One phrase appears on both pages and is wrong on both

Find: `grounded in the developmental and art literature`
Replace: `grounded in developmental and art-education research`

(Also appears as `literature-grounded` — see §2.4.)

---

## Part 1 — `/en/` (free-reading landing page)

### 1.1 Britishism — highest priority

| Find | Replace |
|---|---|
| `No drawing to hand right now? That’s fine — you can start without a photo and add it later.` | `Don’t have a drawing handy? That’s fine — you can start without a photo and add it later.` |

"To hand" is British. This is the single clearest non-US marker on the site.

### 1.2 Section intro

| Find | Replace |
|---|---|
| `Parents usually arrive with one of these` | `Most parents come to us with one of these` |
| `Any of them is a good enough reason to look at one drawing properly.` | `Any one of these is reason enough to take a closer look.` |

`arrive with` is not idiomatic; `properly` as an intensifier is British-flavored.

### 1.3 The concern list — parallelism and one translation artifact

Six of seven bullets start with a verb; one is a bare noun phrase. One bullet mixes tenses. `schematic` is a word no US parent uses about a drawing.

| Find | Replace |
|---|---|
| `People with no faces or hands, very schematic` | `Draws people with no faces or hands, just outlines` |
| `Stopped drawing, or gives up when it doesn't come out right` | `Has stopped drawing, or gives up when it doesn’t come out right` |

(The second one also carries the page's only straight apostrophe.)

### 1.4 The "or maybe nothing's wrong" line

| Find | Replace |
|---|---|
| `Or nothing worries you at all and you’re simply curious what the drawing says about your child — that’s one of the options too.` | `Or nothing worries you at all and you’re simply curious about what the drawing says — that’s a good enough reason too.` |

`curious what` needs a preposition; `that’s one of the options too` is translated-sounding.

### 1.5 "What you get back" bullets

| Find | Replace |
|---|---|
| `the details that are easy to walk past` | `the details that are easy to miss` |
| `One detail worth holding on to` | `One detail worth a second look` |
| `the theme holding your child right now` | `what’s got your child’s attention right now` |
| `And what this one page honestly cannot show` | `And what this one page can’t show` |

Notes: you walk past objects, not details on a page. "Holding on to" means keeping, not pausing on. "Holding" is not transitive that way. `cannot` clashes with the contraction-heavy voice — and dropping `honestly` here fixes the duplicate flagged in §1.8.

**Keep `their answer beats any adult’s guess` exactly as is.** It is the best line on the page.

### 1.6 Disclaimer sentence — missing comma

| Find | Replace |
|---|---|
| `We don’t detect hidden problems and we don’t read fortunes in colors.` | `We don’t detect hidden problems, and we don’t read fortunes in colors.` |

Two independent clauses joined by "and" need the comma.

### 1.7 "How it works" steps

| Find | Replace |
|---|---|
| `and one thing to look at yourself` | `and one thing to check on your own` |
| `Photograph the whole sheet in ordinary light.` | `Take a photo of the whole sheet in normal daylight.` |
| `The reading comes back in about a minute, here and by email.` | `You’ll get it in about a minute — here and by email.` |

`one thing to look at yourself` briefly parses as "look at yourself." `Photograph` as an imperative and `ordinary light` are both a register off for US consumer copy.

### 1.8 Remaining AI tells on this page

Only two left. The page is otherwise clean.

- **`honestly` twice in close proximity** — "what your answers and your child's age can honestly tell you" and "what this one page honestly cannot show." §1.5 removes the second one. Keep the first.
- **The hero tricolon is restated as bullets.** The hero promises "what's actually visible on the page, what that detail may mean, and what to ask your child today," and then "What you get back" re-lists the same three things expanded. Tighten the hero to one clean promise and let the bullets itemize. Suggested hero: `Tell us what you noticed, and we’ll read one drawing for you — starting from what’s actually visible on the page.`

### 1.9 Closing cross-link

| Find | Replace |
|---|---|
| `Looking for the full picture rather than one drawing?` | `Looking for the full picture instead of one drawing?` |

Also consider `seven dimensions` → `seven areas` for consistency with `/en/report`, which says "7 areas of development."

---

## Part 2 — `/en/report` (paid report page)

This page has had the least attention and carries most of the remaining problems.

### 2.1 "What you'll learn" bullets

| Find | Replace |
|---|---|
| `The worlds and themes that draw your child — what they choose to put on the page` | `The worlds and themes your child is drawn to — what they choose to put on the page` |
| `And, in support: the drawing skills coming along — technique, detail, fine motor` | `Plus the supporting skills — technique, detail, and fine motor control` |

The first has the verb backwards and, on a drawing site, reads as an accidental pun. The second is not English: `in support` is not a phrase, `skills coming along` is off, and `fine motor` is missing its noun.

### 2.2 The phrase "and a hint" — delete all three occurrences

`a hint` (singular, unmodified) is a direct-translation artifact. In English it means nothing here.

| Find | Replace |
|---|---|
| `as a suggestion and a hint, never a diagnosis` | `as a suggestion, never a diagnosis` |
| `we offer careful, literature-grounded suggestions and a hint — anchored to what’s visible` | `we offer careful, research-grounded pointers — anchored to what’s visible` |
| `careful, literature-grounded suggestions and a hint, not a diagnosis and not fortune-telling` | `careful, research-grounded pointers — not a diagnosis, and not fortune-telling` |

### 2.3 The "For example" block — the clunkiest section on the site

Current structure: a heading reading `For example, situations like these`, followed by four paragraphs that each open with `For example, a situation like this:`. Five instances of the same frame in one section.

**Delete the frame entirely.** Keep the heading (rename to something like `What this looks like in practice`) and start each paragraph with the scenario itself:

- `A child draws only in black for a few weeks and a parent starts to worry. The report calmly shows…`
- `A child draws the same little house over and over. We help you see…`
- `There’s almost always a single character and no other people. We don’t jump to…`
- `You send three drawings from different days. We show what repeats…`

While in this block:

| Find | Replace |
|---|---|
| `We don't conclude "unsociable"` | `We don’t jump to “your child isn’t social”` |

`conclude` needs an object clause, and `unsociable` is British-leaning.

Also fix the spaced hyphens throughout this block per §0.1.

### 2.4 "No myths" section

| Find | Replace |
|---|---|
| `we lean on real methods (Piaget, Lowenfeld, Vygotsky) and the developmental stages of children’s art` | `we draw on established developmental frameworks (Piaget, Lowenfeld, Vygotsky) and the stages of children’s art` |
| `Think of it as a tool to understand your child through their drawing` | `It’s a way to understand your child through their drawing` |

Piaget, Lowenfeld and Vygotsky are theorists, not methods — and "real methods" sounds defensive, as if answering an accusation the reader hasn't made. `Think of it as…` is a very common LLM framing move.

### 2.5 "How the conclusion is built" — the most obviously generated passage

| Find | Replace |
|---|---|
| `Read in the developmental tradition, an image like this can look like warmth moving through something difficult — a suggestion, not a conclusion.` | `In the developmental literature, an image like this often reads as warmth moving through something hard. A suggestion — not a conclusion.` |

Double-hedged and near-meaningless as written. Rewrite for concreteness; the replacement above is a floor, not a ceiling.

**Then delete the sentence that restates the diagram.** Immediately after the three-panel graphic (`A VISIBLE DETAIL → A GENTLE HYPOTHESIS → WHAT TO ASK YOUR CHILD`), the page says:

> `That’s how the report works: a visible detail → a careful, literature-grounded suggestion → a way back to your child. Never a diagnosis.`

This repeats the graphic in prose one line later. Cut everything before `Never a diagnosis.` — or cut the sentence entirely, since §2.7 shows the page already over-uses that disclaimer.

### 2.6 "How it works" steps and FAQ

| Find | Replace |
|---|---|
| `Nothing needs to be drawn specially.` (2 occurrences — step 1 and the last FAQ) | `Nothing has to be drawn just for this.` |
| `Usually within the hour.` | `Usually within an hour.` |
| `Open real examples: inside you’ll find the drawing, the context, strengths, observations, and activities for parents.` | `Open a real example — you’ll see the drawing, the context, strengths, observations, and activities for parents.` |
| `What you can try at home — after every area` | `Things to try at home, after every area` |

`specially` is the wrong register; `within the hour` reads British.

### 2.7 Fix the self-contradiction in the FAQ

FAQ #1 ends: `It is not a diagnosis and not a judgment of your child’s personality or state.`
FAQ #2 opens: `The report judges skills relative to what’s typical for your child’s age…`

| Find | Replace |
|---|---|
| `The report judges skills relative to what’s typical for your child’s age` | `The report reads skills against what’s typical for your child’s age` |

### 2.8 The negation-contrast reflex — the main AI tell on this page

The construction "not X / never X" appears **at least eight times**:

1. `who they are, not how they hold a pencil`
2. `a suggestion, not a conclusion`
3. `Never a diagnosis.`
4. `as a suggestion and a hint, never a diagnosis`
5. `not a diagnosis and not fortune-telling`
6. `We don’t hunt for hidden diagnoses…`
7. the whole `What we don’t do` column
8. `It is not a diagnosis and not a judgment…` (FAQ)

Any one of these is good copy. Eight is a fingerprint. **Keep three at most**: the `What we don’t do` column (it earns its place — it's the differentiator), the FAQ answer (a direct question deserves a direct denial), and one in the hero area. Cut the rest. §2.2 and §2.5 already remove two.

### 2.9 Other AI tells to thin out on this page

- **Em dash density**: 31 in ~1,300 words, most in the same rhythm — statement, dash, gentle qualifier. `/en/` runs 5. Target roughly half the current count. The archetype to break up: `The mood their drawings carry — offered gently, as a suggestion to explore, never a verdict`.
- **Rule-of-three lists**: `order, warmth, and the familiar` / `their worlds, character, and the mood` / `line, color, and scale` / `the line, the shapes, the details, the composition`. Break two of these into a different shape.
- **Soothing-adjective saturation**: *gently, calmly, warm, careful, gentle hypothesis, warm little bird, calm answers*. Cut roughly a third.
- **`grounded in`** appears 4× (see §0.4 — vary the rest).

**Keep `Most parents don’t want to raise an artist — they want to understand their child.`** It is the strongest line on the page and does not read as generated.

### 2.10 The new free-reading CTA blocks

| Find | Replace |
|---|---|
| `A similar story?` | `Sound familiar?` |
| `Something in the drawings worrying you?` | `Is something in the drawings worrying you?` |

**Keep `there is almost always something behind it, and almost never the thing parents fear`** — that line works.

---

## Verification checklist

Run against both pages after editing:

- [ ] Zero straight apostrophes (`'`) and zero straight quotes (`"`) in rendered body copy
- [ ] Zero occurrences of ` - ` used as a dash
- [ ] Zero occurrences of: `to hand`, `in support:`, `and a hint`, `very schematic`, `unsociable`, `real methods`, `specially`, `walk past`, `within the hour`, `For example, a situation like this`
- [ ] Zero occurrences of `the developmental and art literature`
- [ ] `V0.0xx` not present in the production footer
- [ ] Both footers read `Educational observation, not medical or psychological diagnosis`
- [ ] `not a diagnosis` / `never a diagnosis` appears **at most 3 times** on `/en/report`
- [ ] Em dash count on `/en/report` is roughly halved
- [ ] Every bullet in the `/en/` concern list starts with a present-tense verb
- [ ] No FAQ answer contradicts another
- [ ] Word count on each page is the same or lower than before
- [ ] Run the final copy through a US spellcheck (`color`, `honor`, `-ize` endings — currently correct, keep it that way)

## Out of scope

Layout, styling, component structure, routing, pricing, images, the sample-report contents, other locales, and the blog. Copy only.
