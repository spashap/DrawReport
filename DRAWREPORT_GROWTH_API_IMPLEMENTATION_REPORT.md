# DrawReport Growth Data API — Implementation Report

For the growth strategist. Written 2026-09-10, application version **V0.065**, deployed and
verified live at `https://drawreport.com`.

Companion documents: `growth/DRAWREPORT_GROWTH_API.md` (the API contract and every metric definition)
and `DRAWREPORT_GROWTH_TECHNICAL_REPORT.md` (the V0.064 audit this was built from).

---

## 1. What was implemented

A read-only, token-authenticated, aggregated growth API on the existing Flask app, plus an
append-only change log that records growth-relevant product changes so they can be read
alongside the numbers.

**Three endpoints**, all under `/internal/growth/`:

| Endpoint | Answers |
|---|---|
| `GET /summary?from=&to=` | What happened: traffic, funnels, commercial totals, and both attribution models. |
| `GET /content?from=&to=&limit=` | Which campaigns and content identifiers produced activity. |
| `GET /changes?since=` | What we changed during the same period. |

**Authentication.** A dedicated bearer token in the server environment,
`GROWTH_AGENT_TOKEN`, compared in constant time. The admin password is deliberately not
accepted, so the agent's access can be revoked on its own. No token configured on the server
means every route answers 503; a missing or wrong token means 401. Authentication is checked
before parameter validation, so an unauthenticated caller learns nothing about the API shape.

**Privacy by construction.** No query in the module reads an email address, a child's name, a
free-text note, a public token, a file path, model output or a raw user agent. Visitor, visit
and order identifiers are used as join keys inside Python and never appear in a response. A
test walks every response body and fails if any known private value or private field name
appears.

**Safety.** Every query carries both ends of the date window, and the window itself is capped
at 400 days by default (`GROWTH_MAX_RANGE_DAYS`), so a token holder cannot make the server
scan the whole history on demand. Row lists are capped. Nothing writes to the database.
Internal failures are logged server-side under the `growth` logger and returned to the caller
as a generic message with no SQL and no traceback.

**Reuse rather than reimplementation.** The two per-visit door funnels come from the existing
admin module `app/admin_funnels.py`, and the free-reading-to-purchase attribution comes from
`app/admin_free_analytics.py`. Both were already in production behind the admin screens. The
only change to either was an optional exclusive upper bound on the funnel builder, so the
admin keeps its open-ended "last N days" behaviour while the API can ask for a closed window.

**Two attribution models, never merged.** DrawReport stores both the tags of the visit itself
and the first-touch UTM cookie. The API returns them as separate named blocks with their own
totals, because they answer different questions and a single blended number would be wrong
half the time.

---

## 2. Files changed

New:

| File | Purpose |
|---|---|
| `app/growth.py` | The whole API: auth, validation, envelope, aggregation, attribution folding, change-log reader. |
| `growth/growth_changes.jsonl` | The append-only change log, tracked in git. |
| `growth/DRAWREPORT_GROWTH_API.md` | The API contract, metric definitions, limitations, curl examples. |
| `growth/DRAWREPORT_GROWTH_OPENAPI.yaml` | OpenAPI 3.1 schema to paste into a ChatGPT custom GPT Action. Carries the three interpretation rules in its operation descriptions. Never contains the token. |
| `tests/test_growth_api.py`, `tests/__init__.py` | 17 tests against a temporary database. |
| `DRAWREPORT_GROWTH_TECHNICAL_REPORT.md` | The prior audit, added to the repository. |
| `DRAWREPORT_GROWTH_API_IMPLEMENTATION_REPORT.md` | This document. |

Modified:

