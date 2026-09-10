# DrawReport Growth Data API

Read-only, aggregated growth metrics for an external growth agent (for example a ChatGPT
connector). Implemented in `app/growth.py`; served by the normal web unit at
`https://drawreport.com/internal/growth/*`.

The API answers three questions and nothing else:

| Question | Endpoint |
|---|---|
| What happened? | `GET /internal/growth/summary?from=YYYY-MM-DD&to=YYYY-MM-DD` |
| Which sources / content caused it? | `GET /internal/growth/content?from=YYYY-MM-DD&to=YYYY-MM-DD&limit=50` |
| What did we change meanwhile? | `GET /internal/growth/changes?since=ISO-8601` |

---

## Authentication

```
Authorization: Bearer <TOKEN>
```

- The token is the server environment variable `GROWTH_AGENT_TOKEN` (server `.env`, never in
  git). It is a dedicated token: the admin password is **not** accepted.
- Token not configured on the server → every route answers **503** `not_configured`.
- Header missing, wrong scheme, or wrong token → **401** `unauthorized` (with a
  `WWW-Authenticate: Bearer` header).
- Authentication is checked **before** parameter validation, so an unauthenticated caller
  learns nothing about the API's shape.
- Responses carry `Cache-Control: no-store`.
- Requests to `/internal/` never create analytics visit rows (`app/track.py`), so a polling
  agent does not inflate the numbers it is reading.

Generate a token (on the server, never paste it into chat or docs):

```
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

then add `GROWTH_AGENT_TOKEN=<value>` to `/var/www/DrawReport/.env` and
`systemctl restart drawreport-web`. `/admin` → Site settings shows whether it is set.

---

## Response envelope

Every 200 response:

```json
{
  "schema_version": "1",
  "project": "drawreport",
  "generated_at": "2026-09-10T12:00:00+00:00",
  "period": { "from": "2026-09-01", "to": "2026-09-10", "timezone": "UTC" },
  "data_quality": { "status": "ok | partial", "warnings": ["..."] },
  "data": { }
}
```

- `period.from` / `period.to` are inclusive calendar days in **UTC**. For `/changes`, `from`
  is the `since` you passed and `to` is `generated_at`.
- `data_quality.status` is `partial` whenever there is at least one warning. Warnings are
  plain sentences meant to be read by the agent; they name every metric that is `null`
  because the data does not exist, and every known bias in the numbers.

Every error response:

```json
{ "schema_version": "1", "project": "drawreport",
  "error": { "code": "bad_request | unauthorized | not_configured | internal_error", "message": "..." } }
