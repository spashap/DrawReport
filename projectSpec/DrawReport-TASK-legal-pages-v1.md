# TASK — legal pages: take them out of DRAFT and make them fit the business

**Target files:** `app/legal.py` (primary) · `templates/order.html` · `templates/_free_summary.html` · `config/settings.py`
**Baseline:** `main` @ V0.036 · **Bump to:** VERSION 0.038

> ## ⚠️ Read this first
> This task was drafted by an AI assistant, not by a lawyer, and it is not legal advice. It fixes structural gaps that are visible from the outside — a missing contracting party, undisclosed data recipients, absent standard clauses — and it produces text that is materially better than what is live today. **It does not replace review by a US attorney**, which this business needs because it handles children's data and takes payment.
>
> The existing pages carry a public "DRAFT — to be reviewed by counsel" banner. That banner is removed by this task. **Removing it is not the same as having had the review.** It comes off because announcing to a paying customer that your terms are unfinished is worse than saying nothing — it is a written admission you knew they were unreviewed when you contracted with her. Book the review.

---

## 0. Decisions this task is built on (owner, this session)

| Decision | Consequence for the drafting |
|---|---|
| **US-only. Not selling to EU/UK.** | No GDPR articles, no lawful-basis section, no cookie-consent gate, no 14-day withdrawal right. Replaced by an explicit US-residents-only term. |
| **Operating as an individual / sole trader.** | The contracting party is a named person, not a company. Placeholders `[FULL LEGAL NAME]` and `[BUSINESS ADDRESS]` throughout. |
| **Contact = `team@drawreport.com`.** | Published on all three pages. No new aliases. ⚠️ `config/settings.py:213` defaults `MAIL_FROM_EMAIL` to `hello@drawreport.com` while the server sends from `team@` — confirm which mailbox is actually monitored before publishing it as the privacy contact. |

**Out of scope because of those decisions:** GDPR data-subject-rights section, international-transfer clause, cookie consent banner, EU distance-selling withdrawal checkbox. If EU sales are ever turned on, all four come back and that is a separate project.

**CCPA/CPRA note:** California's law applies above thresholds (roughly $25M revenue, 100k consumers, or selling data) that this business does not meet today, so no CCPA section is included. **COPPA has no such threshold and applies now** — which is why the children's-data section is strengthened rather than trimmed.

---

## 1. Ship-blockers

### 1.1 The public DRAFT banner
`app/legal.py` lines 15, 49, 77 each begin the page body with:
```
**DRAFT — to be reviewed by counsel before launch. Not legal advice.**
```
Live on all three pages while PayPal is in live mode. **Delete all three lines.** The replacement bodies in §2 do not contain it.

### 1.2 There is no acceptance step anywhere
`templates/order.html` contains **no link to the Terms and no acceptance control** — verified by grep: zero matches for `terms`, `legal`, or `agree`. The Terms open with "By using DrawReport, you agree to these terms," which is browsewrap: the weakest form of assent, and routinely unenforced by US courts where the user had no reasonable notice. A checkout that never shows the terms is the weakest version of that.

Fixed in §3.1. This is arguably more valuable than any wording change in §2 — good terms that were never presented are hard to rely on.

---

## 2. `app/legal.py` — replacement page bodies

Replace the three markdown bodies in `_PAGES["en"]` entirely. Structure, `get_legal()`, and `legal_keys()` are unchanged.

### 2.1 Privacy Policy — replace the body at `legal.py:14-47`