| File | Change |
|---|---|
| `config/settings.py` | Added `GROWTH_AGENT_TOKEN`, `GROWTH_MAX_RANGE_DAYS`, `GROWTH_CHANGES_FILE`. |
| `app/__init__.py` | Registered the growth blueprint. |
| `app/track.py` | Added `/internal/` to both exclusion lists, so a polling agent creates no visit rows and no phantom page views. |
| `app/admin_funnels.py` | `build()`, `_visit_types()` and `_orders_by_visit()` take an optional exclusive `until`. Default behaviour is unchanged. |
| `app/admin.py`, `templates/admin/settings.html` | The Site settings line now shows whether the growth token is set. |
| `CLAUDE.md` | The permanent growth-change-logging rule and an as-built row. |
| `DRAWREPORT_DevelopmentStatus.md` | Journal entry for V0.065. |

No public page, no copy, no price, no template outside the admin, and no existing tracking
behaviour was touched. Visitor-facing behaviour is identical to V0.064.

---

## 3. Endpoint URLs

```
GET https://drawreport.com/internal/growth/summary?from=YYYY-MM-DD&to=YYYY-MM-DD
GET https://drawreport.com/internal/growth/content?from=YYYY-MM-DD&to=YYYY-MM-DD&limit=50
GET https://drawreport.com/internal/growth/changes?since=2026-09-01T00:00:00Z
```

All require `Authorization: Bearer <TOKEN>`. All return `Cache-Control: no-store`. Dates are
inclusive UTC calendar days; `limit` defaults to 50 and caps at 200 for content, 500 for
changes.

The envelope is identical on every success:

```json
{ "schema_version": "1", "project": "drawreport", "generated_at": "...",
  "period": { "from": "...", "to": "...", "timezone": "UTC" },
  "data_quality": { "status": "ok|partial", "warnings": [] },
  "data": { } }
```

---

## 4. Exact metrics now available

**Traffic.** Raw visits, non-bot visits, engaged human visits, unique visitors under both
filters, new versus returning among engaged humans, average pages per engaged visit, device
mix, top ten countries.

The named primary metric is `visits_engaged_human`, defined as a visit with
`engaged = 1 AND device <> 'bot'`: the browser reported a scroll, click, key press, touch, or
fifteen seconds of visible time. The raw number is never hidden, and a warning states what
share of raw visits are known bots, because user-agent detection still misses scanners and
link fetchers.

**Funnel.** The two nested per-visit door funnels with per-step mobile and desktop splits:
the paid door from the product page through pricing, order form, order created and checkout
to paid; the free door from the home page through the wizard steps, summary, upload, result
and the click through to the paid report. Payment is always taken from the order row rather
than an event, because the PayPal webhook arrives without a browser.

The free block adds: wizard openers, questionnaires completed, email-only exits, uploads,
completions, insufficient and failed counts, in-progress count, average completion seconds,
failures by reason, uploads refused by reason, clicks through to the paid product, and
free-to-paid transitions split into direct (exact, via the token carried through the order
form), same-email and same-visitor matches.

The orders block adds: orders created, of those still unpaid and later paid, paid orders,
reports delivered, and paid orders by final status.

**Commercial.** Gross revenue, paid orders, average order value, coupon orders, average
drawings per paid order, and a breakdown by product.

**Attribution.** For both models: totals, by campaign, by source, and untagged. Last touch
also returns a channel breakdown and an unattributed bucket. Every row carries visits,
engaged visits, unique visitors, free uploads, free completions, orders created, paid orders
and gross revenue.

**Content.** The same row shape grouped by content identifier, by campaign and by source, for
both attribution models, with everything untagged summed separately rather than guessed.

**Changes.** Every logged growth-relevant change since a timestamp, oldest first.

---

## 5. Metrics still unavailable

These are returned as `null` with an explicit warning, so the caller can never read absence
as zero: ad spend, refunds, net revenue, PayPal fees.

Not exposed at all, because the underlying data does not exist in the system:

- Cost per click, cost per acquisition and return on ad spend, since no spend is stored.
- Refund rate and disputes; the PayPal webhook handles only completed captures.
- Page views, time on page, or read counts for individual blog articles. Only entry paths and
  engaged events exist per URL, and the API does not yet expose them per URL.