```

Internal failures are logged server-side under the `growth` logger and return only
`internal error (logged)`. No SQL, no stack traces.

---

## Parameters and validation

| Parameter | Endpoints | Rules |
|---|---|---|
| `from`, `to` | summary, content | Required. `YYYY-MM-DD` exactly (10 characters). `from <= to`. Window at most `GROWTH_MAX_RANGE_DAYS` days (default 400). Otherwise **400**. |
| `limit` | content (default 50, max 200); changes (max 500) | Integer ≥ 1; larger values are capped silently and reported in `data.limit` (content). Non-integer or < 1 → **400**. |
| `since` | changes | Required. ISO-8601 timestamp; `Z` and `+00:00` accepted; a naive value is read as UTC. Otherwise **400**. |

Timestamps in the database are UTC ISO-8601 strings, so a window `from=A&to=B` selects
rows with `A 00:00:00 <= t < (B+1 day) 00:00:00` UTC.

---

## GET /internal/growth/summary

`data` has four blocks.

### `traffic`

| Field | Definition |
|---|---|
| `primary_metric` | Always `"visits_engaged_human"`. **Use this number for people.** |
| `visits_raw` | All `web_visits` rows started in the window, bots included. Reported, never hidden. |
| `visits_non_bot` | Rows whose `device` is not `bot`. Bot detection is user-agent based (`app/track.py`), so scanners and link fetchers with browser-like agents still pass. Treat as inflated. |
| `visits_engaged_human` | `engaged = 1 AND device <> 'bot'`. Engaged = the browser reported a scroll, click, key press, touch, **or** 15 seconds of visible time (`static/js/track.js`). This is the GA4 engaged-session model. |
| `visitors_unique_non_bot`, `visitors_unique_engaged_human` | Distinct `visitor_id` (1-year first-party cookie `dr_v`) under the same two filters. |
| `engaged_human_new_vs_returning` | Among engaged human visits: `new` = the visitor's first visit ever; `returning` = an earlier visit exists for that cookie. Cookie-based, so a new browser or device is "new". |
| `avg_pages_per_engaged_visit` | HTML page responses per engaged human visit (beacons, polling and static files are not pages). |
| `device_engaged_human` | Engaged human visits by `mobile` / `desktop` / `tablet` / `unknown` (user agent). |
| `countries_engaged_human` | Top 10 ISO country codes (GeoLite2 snapshot; `unknown` before 2026-09-06). |

A warning always states the share of raw visits that are known bots.

### `funnel`

`doors` — the two nested **per-visit** funnels from the admin (`app/admin_funnels.py`),
bounded to the window. Each door lists `steps` with `visits`, `mobile`, `desktop`:

- `paid` door (entry = viewed `/en/report`): opened the product page → stayed → scrolled
  halfway → reached the pricing → opened the order form → started filling it in → created
  an order → reached checkout → **Paid**.
- `free` door (entry = viewed `/en/`): opened the home page → stayed → reached the wizard →
  entered name and age → chose a concern → reached the summary → sent a drawing → opened the
  finished analysis → clicked "get the full report" → created an order → **Paid**.

"Paid" is taken from the order row (`orders.paid_at`), never from an event, because the
PayPal webhook has no browser. Gate steps are filled in from the deepest gate reached, so a
lost beacon cannot make a later step larger than an earlier one. Observation steps
(stayed, scrolled, pricing) are counted as they are.

`free` — the free reading funnel:

| Field | Definition |
|---|---|
| `wizard_openers_visitors` | Distinct non-bot visitors with a `free_view` event. |
| `questionnaires_completed` | `free_analyses` rows created in the window (one per completed 3-question set; one person can complete it twice). |
| `email_only_no_drawing` | Rows still `draft` where an email was left ("no drawing to hand" exit). |
| `uploads` | Rows with `uploaded_at` (a drawing was accepted). |
| `completions` | `status = 'done'` (a reading was produced). |
| `insufficient`, `failed`, `in_progress` | Other terminal / transient statuses. |
| `avg_completion_seconds` | Mean model turnaround for completed readings. |
| `failures_by_reason` | `insufficient`/`failed` rows by `reason_key` (e.g. `photo_poor`, `not_a_drawing`, `blank`, `other`, `failed`). |
| `uploads_refused_by_reason` | Uploads rejected **before** a row changed, from `free_upload_failed` events: `too_big`, `format`, `broken`, `no_file`, `email`, `cap`, `email_cap`, `limit`, `already`, `not_found`. |
| `to_paid_click_visitors` | Distinct visitors who clicked "get the full report" on a free result. |
| `to_paid_transitions` | Orders by people from this questionnaire cohort, matched three ways in descending precision: `direct` (exact: the order carries the reading's token), `same_email`, `same_visitor`. Purchases are counted with **no date limit** (the question is "did they buy at all"). Same logic as `/admin/free-analytics`. |

`orders`:

| Field | Definition |
|---|---|
| `orders_created` | Orders whose `created_at` is in the window (= checkout started; PayPal's own page is off-site and unobservable). |
| `orders_created_still_unpaid` / `orders_created_and_paid` | Split of the above by whether `paid_at` was ever set. |
| `paid_orders` | Orders whose `paid_at` is in the window. |
| `reports_delivered` | `reports.generated_at` in the window. |
| `paid_orders_by_status` | Of the paid orders: `delivered` / `insufficient` / `failed`. |

### `commercial`

| Field | Definition |
|---|---|
| `gross_revenue_usd` | `SUM(orders.price_cents)/100` for orders with `paid_at` in the window. This is the amount charged, **after** any coupon. |
| `paid_orders`, `average_order_value_usd` | Count and mean of the same set (`null` when there are none). |
| `coupon_orders` | Paid orders that used a coupon code. |
| `avg_drawings_per_paid_order` | Mean number of uploaded drawings per paid order. |
| `by_product` | Paid orders and revenue per `product_code`. |
| `ad_spend_usd`, `refunds_usd`, `net_revenue_usd`, `paypal_fees_usd` | **Always `null`.** None of these is stored anywhere in DrawReport; each has a warning. Do not read `null` as zero. |

### `attribution` — two models, never merged

DrawReport stores **both** of these, and they answer different questions:

| Model | Where the tag comes from | Unit | Outcomes joined by |
|---|---|---|---|
| `last_touch` | The visit's own URL tags at visit start: `utm_*`, click id (`gclid`/`fbclid`/`msclkid`), referer, and a derived `channel` | one non-bot **visit** | `visit_id` (the order / free analysis created in that visit) |
| `first_touch` | The 1-year first-touch cookie `dr_utm`, set the first time the browser arrived with any UTM; copied onto every event and onto the order | one **visitor** seen in the window | `visitor_id` (orders use their own stored first-touch copy) |

Consequences you must know:

- A visitor who first came from a Facebook ad and later returned from Google is
  `organic` in last touch and `facebook` in first touch. Both are true.
- First touch is **only ever a UTM**. Organic, referral and direct first visits leave the
  cookie unset and appear under `first_touch.untagged`. Do not read "untagged" as "direct".
- `last_touch.unattributed` counts outcomes (orders, free analyses) created in the window
  whose visit either started before the window or is bot-flagged; they are not guessed into a
  bucket.
- Each model returns `totals`, `by_utm_campaign`, `by_utm_source`, and `untagged`; last touch
  also returns `by_channel`. Row fields: `visits`, `engaged_visits`, `visitors`,
  `free_uploads`, `free_completions`, `orders_created`, `paid_orders`, `gross_revenue_usd`
  (revenue of the paid orders **created** in the window, so it can differ from
  `commercial.gross_revenue_usd`, which uses `paid_at`).

Channel values (last touch, `app/track.classify_channel`, in trust order): `ads` (a click id
or a paid `utm_medium`), `social`, `email`, `utm` (other UTM), `direct` (no referer),
`internal`, `organic` (search engine referer), `referral`.

---

## GET /internal/growth/content

Same window rules as `/summary`. `data`:

```
grouping: "..."
last_touch:  { content: [...], content_truncated: bool, campaign: [...], source: [...], untagged: {...}, unattributed: {...} }
first_touch: { content: [...], content_truncated: bool, campaign: [...], source: [...], untagged: {...} }
limit: 50
```

Row shape (all levels):

```json
{ "level": "content | campaign | source",
  "content_id": "curious-drawing", "source": "facebook", "medium": "social", "campaign": "freemium",
  "visits": 0, "engaged_visits": 0, "visitors": 0,
  "free_uploads": 0, "free_completions": 0, "orders_created": 0, "paid_orders": 0,
  "gross_revenue_usd": 0.0 }
