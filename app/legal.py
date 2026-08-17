"""US legal pages, per-locale, as markdown. DRAFT copy — the owner must have these
reviewed by counsel before launch (especially children’s-data / COPPA and refund terms).
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

DrawReport ("we," "us") gives a parent or guardian an educational report about their
child’s drawing. This policy explains what we collect and how we handle it.

### Children’s data (COPPA)
DrawReport is intended for **parents and guardians**, not for children. We do not knowingly
collect personal information directly from children under 13. A parent or guardian uploads
their child’s drawing and provides limited context (the child’s first name, gender, and
birth month/year) **on the child’s behalf and, as that child’s parent or guardian, consents to it**.

### What we collect
- The drawing image(s) you upload and the context you enter.
- Your email address (so we can send you the report and let you sign in).
- No card data: payment is handled by **PayPal**, and we do not receive or store your full
  card number.
- Basic, privacy-friendly web analytics. To get a rough location, we work out an approximate
  region from your IP address and store **only that region name, never the IP address itself**.

### How we use it
Solely to generate and deliver your report, operate your account, provide support, and
improve the service. The child’s drawings are **never published, never used in advertising,
and never sold or shared with third parties**, other than service providers that are strictly
necessary to run the service (for example, our report-generation and email providers).

### Retention & your choices
You can ask us to delete your drawings, report, and account data at any time by replying
to any email from us or contacting support. We retain order records as required for tax and
accounting purposes.

### Contact
Questions, or want your data deleted? Just reply to any email from us.
"""),
        "terms": ("Terms of Service", """
**DRAFT — to be reviewed by counsel before launch. Not legal advice.**

By using DrawReport, you agree to these terms.

### What the service is
DrawReport provides an **educational observation** of the skills visible in a child’s drawing,
alongside the typical developmental stages of children’s art. It is **not** a medical,
psychological, or diagnostic service, and does not replace professional advice. Reports are
generated with the help of AI and are meant to be read as a warm, educational observation,
not a clinical assessment.

### Accounts
You sign in to your reports with a one-time code sent to your email. Keep your email account
secure.

### Payment
Payments are processed by **PayPal**. Prices are shown in US dollars before purchase.

### Acceptable use
Upload only drawings that you have the right to share and that were made by your own child,
or by a child for whom you are the parent or guardian. Do not upload unlawful content.

### Disclaimer & liability
The service is provided "as is." To the maximum extent permitted by law, DrawReport is not
liable for indirect or consequential damages. Nothing in these terms takes away rights that
cannot be limited under applicable law.
"""),
        "refund": ("Refund Policy", """
**DRAFT — to be reviewed by counsel before launch. Not legal advice.**

We want you to be happy with your report.

### Money-back guarantee
If you’re not satisfied with your report, contact us within **7 days** of delivery and we’ll
refund your payment, no hassle. Just reply to the email your report arrived in, or contact
support.

### If we can’t make a report
If we can’t produce a meaningful report from the photos you sent (for example, the photo isn’t
a readable drawing), we’ll ask for new photos and re-run the analysis **for free**, or refund
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