- Search Console impressions, clicks, queries and positions; Google Analytics 4 metrics; Meta
  Ads Manager delivery data. None of the three is integrated.
- Checkout abandonment inside PayPal, which is off-site and unobservable.
- Experiment or variant assignment, which the product has no mechanism for.

Two known biases are reported rather than silently corrected. Bot detection is user-agent
only, so non-bot visit counts remain inflated. First touch is recorded only when a UTM was
present in the URL, so organic, referral and direct first visits appear as untagged rather
than as their true first source.

---

## 6. Change-log mechanism

`growth/growth_changes.jsonl` holds one JSON object per line, tracked in git and appended to
in the same session as the change it describes. Identifiers are sequential, `DR-CHG-NNNN`.
The schema is the one in the specification: id, timestamp, category, title, reason, affected
area, expected metrics, experiment id, author, notes.

Allowed categories: analytics, attribution, funnel, landing_page, pricing, seo, social,
content, retention, product, email, infrastructure.

The reader tolerates damage without going offline. A blank line is ignored; a line that is
not a JSON object with an identifier and a parseable timestamp is skipped, counted, and
reported as a warning, so one bad line cannot take the whole log out of service. Entries are
sorted oldest first and filtered by the `since` argument. No filesystem path is ever exposed.

The first entry, `DR-CHG-0001`, records this implementation. A test asserts that the tracked
file parses cleanly, that identifiers are sequential with no gaps, and that every category is
one of the allowed values, so a malformed entry fails the suite rather than reaching
production.

---

## 7. The rule added to CLAUDE.md

A permanent section titled "Growth change logging" now states that whenever a change could
materially affect acquisition, search, attribution, analytics, landing-page behaviour, funnel
conversion, pricing, social traffic, email capture, retention, product usage, checkout or
revenue, an entry must be appended in the same work session, with the commit that ships the
change.

It explicitly excludes refactors with no behavioural effect, typo fixes, formatting, comments,
routine dependency maintenance, and purely internal engineering that cannot move a growth
metric. Where there is doubt, the instruction is to log it. Historical lines are never
rewritten except to correct a factual mistake, which must be said in the notes field.

---

## 8. Test results

Seventeen tests, all passing:

```
venv\Scripts\python.exe -m unittest discover -s tests -t .
Ran 17 tests in 0.654s
OK
```

Every test runs against a temporary SQLite file and a temporary change log created in a
system temporary directory. The settings paths are patched before the application is created
and restored afterwards, so production data is never opened, read or written.

Coverage:

| Area | Tests |
|---|---|
| Authentication | Missing header returns 401; wrong token returns 401; a non-bearer scheme returns 401; an unconfigured token returns 503 on every route, including when the caller sends an empty bearer value; the correct token returns 200 with a no-store header. |
| Side effects | Calls to the API create no rows in the visits table, authenticated or not. |
| Validation | Missing, malformed, non-ISO and reversed dates return 400 on both dated endpoints; an over-long range returns 400; a non-integer or zero limit returns 400; an oversized limit is capped rather than rejected; a missing or unparseable `since` returns 400. |
| Change log | Parsing skips and counts malformed lines; entries sort oldest first regardless of file order; the endpoint filters by `since`, strips internal fields, and warns about skipped lines; the real tracked log parses with sequential identifiers and valid categories. |
| Summary | Full envelope shape; exact expected counts for traffic, bot exclusion, new versus returning, device and country; free funnel counts including failure and refusal reasons; free-to-paid transitions; order and revenue figures; unavailable money fields are null; both attribution blocks present with the expected disagreement between them; an empty window still returns a valid document. |
| Content | Full row shape at every level; exact counts; the two models visibly disagree on the same content identifier; the limit applies. |
| Privacy | Every endpoint is swept for seven seeded private values and nineteen forbidden field names across the entire nested response. |
| Errors | An unauthenticated caller with invalid parameters gets 401 and a body containing nothing but the schema version, project and error. |