```

- `content` rows exist only where `utm_content` was present; `campaign` rows only where
  `utm_campaign` was present (`content_id` is `null` and the row aggregates every content id
  under that campaign, including none); `source` rows likewise. **Nothing is guessed** for a
  visit without the tag; those are summed into `untagged`.
- Rows are sorted by `engaged_visits`, then `paid_orders`, `orders_created`, `visits`, and
  cut at `limit` per list (`content_truncated` says whether the content list was cut).
- Both models are returned in full so a disagreement is visible, not hidden.

---

## GET /internal/growth/changes

Reads the tracked, append-only file `growth/growth_changes.jsonl` (one JSON object per
line) and returns entries with `timestamp >= since`, **oldest first**, at most 500.

```json
"data": { "changes": [ { "id": "DR-CHG-0001", "timestamp": "...", "category": "analytics",
                          "title": "...", "reason": "...", "affected_area": ["..."],
                          "expected_metrics": [], "experiment_id": null,
                          "author": "claude-code", "notes": "" } ],
          "count": 1 }
```

Malformed lines are skipped and counted in a warning; no filesystem paths are exposed.
Categories: `analytics`, `attribution`, `funnel`, `landing_page`, `pricing`, `seo`, `social`,
`content`, `retention`, `product`, `email`, `infrastructure`. The logging rule for
contributors is in `CLAUDE.md` ("Growth change logging").

---

## Connecting a ChatGPT connector or custom GPT

There is **no Vercel, Netlify or serverless layer in this project** and nothing to configure on
one. DrawReport is a Flask application served by gunicorn behind nginx on its own VPS, and the
API is part of that application. The token lives in one place only: `/var/www/DrawReport/.env`
on the server.

1. **Read the token** on the server, in a terminal rather than in a chat window:
   `ssh root@<host> "grep '^GROWTH_AGENT_TOKEN=' /var/www/DrawReport/.env | cut -d= -f2-"`
2. **Create the GPT** and open Configure, then Actions, then Create new action.
3. **Paste the schema** from `growth/DRAWREPORT_GROWTH_OPENAPI.yaml` into the Schema box. It
   already names `https://drawreport.com` as the server and declares all three operations.