```markdown
_Last updated: [DATE]_

DrawReport is operated by [FULL LEGAL NAME], [BUSINESS ADDRESS], United States
("we," "us"). We give a parent or guardian an educational report about their child's
drawing. This policy explains what we collect, who it goes to, and how long we keep it.

Questions about this policy, or about your data: **team@drawreport.com**.

### Who this service is for
DrawReport is offered to residents of the United States who are 18 or older. It is
intended for **parents and guardians**, not for children.

### Children's data (COPPA)
We do not knowingly collect personal information directly from children under 13.
A parent or guardian uploads their child's drawing and provides limited context — the
child's first name, gender, and birth month and year — **on the child's behalf, and as
that child's parent or guardian, consents to it**.

We use a child's information for one purpose only: producing the report that parent
asked for. We do not use it to build profiles, we do not use it for advertising, we do
not use it to train AI models, and we do not sell it. A parent can withdraw consent and
have the child's drawings and information deleted at any time by emailing
**team@drawreport.com**.

### What we collect
- **The drawing images you upload** and the context you type about the drawing and the child.
- **Your email address**, so we can send you the report and let you sign in.
- **Payment**: handled entirely by PayPal. We receive confirmation that a payment succeeded.
  We never see or store your card number.
- **Basic web analytics**: which pages were visited, on what kind of device, and how you
  reached the site. To get a rough location we look up an approximate region from your IP
  address and store **only that region name — the IP address itself is never stored**.

### Cookies
We use a small number of first-party cookies. We do not use advertising cookies and we
do not allow third parties to track you across other websites.

- `dr_s` — identifies a single visit, expires after 30 minutes of inactivity.
- `dr_v` — an anonymous visitor identifier so repeat visits are not double-counted.
- `dr_utm` — remembers how you first found the site (for example, a search or a link).
- A sign-in cookie, set only after you sign in, which keeps you signed in.

You can clear or block cookies in your browser. Blocking them does not stop you ordering
or reading a report.

### Who else sees your data
We do not sell your data and we do not share it for anyone else's marketing. Your child's
drawings are **never published and never used in advertising**. We use a small number of
service providers, each of which receives only what it needs to do its job:

- **Anthropic** — the AI service that generates the report. It receives the drawing image
  and the context you entered. Under Anthropic's commercial terms, data sent through their
  API is not used to train their models.
- **Brevo** — sends the emails that deliver your report and your sign-in codes. Receives
  your email address.
- **PayPal** — processes payment. Receives what it needs to take the payment; we do not
  pass it your child's drawing or the report.
- **Our hosting provider**, which stores the site's data on our behalf.

We may also disclose information if the law requires it.

### How long we keep things
- **Free readings**: the uploaded photo is deleted **90 days** after the reading. The text
  of the reading stays at your link.
- **Paid reports**: we keep the drawings and the report in your account so you can return
  to them. Ask us to delete them at any time and we will.
- **Order and payment records**: kept **7 years**, because tax and accounting rules require it.
- **Analytics records**: kept **24 months**, then deleted.

### Your choices
Email **team@drawreport.com** to:
- get a copy of what we hold about you,
- correct something that is wrong,
- delete your drawings, reports, and account.

We will respond within 30 days. Deleting your account does not delete the order records
we are required to keep.

### Security
Traffic to the site is encrypted. Access to reports is by a one-time code sent to your
email, so keeping your email account secure matters.

### Changes
If we change this policy we will update the date at the top. If a change materially
affects how we handle your data, we will email people who have an account.
```

### 2.2 Terms of Service — replace the body at `legal.py:48-75`

```markdown
_Last updated: [DATE]_

These terms are an agreement between you and [FULL LEGAL NAME], [BUSINESS ADDRESS],
United States ("we," "us"), who operates DrawReport. By ordering a report or using the
free reading, you agree to them.

### Who can use DrawReport
You must be **18 or older** and a **resident of the United States**. We offer the service
in the United States only, and we do not offer it to residents of the European Union or
the United Kingdom.

### What the service is — and what it is not
DrawReport provides an **educational observation** of what is visible in a child's
drawing, alongside the typical developmental stages of children's art.

It is **not** a medical, psychological, or diagnostic service, it is **not** a substitute
for professional advice, and it must not be relied on to decide whether a child needs
care. If you have concerns about your child's health, development, or wellbeing, speak
to a pediatrician or a qualified professional. A drawing cannot tell you that, and neither
can we.

Reports are **generated with the help of AI**. The observations in them are suggestions
based on what is visible in the image and what you told us. **They may be incomplete or
wrong.** Read them as one perspective to explore with your child, not as findings.

### Your child's drawings — who owns what
You keep every right you have in your child's drawings. Uploading a drawing gives us a
limited licence to store it and process it **for the single purpose of producing and
delivering your report**, and for nothing else. We claim no ownership of your child's
artwork. We do not publish it, we do not use it in advertising, and we do not use it to
train AI models.

The report we deliver is yours to keep, print, and share with family, teachers, or a
professional. Please do not resell it or republish it as your own work.

### Accounts
You sign in with a one-time code sent to your email address. Anyone with access to that
email can reach your reports, so keep it secure.

### Payment
Payments are processed by PayPal. Prices are shown in US dollars before you pay. The price
covers one report for one to three drawings from the same period.

### Refunds
Set out in our Refund Policy, which forms part of these terms.

### Acceptable use
Upload only drawings that you have the right to share, and that were made by your own
child or by a child for whom you are the parent or legal guardian. Do not upload unlawful
content, anyone else's work, or images that are not a child's drawing. We may decline or
stop providing the service to anyone who breaks these terms, and we will refund any
payment for a report we decline to produce.

### Availability
We aim to deliver reports promptly but do not guarantee uninterrupted service. Delivery
times quoted on the site are estimates.

### Disclaimer and limit of liability
The service is provided **"as is" and without warranties of any kind**, including any
warranty that the observations in a report are accurate or complete.

To the maximum extent permitted by law, our total liability arising out of or relating to
the service is limited to **the amount you paid us for the report in question**, and we
are not liable for indirect, incidental, or consequential damages. Nothing in these terms
limits liability that cannot be limited under applicable law, including liability for
fraud or for death or personal injury caused by negligence.

### Changes to these terms
We may update these terms. The date at the top shows when they last changed, and changes
apply to orders placed after that date.

### Governing law
These terms are governed by the laws of [STATE], United States, and you and we agree that
any dispute will be brought in the state or federal courts located in [COUNTY, STATE].

### Contact
**team@drawreport.com**
```