The fixture deliberately seeds a visitor who arrives first from a Facebook advertisement and
returns later from organic search, so the tests prove that first touch and last touch produce
different, correct numbers for the same person.

A separate manual regression check confirmed that the public pages, the sitemap, robots,
the health endpoint and all four admin screens still render, and that the funnel builder
still works when called without the new upper bound.

---

## 9. Deployment status

**Deployed to production.** The project's existing one-command release was used:

```
release.bat "<message>"
```

which bumped the version to V0.065, committed, pushed to GitHub, ran the server deploy script
over SSH, and asserted a 200 on the home page, the free wizard and the product page. All three
service units came back active.

The token was then generated on the server itself with `secrets.token_urlsafe(32)`, appended
to `/var/www/DrawReport/.env`, and the web unit restarted. The token was never printed, never
transmitted, and does not appear in this document, in the repository, or anywhere in the
conversation that produced it.

Live verification against the production host returned the expected status codes: 401 without
a token, 401 with a wrong token, 400 for a reversed date range, and 200 for all three
endpoints with the correct token. The live summary returned a well-formed document with
partial data quality and six warnings, all of them expected: the bot-share warning, the
small-sample warning, and the four unavailable-money warnings.

To rotate the token later, replace the value in the server environment file and restart
`drawreport-web`. To disable the API entirely, remove the value; every route then answers 503
and nothing else changes. The admin Site settings screen shows whether it is currently set.

---

## 10. Deviations from the specification

Five, all minor, none reducing scope.

**A test runner other than pytest.** The project has no test framework installed and the
brief forbids installing packages, so the tests are written for the standard library's
unittest and run with `python -m unittest discover -s tests -t .`. Coverage is exactly what
was asked for.

**An unattributed bucket was added.** The specification says not to guess when content-level
attribution is unavailable. Rather than silently dropping such rows, outcomes that cannot be
attributed to a visit inside the window are returned in a named `unattributed` bucket, so the
totals reconcile and the caller can see the size of the gap.

**Two revenue figures with different definitions coexist.** The commercial block counts
revenue by payment date, which is the correct answer to "what did we earn in this period".
The attribution rows count revenue of paid orders created in the period, because an order can
only be attributed to the visit that created it. Both are labelled, and the difference is
documented rather than reconciled away.

**Changes are capped at 500 entries per response.** The specification set no limit; an
unbounded log read would eventually be a slow response, so the cap exists with a warning
telling the caller to move `since` forward.

**A one-line admin display was added.** The Site settings screen now says whether the token is
configured. This is the only user-visible change anywhere in the application, it sits behind
the admin password, and it exists because the same failure mode has bitten this project
before: a value that lives only in the server environment file disappears on a rebuild and
nothing warns anyone.

One implementation note worth recording: SQLite treats `returning` as a reserved word, so a
column alias by that name is a syntax error. The alias is `n_returning` in the query and the
field is `returning` in the response.

---

## 11. Example responses

**All values below are fabricated for illustration.** They are not production figures.

### `GET /internal/growth/summary?from=2026-09-01&to=2026-09-10`

