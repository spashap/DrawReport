# DrawReport Growth Connector Handoff

Everything an external Growth Lab connector needs to consume the DrawReport Growth Data API,
and nothing else. No token value appears in this file; request it from the site owner.

---

## 1. Production base URL

```
https://drawreport.com
```

TLS only. Plain HTTP redirects to HTTPS, and `www` redirects to the apex host. Point the
connector at the apex host directly to avoid a redirect hop.

---

## 2. Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/internal/growth/summary` | Traffic, funnels, commercial totals, both attribution models |
| GET | `/internal/growth/content` | Campaign and content-identifier breakdowns, both attribution models |
| GET | `/internal/growth/changes` | The growth change log: what the team changed and when |

All three are read-only. Nothing in this API writes, and there are no other verbs.

---

## 3. Query parameters

| Parameter | Endpoints | Required | Format and rules |
|---|---|---|---|
| `from` | summary, content | yes | `YYYY-MM-DD`, exactly 10 characters. Inclusive first day, UTC. |
| `to` | summary, content | yes | `YYYY-MM-DD`. Inclusive last day, UTC. Must not precede `from`. |
| `since` | changes | yes | ISO-8601 timestamp. `Z` and `+00:00` both accepted; a value with no offset is read as UTC. |
| `limit` | content | no | Integer ≥ 1. Default 50, silently capped at 200. Echoed back as `data.limit`. |
| `limit` | changes | no | Integer ≥ 1. Default and cap 500. |
| `token` | all | no | Compatibility authentication, see section 4. |

Unknown parameters are ignored.

---

## 4. Authentication

**Preferred, use this whenever the client can set a header:**

```
Authorization: Bearer <TOKEN>
```

**Compatibility fallback**, for clients that cannot attach an arbitrary request header:

```
GET /internal/growth/summary?from=...&to=...&token=<TOKEN>
```

Both mechanisms accept the same token and are compared in constant time. The header wins when
both are present.

Notes a connector author must know:

- The token is a single dedicated credential. It is not the site admin password and grants no
  access to anything except these three endpoints.
- A token in a URL is more exposed than one in a header. It lands in the caller's history and
  in any intermediate proxy. The DrawReport server strips query strings from its own access
  log for this path, but that protects one hop only. Treat a URL token as rotatable and move
  to the header as soon as the client supports it.
- Rotation is a server-side change with no client change beyond the new value. Assume it can
  happen without notice and surface a clear error rather than caching a token indefinitely.
- Do not embed the token in client-side code, a repository, or a shared document.

---

## 5. HTTP error behaviour

| Status | When | Body |
|---|---|---|
| 200 | Success | Full envelope, section 6 |
| 400 | Bad or missing dates, reversed range, range over the limit, bad `limit`, missing or unparseable `since` | Error envelope, `code` is `bad_request` |
| 401 | Missing, malformed or wrong token | Error envelope, `code` is `unauthorized`, plus a `WWW-Authenticate: Bearer` header |
| 404 | No such endpoint under `/internal/` | Error envelope, `code` is `not_found` |
| 503 | The server has no token configured, so the API is switched off | Error envelope, `code` is `not_configured` |
| 500 | Unexpected server fault | Error envelope, `code` is `internal_error`, message is deliberately generic |

Error body shape, identical for every failure:

```json
{
  "schema_version": "1",
  "project": "drawreport",
  "error": { "code": "bad_request", "message": "from must not be after to" }
}
```

Every response, success or failure, carries `Cache-Control: no-store`. Server-side faults are
logged on the server; the caller never receives SQL, stack traces or file paths. Distinguish
401 from 503 in your retry logic: 401 means fix the credential, 503 means the operator has
switched the API off and retrying with a different token will not help.

---

## 6. Response envelope

Every successful response has exactly this outer shape:

```json
{
  "schema_version": "1",
  "project": "drawreport",
  "generated_at": "2026-09-10T14:00:00+00:00",
  "period": { "from": "2026-08-12", "to": "2026-09-10", "timezone": "UTC" },
  "data_quality": { "status": "ok", "warnings": [] },
  "data": { }
}
```

| Field | Meaning |
|---|---|
| `schema_version` | Currently `"1"`. A breaking change to `data` will increment it. Assert on it. |
| `project` | Always `"drawreport"`. Use it to guard against pointing at the wrong host. |
| `generated_at` | UTC timestamp when the response was computed. Not cached. |
| `period.from` / `period.to` | The window actually used. For `/changes` these are the `since` you sent and the current time. |
| `period.timezone` | Always `UTC`. |
| `data_quality.status` | `ok` or `partial`. `partial` whenever there is at least one warning. |
| `data_quality.warnings` | Plain sentences naming every metric that is null and every known bias in the window. **Read these before quoting any number.** In practice a summary response is almost always `partial`, because the unavailable money fields always warn. |
| `data` | The payload, different per endpoint. |

Top-level blocks in `data`:

- **summary**: `traffic`, `funnel` (with `doors`, `free`, `orders`), `commercial`, `attribution`.
- **content**: `grouping`, `limit`, `last_touch`, `first_touch`.
- **changes**: `changes` (array) and `count`.

---

## 7. Interpretation rules specific to this project

These are not style preferences. Ignoring them produces confidently wrong conclusions.

**7.1 Use `visits_engaged_human` when you mean people.** Raw traffic to this site is dominated
by crawlers, scanners and social link-preview fetchers. Three counts are returned deliberately:

