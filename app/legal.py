"""US legal pages, per-locale, as markdown.

Two things about this file are load-bearing.

**The contracting party is PROVISIONAL.** The pages currently name "DrawReport Team",
which is a trading name, not a legal person - owner decision, taken so the pages could go
live without brackets showing while the real identity is settled. The business is operated
by an individual, so the eventual answer is a personal legal name (or an LLC) plus an
address, and only the owner can supply those. They come from the environment (see
`config/settings.py`), so filling them in is an .env change on the server, not a deploy.

Anything still unset is OMITTED rather than printed as a bracket: no address means the
sentence just ends at the country, and no state means the whole Governing law section
disappears. A missing clause is a known gap; "[STATE]" on a live page is a broken page,
and a GUESSED state would be worse than either. `unfilled_placeholders()` reports what is
still missing, because nothing on the rendered page shows it any more.

**These pages have not been reviewed by a lawyer.** They used to say so, out loud, at the
top of every page, while PayPal was live - which is a written admission to a paying
customer that you knew your terms were unfinished when you contracted with her. The banner
is gone; the review still needs booking (admin task `legal_review`).

Scope decisions behind the wording (owner, 2026-08-19): US only, sold to residents of the
United States who are 18 or older, so there is no GDPR/UK section, no cookie-consent gate
and no 14-day withdrawal right. CCPA thresholds are not met today. COPPA has no threshold
and applies now, which is why the children's-data section is the longest one.
"""
from __future__ import annotations

import markdown as md

from config import settings

# Bump this whenever a page body below changes - it is what every page prints as its
# "Last updated" line, and a policy whose date predates its own text is worse than no date.
LEGAL_LAST_UPDATED = "August 19, 2026"

# {locale: {page_key: (title, markdown_body)}}
_PAGES = {
    "en": {
        "privacy": ("Privacy Policy", """
_Last updated: [DATE]_

DrawReport is operated by [IDENTITY] (“we,” “us”).
We give a parent or guardian an educational report about their child’s
drawing. This policy explains what we collect, who it goes to, and how long we keep it.

Questions about this policy, or about your data: **[CONTACT EMAIL]**.

### Who this service is for
DrawReport is offered to residents of the United States who are 18 or older. It is
intended for **parents and guardians**, not for children.

### Children’s data (COPPA)
We do not knowingly collect personal information directly from children under 13.
A parent or guardian uploads their child’s drawing and provides limited context — the
child’s first name, gender, and birth month and year — **on the child’s behalf, and as
that child’s parent or guardian, consents to it**.

We use a child’s information for one purpose only: producing the report that parent
asked for. We do not use it to build profiles, we do not use it for advertising, we do
not use it to train AI models, and we do not sell it. A parent can withdraw consent and
have the child’s drawings and information deleted at any time by emailing
**[CONTACT EMAIL]**.

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
- `locale` — remembers which language version of the site you are reading.
- A sign-in cookie, set only after you sign in, which keeps you signed in.

You can clear or block cookies in your browser. Blocking them does not stop you ordering
or reading a report.

### Who else sees your data
We do not sell your data and we do not share it for anyone else’s marketing. Your child’s
drawings are **never published and never used in advertising**. We use a small number of
service providers, each of which receives only what it needs to do its job:

- **Anthropic** — the AI service that generates the report. It receives the drawing image
  and the context you entered. Under Anthropic’s commercial terms, data sent through their
  API is not used to train their models.
- **Brevo** — sends the emails that deliver your report and your sign-in codes. Receives
  your email address.
- **PayPal** — processes payment. Receives what it needs to take the payment; we do not
  pass it your child’s drawing or the report.
- **Our hosting provider**, which stores the site’s data on our behalf.

We may also disclose information if the law requires it.

### How long we keep things
- **Free readings**: the uploaded photo is deleted **90 days** after the reading. The text
  of the reading stays at your link.
- **Paid reports**: we keep the drawings and the report in your account so you can return
  to them. Ask us to delete them at any time and we will.
- **Order and payment records**: kept **7 years**, because tax and accounting rules require it.
- **Analytics records**: which pages were visited and roughly where from, with no drawing
  and no IP address in them. We keep these while we run the site.

### Your choices
Email **[CONTACT EMAIL]** to:
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
"""),
        "terms": ("Terms of Service", """
_Last updated: [DATE]_

These terms are an agreement between you and [IDENTITY] (“we,” “us”), who operates
DrawReport. By ordering a report or using the free reading, you agree to them.

### Who can use DrawReport
You must be **18 or older** and a **resident of the United States**. We offer the service
in the United States only, and we do not offer it to residents of the European Union or
the United Kingdom.

### What the service is — and what it is not
DrawReport provides an **educational observation** of what is visible in a child’s
drawing, alongside the typical developmental stages of children’s art.

It is **not** a medical, psychological, or diagnostic service, it is **not** a substitute
for professional advice, and it must not be relied on to decide whether a child needs
care. If you have concerns about your child’s health, development, or well-being, speak
to a pediatrician or a qualified professional. A drawing cannot tell you that, and neither
can we.

Reports are **generated with the help of AI**. The observations in them are suggestions
based on what is visible in the image and what you told us. **They may be incomplete or
wrong.** Read them as one perspective to explore with your child, not as findings.

### Your child’s drawings — who owns what
You keep every right you have in your child’s drawings. Uploading a drawing gives us a
limited license to store it and process it **for the single purpose of producing and
delivering your report**, and for nothing else. We claim no ownership of your child’s
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
content, anyone else’s work, or images that are not a child’s drawing. We may decline or
stop providing the service to anyone who breaks these terms, and we will refund any
payment for a report we decline to produce.

### Availability
We aim to deliver reports promptly but do not guarantee uninterrupted service. Delivery
times quoted on the site are estimates.

### Disclaimer and limit of liability
The service is provided **“as is” and without warranties of any kind**, including any
warranty that the observations in a report are accurate or complete.

To the maximum extent permitted by law, our total liability arising out of or relating to
the service is limited to **the amount you paid us for the report in question**, and we
are not liable for indirect, incidental, or consequential damages. Nothing in these terms
limits liability that cannot be limited under applicable law, including liability for
fraud or for death or personal injury caused by negligence.

### Changes to these terms
We may update these terms. The date at the top shows when they last changed, and changes
apply to orders placed after that date.

[GOVERNING LAW]### Contact
**[CONTACT EMAIL]**
"""),
        "refund": ("Refund Policy", """
_Last updated: [DATE]_

We want you to be happy with your report. This policy forms part of our Terms of Service.

### Money-back guarantee
If you are not satisfied with your report, email us within **7 days** of delivery and we
will refund your payment in full. No explanation needed. Reply to the email your report
arrived in, or write to **[CONTACT EMAIL]**.

Refunds are returned through PayPal to the account used for the purchase. PayPal usually
completes this within a few business days.

### If we cannot make a report
If we cannot produce a meaningful report from the photos you sent — for example, the photo
is not a readable drawing — we will ask for new photos and re-run the analysis **for free**,
or refund you in full. Your choice.

### Contact
**[CONTACT EMAIL]**
"""),
    },
}