```json
{
  "schema_version": "1",
  "project": "drawreport",
  "generated_at": "2026-09-10T12:00:00+00:00",
  "period": { "from": "2026-09-01", "to": "2026-09-10", "timezone": "UTC" },
  "data_quality": {
    "status": "partial",
    "warnings": [
      "87% of raw visits are known bots; user-agent detection also misses scanners and link fetchers, so visits_non_bot is still inflated - use visits_engaged_human (120) as the human count",
      "ad_spend_usd is null: ad spend is not stored anywhere in DrawReport",
      "refunds_usd is null: refunds are not tracked (no refund webhook or column)",
      "net_revenue_usd is null: net revenue needs PayPal fees and refunds, neither is stored",
      "paypal_fees_usd is null: PayPal fees are not stored",
      "first_touch: the first-touch cookie is set only when a UTM was in the URL, so organic/referral/direct first visits appear as utm=null"
    ]
  },
  "data": {
    "traffic": {
      "primary_metric": "visits_engaged_human",
      "primary_metric_definition": "web_visits rows with engaged = 1 AND device <> 'bot': a non-bot visit that scrolled, clicked, or stayed 15 seconds",
      "visits_raw": 9000,
      "visits_non_bot": 1150,
      "visits_engaged_human": 120,
      "visitors_unique_non_bot": 980,
      "visitors_unique_engaged_human": 112,
      "engaged_human_new_vs_returning": { "new": 104, "returning": 16 },
      "avg_pages_per_engaged_visit": 1.8,
      "device_engaged_human": { "mobile": 74, "desktop": 41, "tablet": 5 },
      "countries_engaged_human": [
        { "country": "US", "engaged_visits": 88 },
        { "country": "GB", "engaged_visits": 12 }
      ]
    },
    "funnel": {
      "doors": [
        {
          "door": "free",
          "title": "Free door - the home page wizard",
          "visits": 96,
          "gross_revenue_usd": 38.0,
          "steps": [
            { "step": "Opened the home page", "kind": "path", "visits": 96, "mobile": 60, "desktop": 36 },
            { "step": "Stayed (scroll / 15s)", "kind": "path", "visits": 71, "mobile": 42, "desktop": 29 },
            { "step": "Reached the wizard", "kind": "gate", "visits": 22, "mobile": 14, "desktop": 8 },
            { "step": "Sent a drawing", "kind": "gate", "visits": 9, "mobile": 6, "desktop": 3 },
            { "step": "Created an order", "kind": "gate", "visits": 2, "mobile": 1, "desktop": 1 },
            { "step": "Paid", "kind": "gate", "visits": 2, "mobile": 1, "desktop": 1 }
          ]
        }
      ],
      "free": {
        "wizard_openers_visitors": 22,
        "questionnaires_completed": 14,
        "email_only_no_drawing": 3,
        "uploads": 9,
        "completions": 7,
        "insufficient": 1,
        "failed": 1,
        "in_progress": 0,
        "avg_completion_seconds": 41.6,
        "failures_by_reason": { "photo_poor": 1, "failed": 1 },
        "uploads_refused_by_reason": { "too_big": 2, "format": 1 },
        "to_paid_click_visitors": 3,
        "to_paid_transitions": {
          "direct": { "orders": 2, "paid_orders": 2, "gross_revenue_usd": 38.0 },
          "same_email": { "orders": 0, "paid_orders": 0, "gross_revenue_usd": 0.0 },
          "same_visitor": { "orders": 1, "paid_orders": 0, "gross_revenue_usd": 0.0 }
        },
        "to_paid_transitions_note": "cohort by questionnaire date; purchases counted with no date limit; 'direct' is exact (orders.free_token), the other two are matches by coincidence"
      },
      "orders": {
        "orders_created": 4,
        "orders_created_still_unpaid": 2,
        "orders_created_and_paid": 2,
        "paid_orders": 2,
        "reports_delivered": 2,
        "paid_orders_by_status": { "delivered": 2, "insufficient": 0, "failed": 0 }
      }
    },
    "commercial": {
      "currency": "USD",
      "gross_revenue_usd": 38.0,
      "paid_orders": 2,
      "average_order_value_usd": 19.0,
      "coupon_orders": 0,
      "avg_drawings_per_paid_order": 2.0,
      "by_product": { "snapshot": { "paid_orders": 2, "gross_revenue_usd": 38.0 } },
      "ad_spend_usd": null,
      "refunds_usd": null,
      "net_revenue_usd": null,
      "paypal_fees_usd": null,
      "note": "gross revenue = SUM(orders.price_cents) for orders with paid_at in the window (price after coupon, as charged); orders_created uses created_at"
    },
    "attribution": {
      "note": "last_touch = the tags of the visit itself (web_visits: utm, click id, referer -> channel), outcomes joined by visit_id; first_touch = the 1-year first-touch UTM cookie as recorded on events/orders, outcomes joined by visitor. They answer different questions and are never merged.",
      "last_touch": {
        "totals": { "visits": 1150, "engaged_visits": 120, "visitors": 980,
                    "free_uploads": 9, "free_completions": 7,
                    "orders_created": 4, "paid_orders": 2, "gross_revenue_usd": 38.0 },
        "by_channel": [
          { "channel": "ads", "visits": 61, "engaged_visits": 46, "visitors": 58,
            "free_uploads": 6, "free_completions": 5, "orders_created": 2,
            "paid_orders": 1, "gross_revenue_usd": 19.0 },
          { "channel": "organic", "visits": 150, "engaged_visits": 32, "visitors": 141,
            "free_uploads": 2, "free_completions": 2, "orders_created": 1,
            "paid_orders": 1, "gross_revenue_usd": 19.0 }
        ],
        "by_utm_campaign": [
          { "level": "campaign", "content_id": null, "source": "facebook",
            "medium": "paid", "campaign": "sample-campaign-a",
            "visits": 40, "engaged_visits": 31, "visitors": 39,
            "free_uploads": 5, "free_completions": 4, "orders_created": 1,
            "paid_orders": 1, "gross_revenue_usd": 19.0 }
        ],
        "by_utm_source": [],
        "untagged": { "visits": 900, "engaged_visits": 40, "visitors": 860,
                      "free_uploads": 1, "free_completions": 1, "orders_created": 1,
                      "paid_orders": 0, "gross_revenue_usd": 0.0 },
        "unattributed": { "free_uploads": 0, "free_completions": 0,
                          "orders_created": 1, "paid_orders": 0 }
      },
      "first_touch": {
        "totals": { "visits": 300, "engaged_visits": 120, "visitors": 250,
                    "free_uploads": 9, "free_completions": 7,
                    "orders_created": 4, "paid_orders": 2, "gross_revenue_usd": 38.0 },
        "by_utm_campaign": [
          { "level": "campaign", "content_id": null, "source": "facebook",
            "medium": "paid", "campaign": "sample-campaign-a",
            "visits": 55, "engaged_visits": 44, "visitors": 39,
            "free_uploads": 6, "free_completions": 5, "orders_created": 2,
            "paid_orders": 2, "gross_revenue_usd": 38.0 }
        ],
        "by_utm_source": [],
        "untagged": { "visits": 210, "engaged_visits": 70, "visitors": 205,
                      "free_uploads": 3, "free_completions": 2, "orders_created": 2,
                      "paid_orders": 0, "gross_revenue_usd": 0.0 }
      }
    }
  }
}
```

