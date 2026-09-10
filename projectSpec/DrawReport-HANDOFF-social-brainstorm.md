# HANDOFF — social media plan for DrawReport (for brainstorming)

Paste this into a fresh chat. It is self-contained; no repo access needed.

## The product

**DrawReport** (drawreport.com) — a parent uploads 1–3 photos of their child's drawing, pays $29,
and gets an 8-page PDF: an educational observation of the child through the drawing (character,
themes, interests, developmental stage), plus simple at-home activities. Live, taking real payments.
There is also a **free reading** funnel — 3 questions, upload one drawing, get a short reading — which
is the main front door and feeds the paid product.

Audience: US parents of children roughly 3–12. English only. Sold to US residents only.

## The goal

Get social accounts running, then eventually generate and publish content automatically.
Nothing exists yet — zero social presence today.

## Hard constraints (these are not preferences)

1. **We can never post a customer's drawing.** The live Privacy Policy and Terms promise that
   customer drawings are never published and never used in advertising. Content can only come from:
   our own three sample reports, original illustrations we make, and educational writing about
   children's developmental art stages.
2. **"Educational observation, not a medical or psychological diagnosis."** This framing is legally
   load-bearing (FTC claims) and appears on every page. Social copy must never drift into
   "find out what your child's drawing reveals about their problems" territory, however well it
   would perform.
3. **Children's data / COPPA.** The product is sold to parents, not children. Nothing addressed to
   kids, no child-facing content.

## Decisions already made

- **Use Postiz Cloud** (postiz.com), ~$29/month, monthly not annual at first.
  Reason: on their cloud plan you connect accounts by simple OAuth login. Self-hosting Postiz would
  force us to register our own developer app with Meta, TikTok, Pinterest etc. — weeks of approvals,
  which is the exact pain we are paying to skip. Self-hosting was rejected for that reason, and also
  because our server (3.8 GB RAM, no swap) already runs two other production apps.
- **One Postiz account covers all projects.** Its "Customers" grouping separates brands; the plan
  price scales with number of connected accounts, not number of projects. Standard (5 accounts) for
  DrawReport alone; Team ($39, 10) once a second project joins.
- **Postiz does not create accounts.** Signup, phone verification, CAPTCHA and 2FA are all manual
  and human. Postiz only connects to accounts that already exist.
- **Test TikTok during the free trial before paying** — unaudited TikTok API clients can only post
  privately, and it is unconfirmed whether Postiz Cloud's client is audited.
- **Instagram must be a Professional/Business account linked to a Facebook Page** from the start.

## What to brainstorm

1. **Which platforms, and in what order?** Pinterest looks like the strongest fit (visual, parenting,
   long content half-life, search-driven). Instagram second. Open question: TikTok/Reels — high
   reach, but is short video realistic to sustain, and does it suit a $29 considered purchase?
2. **What is the content, given we cannot show customer drawings?** This is the central creative
   problem. Ideas needed for a repeatable format that is genuinely useful to a parent and does not
   depend on user uploads.
3. **Handle and brand voice** — one handle across platforms, warm and parent-facing, never clinical,
   never alarming.
4. **Posting cadence** that one person plus AI assistance can actually sustain.
5. **How the free reading fits** — it is the natural call to action (costs the parent nothing), but
   each free reading costs us an LLM call, so the funnel has a real unit cost.

## What happens next (not part of the brainstorm)

A separate Claude Code session will: create the accounts together with the owner (he does every
signup, password and verification step personally), set up the profiles, then connect them to Postiz.
Much later, a third project builds automated content generation — our admin panel generates posts and
pushes them to Postiz via its public API, so we never write per-platform posting code.