4. **Set Authentication** to API Key, Auth Type **Bearer**, and paste the token as the key.
   Nothing else is needed; there is no OAuth flow and no callback URL.
5. **Test** with the built-in tester on `getGrowthSummary`, `from` 2026-09-01, `to` 2026-09-10.
   A 401 means the token is wrong or missing, a 503 means the server has no token configured.

The schema file is deliberately **not served over HTTP**. It describes the shape of a
token-protected endpoint, and there is no reason to publish that to anyone who asks; pasting it
into the builder is enough. It is also tracked in git, so the token must never be written into
it.

The operation descriptions inside the schema carry the three rules that keep an agent from
answering confidently and wrongly: use the engaged human count for people, never merge the two
attribution models, and treat a null money field as absent rather than zero.

## Known measurement limitations

1. **Bots.** Detection is user-agent only. Raw visits are dominated by scanners and by
   Facebook's link-preview fetchers, which even re-request the ad URL with truncated UTM
   values. Only `engaged` is a reliable human signal.
2. **Sample size.** At the time of writing the site has near-zero conversions; every rate
   is reported with a small-sample warning below 30 engaged visitors.
3. **No cost data.** Ad spend, CPC, CAC and ROAS cannot be computed from this API.
4. **No refunds, fees or net revenue.** Only gross booked revenue exists.
5. **Paid vs organic social.** `utm_medium=social` on a boosted post is identical for a paid
   click and an organic click. Use a distinct `utm_medium` (e.g. `paid`) per paid placement.
6. **Checkout is a black box.** PayPal's page is off-site; "orders created" is the last
   observable step before payment.
7. **Content pages.** There is no per-URL page-view record; blog traffic is visible only
   through entry paths and engaged events, which this API does not yet expose per URL.
8. **First-touch is UTM-only** (see attribution above).
9. **GA4, Search Console, Meta Ads Manager** data are not integrated and are not returned.
10. **Timezone.** Everything is UTC; daily buckets will not match a US-local day in Ads
    Manager.

---

## Examples

```bash
# What happened in the first ten days of September
curl -sS -H "Authorization: Bearer <TOKEN>" \
  "https://drawreport.com/internal/growth/summary?from=2026-09-01&to=2026-09-10"

# Which campaigns / content ids produced activity, top 20 rows per table
curl -sS -H "Authorization: Bearer <TOKEN>" \
  "https://drawreport.com/internal/growth/content?from=2026-09-01&to=2026-09-10&limit=20"

# Every growth-relevant change since the 1st
curl -sS -H "Authorization: Bearer <TOKEN>" \
  "https://drawreport.com/internal/growth/changes?since=2026-09-01T00:00:00Z"

# Expected failures
curl -sS -o /dev/null -w "%{http_code}\n" \
  "https://drawreport.com/internal/growth/summary?from=2026-09-01&to=2026-09-10"      # 401
curl -sS -H "Authorization: Bearer <TOKEN>" \
  "https://drawreport.com/internal/growth/summary?from=2026-09-10&to=2026-09-01"      # 400
```

Tests: `venv\Scripts\python.exe -m unittest discover -s tests -t .` (temporary database
and change log; production data is never touched).