Note in the fabricated example what the design is for: the same campaign shows one paid order
under last touch and two under first touch, because one buyer arrived from the campaign,
left, and came back through search before buying. Both numbers are correct answers to
different questions, and neither is hidden.

### `GET /internal/growth/content?from=2026-09-01&to=2026-09-10&limit=20`

```json
{
  "schema_version": "1",
  "project": "drawreport",
  "generated_at": "2026-09-10T12:00:00+00:00",
  "period": { "from": "2026-09-01", "to": "2026-09-10", "timezone": "UTC" },
  "data_quality": {
    "status": "partial",
    "warnings": [
      "utm_medium=social does not separate paid from organic clicks on the same boosted post; use a distinct utm_medium per paid placement"
    ]
  },
  "data": {
    "grouping": "rows are grouped by (utm_source, utm_medium, utm_campaign, utm_content) at level=content, by campaign and by source; a row exists only where the tag exists - nothing is guessed",
    "last_touch": {
      "content": [
        { "level": "content", "content_id": "sample-creative-one", "source": "facebook",
          "medium": "paid", "campaign": "sample-campaign-a",
          "visits": 24, "engaged_visits": 19, "visitors": 24,
          "free_uploads": 4, "free_completions": 3,
          "orders_created": 1, "paid_orders": 1, "gross_revenue_usd": 19.0 },
        { "level": "content", "content_id": "sample-creative-two", "source": "facebook",
          "medium": "paid", "campaign": "sample-campaign-a",
          "visits": 16, "engaged_visits": 12, "visitors": 16,
          "free_uploads": 1, "free_completions": 1,
          "orders_created": 0, "paid_orders": 0, "gross_revenue_usd": 0.0 }
      ],
      "content_truncated": false,
      "campaign": [],
      "source": [],
      "untagged": { "visits": 900, "engaged_visits": 40, "visitors": 860,
                    "free_uploads": 1, "free_completions": 1, "orders_created": 1,
                    "paid_orders": 0, "gross_revenue_usd": 0.0 },
      "unattributed": { "free_uploads": 0, "free_completions": 0,
                        "orders_created": 1, "paid_orders": 0 }
    },
    "first_touch": {
      "content": [
        { "level": "content", "content_id": "sample-creative-one", "source": "facebook",
          "medium": "paid", "campaign": "sample-campaign-a",
          "visits": 31, "engaged_visits": 25, "visitors": 24,
          "free_uploads": 4, "free_completions": 3,
          "orders_created": 2, "paid_orders": 2, "gross_revenue_usd": 38.0 }
      ],
      "content_truncated": false,
      "campaign": [],
      "source": [],
      "untagged": { "visits": 210, "engaged_visits": 70, "visitors": 205,
                    "free_uploads": 3, "free_completions": 2, "orders_created": 2,
                    "paid_orders": 0, "gross_revenue_usd": 0.0 }
    },
    "limit": 20
  }
}
```