| Field | What it is |
|---|---|
| `visits_raw` | Everything, bots included. Never quote as an audience. |
| `visits_non_bot` | User-agent filtering only, so still inflated by anything with a browser-like agent. |
| `visits_engaged_human` | A non-bot visit that scrolled, clicked, or stayed 15 seconds. The trustworthy count. |

The response names this itself in `traffic.primary_metric`. Recent windows have shown roughly
forty thousand raw visits against low hundreds of engaged human ones, so the difference is not
a rounding matter.

**7.2 Never merge the two attribution models.** Both are returned, side by side, under their
own names, and they routinely disagree because they answer different questions.

| Model | Question it answers | Tagged from | Joined by |
|---|---|---|---|
| `last_touch` | Which click produced this outcome | The visit's own UTM tags, click identifier, referrer, and a derived channel | The visit the outcome happened in |
| `first_touch` | Where did this person originally come from | A one-year first-touch UTM cookie | The visitor identity |

A person who arrived from an ad, left, and returned through search is `organic` in last touch
and the ad campaign in first touch. Both are correct. State which model any claim rests on.

**7.3 First touch is UTM-only.** The first-touch cookie is set only when a UTM was present on
the inbound link, so organic, referral and direct first visits appear under `untagged`.
`untagged` does not mean direct.

**7.4 Absent is not zero.** `ad_spend_usd`, `refunds_usd`, `net_revenue_usd` and
`paypal_fees_usd` are always `null` because the system does not store them. Cost per
acquisition, return on ad spend and net revenue therefore cannot be computed from this API.
They require spend figures from the advertising platform, combined outside DrawReport.

**7.5 Nothing is guessed.** A campaign or content row exists only where that tag was actually
present on the inbound link. Everything else is summed into `untagged`. Outcomes whose
originating visit falls outside the requested window, or was bot-flagged, appear in
`last_touch.unattributed` rather than being assigned to a bucket.

**7.6 Two revenue definitions coexist, both labelled.** `commercial.gross_revenue_usd` counts
by payment date. Revenue inside an attribution row counts paid orders by creation date,
because an order can only be attributed to the visit that created it. They can differ.

**7.7 Revenue is gross and after coupon.** It is the amount charged. No fees are deducted, and
refunds are not tracked at all.

**7.8 Small samples.** This site currently produces very few conversions. Any rate computed
over a short window is not statistically meaningful, and the response warns when the window
holds fewer than thirty engaged human visitors.

**7.9 Everything is UTC.** Daily buckets will not line up with a United States local day in an
advertising platform's reporting.

**7.10 Read `/changes` before explaining a movement.** A shift in the numbers may simply follow
a price change, a landing-page rewrite or a tracking change made on that date. Entries carry a
category, a reason, the affected area, and the metrics the author expected to move.

---

## 8. Limits

| Limit | Value |
|---|---|
| Maximum date range per request | 400 days. A longer window returns 400. |
| `limit` on `/content` | Default 50, hard cap 200 per table |
| `limit` on `/changes` | Default and hard cap 500 entries |
| Request rate | No rate limiter is enforced. Be considerate: the site runs on a single small server that also serves customers. Poll no more than a few times an hour, and cache within a period rather than re-requesting the same window. |
| Response size | Uncapped in principle, bounded in practice by the row limits above. A 30-day summary is roughly 11 KB. |

Requests to `/internal/` are excluded from the site's own visitor analytics, so polling does
not contaminate the numbers being read.

---

## 9. Privacy guarantee

Responses contain aggregated counts and money only. No email addresses, no children's names,
no free-text notes, no drawings, no report content, no visitor, visit or order identifiers, no
IP addresses and no user agents. This is verified automatically: the production check walks
every response and fails if a forbidden field name or an email address appears anywhere.

---

## 10. Deployment verification status

**Verified against production on 2026-09-10, application version V0.072. Result: PASS.**

48 automated checks run directly against `https://drawreport.com`, all passing:

| Area | Checks | Result |
|---|---|---|
| Authentication | No credentials, wrong token, valid bearer, URL-token fallback, cache header | pass |
| Endpoints | summary, content, changes all return 200 | pass |
| Envelope | `project`, `schema_version`, `period.timezone`, `data_quality` on all three | pass |
| Summary payload | `visits_engaged_human` present, counts nest correctly, both funnel doors, free and orders funnels, unavailable money null | pass |
| Attribution | `first_touch` and `last_touch` both present and separate, no blended key | pass |
| Content payload | Both models, content/campaign/source tables, untagged reported, required metrics on every row | pass |
| Changes | Change log returned, identifiers sequential, oldest first, full schema per entry | pass |
| Privacy | No forbidden field names, no email addresses, token never echoed | pass |
| Errors | Bad date, reversed range, over-long range, missing `since`, unknown path all return the JSON error envelope | pass |

The window used for verification was the 30 days ending 2026-09-10, and the summary returned
real production data rather than an empty document.

One defect was found and fixed during this verification: an unknown path under `/internal/`
previously returned the site's HTML error page instead of a JSON error envelope, which would
have broken a client parsing JSON. It now returns the standard error envelope with code
`not_found`.

A separate suite of 25 unit tests runs against a temporary database and covers the same
contract offline.

---

## 11. Out of scope

The DrawReport application deliberately contains no connector-side machinery: no MCP server,
no OpenAI or Google integration, and no gateway. It exposes these three HTTP endpoints and
nothing more. Any orchestration, scheduling, caching or model integration belongs on the
Growth Lab side.