# A value is "unset" when it is still the bracketed default from config/settings.py.
# Unset values are never printed - the sentence around them is dropped instead. See the
# module docstring for why a bracket on a live page is worse than a missing clause.
_TOKENS = ("[DATE]", "[IDENTITY]", "[GOVERNING LAW]", "[CONTACT EMAIL]")

# The name the pages carry until a real legal person is decided (owner, 2026-08-19).
# It is a TRADING name, not a legal entity, so unfilled_placeholders() keeps flagging it.
PROVISIONAL_ENTITY_NAME = "DrawReport Team"

_GOVERNING_LAW = """### Governing law
These terms are governed by the laws of {state}, United States, and you and we agree that
any dispute will be brought in the state or federal courts located in {venue}.

"""


def _unset(value: str) -> bool:
    """Still the bracketed default, e.g. "[BUSINESS ADDRESS]"."""
    v = (value or "").strip()
    return not v or (v.startswith("[") and v.endswith("]"))


def _identity() -> str:
    """The contracting party as one phrase: name, address if we have one, country.

    Composed rather than three separate tokens because the COMMAS belong to whichever
    parts survive - "DrawReport Team, , United States" is exactly the kind of thing that
    reaches production when each piece is substituted on its own."""
    parts = [settings.LEGAL_ENTITY_NAME]
    if not _unset(settings.LEGAL_ENTITY_ADDRESS):
        parts.append(settings.LEGAL_ENTITY_ADDRESS)
    parts.append("United States")
    return ", ".join(parts)


def _values() -> dict:
    """Read settings at call time, not at import: the env can change under a long-lived
    gunicorn worker and a policy page must not serve a stale legal name."""
    have_venue = not _unset(settings.LEGAL_STATE) and not _unset(settings.LEGAL_VENUE)
    return {
        "[DATE]": LEGAL_LAST_UPDATED,
        "[IDENTITY]": _identity(),
        # No state means no governing-law clause at all. The alternative - naming a state
        # we guessed - would be a false statement about where a customer has to sue.
        "[GOVERNING LAW]": (_GOVERNING_LAW.format(state=settings.LEGAL_STATE,
                                                  venue=settings.LEGAL_VENUE)
                            if have_venue else ""),
        "[CONTACT EMAIL]": settings.LEGAL_CONTACT_EMAIL,
    }


def _fill(body: str) -> str:
    """Substitute the identity and the date at RENDER time, not in the source text.

    The date then exists once instead of three times, and the identity comes from the
    environment so the owner can put a legal name on the site without a code change.
    Plain replace rather than str.format: these bodies are markdown written by a human,
    and format() would make them escape every brace they ever grow."""
    values = _values()
    for token in _TOKENS:
        body = body.replace(token, values[token])
    return body


def unfilled_placeholders(locale: str = settings.DEFAULT_LOCALE) -> list:
    """Which pieces of the legal identity are still missing, by env var name.

    Reads the settings rather than the rendered page ON PURPOSE: unset values are now
    omitted, so the pages look complete whether or not anyone has filled them in, and
    this is the only thing that can still tell the difference. The provisional trading
    name counts as missing - "DrawReport Team" is not a legal person and cannot be sued
    or sue."""
    gaps = []
    if _unset(settings.LEGAL_ENTITY_NAME) or             settings.LEGAL_ENTITY_NAME.strip() == PROVISIONAL_ENTITY_NAME:
        gaps.append("LEGAL_ENTITY_NAME")
    for name in ("LEGAL_ENTITY_ADDRESS", "LEGAL_STATE", "LEGAL_VENUE"):
        if _unset(getattr(settings, name)):
            gaps.append(name)
    return gaps


def get_legal(page: str, locale: str = settings.DEFAULT_LOCALE):
    """Returns (title, html) or None."""
    loc = locale if locale in _PAGES else settings.DEFAULT_LOCALE
    entry = _PAGES[loc].get(page)
    if entry is None:
        return None
    title, body = entry
    return title, md.markdown(_fill(body), extensions=["extra"])


def legal_keys(locale: str = settings.DEFAULT_LOCALE):
    return list(_PAGES.get(locale, _PAGES[settings.DEFAULT_LOCALE]).keys())