### `GET /internal/growth/changes?since=2026-09-01T00:00:00Z`

```json
{
  "schema_version": "1",
  "project": "drawreport",
  "generated_at": "2026-09-10T12:00:00+00:00",
  "period": { "from": "2026-09-01T00:00:00+00:00", "to": "2026-09-10T12:00:00+00:00", "timezone": "UTC" },
  "data_quality": { "status": "ok", "warnings": [] },
  "data": {
    "changes": [
      {
        "id": "DR-CHG-0001",
        "timestamp": "2026-09-10T12:00:00Z",
        "category": "analytics",
        "title": "Implemented the Growth Data API and the growth change log",
        "reason": "Expose decision-quality, aggregated growth data to an external growth agent, and give it a record of growth-relevant product changes to read alongside the numbers",
        "affected_area": ["/internal/growth/summary", "/internal/growth/content", "/internal/growth/changes"],
        "expected_metrics": [],
        "experiment_id": null,
        "author": "claude-code",
        "notes": "Read-only. Own bearer token, 503 until set on the server. No visitor-facing change, so no metric is expected to move."
      }
    ],
    "count": 1
  }
}
```

### Error shapes

```json
{ "schema_version": "1", "project": "drawreport",
  "error": { "code": "unauthorized", "message": "missing or invalid bearer token" } }

{ "schema_version": "1", "project": "drawreport",
  "error": { "code": "bad_request", "message": "from must not be after to" } }

{ "schema_version": "1", "project": "drawreport",
  "error": { "code": "not_configured",
             "message": "the growth API is disabled: GROWTH_AGENT_TOKEN is not set" } }
```

---

## 12. How to start using it

Ask the owner for the token; it is in the server environment file and nowhere else. Then read
`growth/DRAWREPORT_GROWTH_API.md` for the metric definitions before interpreting any number, particularly
the difference between the two attribution models and the definition of an engaged human
visit.

Three things to hold in mind when designing the first experiments. Use
`visits_engaged_human`, never the raw count, whenever you mean people. Expect first touch and
last touch to disagree, and say which one a claim rests on. Cost is not in this system, so any
efficiency measure has to be assembled by hand from Ads Manager spend and the counts here.
