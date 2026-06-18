"""US legal pages, per-locale, as markdown. DRAFT copy — the owner must have these
reviewed by counsel before launch (especially children's-data / COPPA and refund terms).
This is not legal advice.
"""
from __future__ import annotations

import markdown as md

from config import settings

# {locale: {page_key: (title, markdown_body)}}
_PAGES = {
    "en": {
        "privacy": ("Privacy Policy", """
**DRAFT — to be reviewed by counsel before launch. Not legal advice.**

DrawReport ("we") helps a parent or guardian receive an educational report about their
child's drawing. This policy explains what we collect and how we handle it.

### Children's data (COPPA)
DrawReport is intended for **parents and guardians**, not for children. We do not knowingly
collect personal information directly from children under 13. A parent or guardian uploads
their child's drawing and provides limited context (the child's first name, gender, and
birth month/year) **on the child's behalf and with their consent as the child's parent**.

### What we collect
- The drawing image(s) you upload and the context you enter.
- Your email address (to deliver the report and provide account access).
- Payment is processed by **PayPal**; we do not receive or store your full card details.
- Basic, privacy-preserving web analytics. For geography we derive only an approximate
  region from your IP address and store **only that derived label — never the IP itself**.

### How we use it
Solely to generate and deliver your report, operate your account, provide support, and
improve the service. The child's drawings are **never published, never used in advertising,
and never sold or shared with third parties**, except service providers strictly necessary
to run the service (e.g. the report-generation and email providers).

### Retention & your choices
You may request deletion of your drawings, report, and account data at any time by replying
to any email from us or contacting support. We retain order records as required for tax and
accounting purposes.

### Contact
Questions or deletion requests: reply to any email from us.
"""),
        "terms": ("Terms of Service", """
**DRAFT — to be reviewed by counsel before launch. Not legal advice.**

By using DrawReport you agree to these terms.

### What the service is
DrawReport provides an **educational observation** of the skills visible in a child's drawing,
set against the typical developmental stages of children's art. It is **not** a medical,
psychological, or diagnostic service, and does not replace professional advice. Reports are
generated with the help of AI and are intended as a warm, educational read — not a clinical
assessment.

### Accounts
Access to your reports is by email sign-in (a one-time code). Keep access to your email secure.

### Payment
Payments are processed by **PayPal**. Prices are shown in US dollars before purchase.

### Acceptable use
Upload only drawings you have the right to share, made by your own child or a child for whom
you are the parent or guardian. Do not upload unlawful content.

### Disclaimer & liability
The service is provided "as is." To the maximum extent permitted by law, DrawReport is not
liable for indirect or consequential damages. Nothing here limits rights that cannot be
limited under applicable law.
"""),
        "refund": ("Refund Policy", """
**DRAFT — to be reviewed by counsel before launch. Not legal advice.**

We want you to be happy with your report.

### Money-back guarantee
If you're not satisfied with your report, contact us within **7 days** of delivery and we'll
refund your payment — no fuss. Just reply to the email your report came in, or contact support.

### Couldn't make a report
If we can't produce a meaningful report from the photos you sent (for example, the image isn't
a readable drawing), we'll ask for new photos and re-run the analysis **for free**, or refund
you in full — your choice.
"""),
    },
}


def get_legal(page: str, locale: str = settings.DEFAULT_LOCALE):
    """Returns (title, html) or None."""
    loc = locale if locale in _PAGES else settings.DEFAULT_LOCALE
    entry = _PAGES[loc].get(page)
    if entry is None:
        return None
    title, body = entry
    return title, md.markdown(body, extensions=["extra"])


def legal_keys(locale: str = settings.DEFAULT_LOCALE):
    return list(_PAGES.get(locale, _PAGES[settings.DEFAULT_LOCALE]).keys())