### 2.3 Refund Policy — replace the body at `legal.py:76-90`

Mostly fine already. Adds the identity line, the date, and a payout-timing sentence.

```markdown
_Last updated: [DATE]_

We want you to be happy with your report. This policy forms part of our Terms of Service.

### Money-back guarantee
If you are not satisfied with your report, email us within **7 days** of delivery and we
will refund your payment in full. No explanation needed. Reply to the email your report
arrived in, or write to **team@drawreport.com**.

Refunds are returned through PayPal to the account used for the purchase. PayPal usually
completes this within a few business days.

### If we cannot make a report
If we cannot produce a meaningful report from the photos you sent — for example, the photo
is not a readable drawing — we will ask for new photos and re-run the analysis **for free**,
or refund you in full. Your choice.

### Contact
**team@drawreport.com**
```

---

## 3. Code changes

### 3.1 Present the terms at the point of payment — **the important one**

`templates/order.html`, immediately above the submit button. Not a checkbox to tick blindly, but visible notice at the moment of assent:

```jinja
<p class="hint">{{ _('By placing this order you confirm that you are 18 or older, that you
  are a US resident, that the drawings are your own child’s or those of a child you are
  parent or guardian to, and that you agree to our') }}
  <a href="{{ url_for('main.legal', page='terms') }}">{{ _('Terms') }}</a>,
  <a href="{{ url_for('main.legal', page='privacy') }}">{{ _('Privacy Policy') }}</a>
  {{ _('and') }}
  <a href="{{ url_for('main.legal', page='refund') }}">{{ _('Refund Policy') }}</a>.</p>
```

Check the real endpoint name and signature for the legal route in `app/routes.py` before writing the `url_for` — do not guess it.

Add the same one-line notice above the upload button in `templates/_free_summary.html`, minus the age/residency sentence, since the free flow takes no payment but does take a child's photo:

```jinja
<p class="hint">{{ _('By uploading you agree to our') }}
  <a href="{{ url_for('main.legal', page='privacy') }}">{{ _('Privacy Policy') }}</a>.</p>
```

### 3.2 Last-updated dates
Do not hardcode a date string inside each markdown body where it can drift. Add a single constant in `app/legal.py`:

```python
LEGAL_LAST_UPDATED = "August 18, 2026"   # bump whenever a page body changes
```
and substitute it into `_Last updated: …_` at render time in `get_legal()`.

### 3.3 Nothing else
No cookie banner, no geo-blocking middleware, no consent table. See §4.

---

## 4. What "US-only" actually requires — and what it doesn't

**Do not build an IP geo-block.** It is not required, and it creates false negatives for US customers on VPNs or traveling abroad. US privacy law does not turn on IP address, and EU law turns on whether a business **targets** EU data subjects — not on whether a website is technically reachable from Europe.

What actually supports the US-only position, all of it cheap:
1. The Terms say the service is offered to US residents only (§2.2).
2. The order form asks the customer to confirm US residency (§3.1).
3. Prices are in USD only. Already true.
4. No marketing, ads, or SEO targeted at EU or UK audiences. A future decision, worth recording now.
5. No EU languages offered. Already true — `LOCALES` is `en` only.

Together these are a defensible "not targeting the EU" posture. Ask counsel whether they want more.

---

## 5. Before this goes live

| # | Check | |
|---|---|---|
| 1 | `[FULL LEGAL NAME]`, `[BUSINESS ADDRESS]`, `[STATE]`, `[COUNTY, STATE]` all filled | **pages must not ship with placeholders visible** |
| 2 | `DRAFT — to be reviewed by counsel` appears nowhere in the codebase | grep |
| 3 | `team@drawreport.com` is a monitored mailbox | see §0 note about `hello@` vs `team@` |
| 4 | Retention claims match reality: free photo deleted at 90 days, analytics purged at 24 months | **verify in `app/free_retention.py` and the analytics tables — do not publish a retention promise the code does not keep** |
| 5 | The named processors are the actual ones | Anthropic, Brevo, PayPal, host |
| 6 | Terms + Privacy + Refund links visible at checkout and before free upload | §3.1 |
| 7 | All three pages render, 200, from the footer and from checkout | |
| 8 | An attorney has reviewed the result | ⚠️ |

**Check 4 is the one that bites.** A privacy policy that promises deletion the system does not perform is a worse position than no policy at all — it converts a technical gap into a misrepresentation. If the 24-month analytics purge does not exist, either build it or remove the sentence.

---

## 6. One thing to raise with the owner

Sole trader means **your own legal name and a contactable address go on a public website**. For most people operating from home that means a home address. The usual fix is a single-member LLC, or a registered-agent / virtual business address, either of which lets a business name and address appear instead. It also separates personal assets from business liability — which matters more than usual for a service that makes interpretive statements about children.

That is a decision for the owner and an attorney, not for this task. The placeholders are written so either answer drops straight in.
