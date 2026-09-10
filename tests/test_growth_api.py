"""Growth Data API tests (stdlib unittest - pytest is not a project dependency).

Run:  venv\\Scripts\\python.exe -m unittest discover -s tests -t .

Everything runs against a TEMPORARY SQLite file and a temporary change log: settings
paths are patched before the app is created, so no test can touch data/ or the live log.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from config import settings

TOKEN = "test-token-not-a-real-one"
AUTH = {"Authorization": f"Bearer {TOKEN}"}

# Values that must NEVER appear in any response body.
PII_STRINGS = ["pii@example.com", "Zebulon", "tok-secret-1", "rpt-secret", "secret note",
               "data/free/", "Mozilla/5.0 (test UA)"]
# Column / field names that must never appear as JSON keys.
PII_KEYS = {"email", "child_name", "child_json", "token", "public_token", "free_token",
            "file_path", "image_path", "parent_text", "result_json", "phrase",
            "user_agent", "visitor_id", "visit_id", "payment_id", "order_id", "child",
            "pairs", "name"}

CHANGES = [
    {"id": "DR-CHG-0001", "timestamp": "2026-09-01T10:00:00Z", "category": "analytics",
     "title": "first", "reason": "r", "affected_area": [], "expected_metrics": [],
     "experiment_id": None, "author": "test", "notes": ""},
    {"id": "DR-CHG-0003", "timestamp": "2026-09-10T10:00:00+00:00", "category": "seo",
     "title": "third", "reason": "r", "affected_area": [], "expected_metrics": [],
     "experiment_id": None, "author": "test", "notes": ""},
    {"id": "DR-CHG-0002", "timestamp": "2026-09-05T10:00:00Z", "category": "pricing",
     "title": "second", "reason": "r", "affected_area": [], "expected_metrics": [],
     "experiment_id": None, "author": "test", "notes": ""},
]


def _all_keys(obj, out: set) -> set:
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k)
            _all_keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _all_keys(v, out)
    return out


class GrowthApiBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="dr-growth-test-"))
        cls._saved = {k: getattr(settings, k) for k in (
            "DATA_DIR", "DB_PATH", "FREE_DIR", "DRAWINGS_DIR", "REPORTS_DIR", "OUTBOX_DIR",
            "PRODUCTS_RUNTIME_FILE", "FREE_LIMITS_RUNTIME_FILE", "REPORT_TEXTS_RUNTIME_FILE",
            "GROWTH_CHANGES_FILE", "GROWTH_AGENT_TOKEN")}
        settings.DATA_DIR = cls.tmp / "data"
        settings.DB_PATH = settings.DATA_DIR / "test.sqlite3"
        settings.FREE_DIR = settings.DATA_DIR / "free"
        settings.DRAWINGS_DIR = settings.DATA_DIR / "drawings"
        settings.REPORTS_DIR = settings.DATA_DIR / "reports"
        settings.OUTBOX_DIR = settings.DATA_DIR / "outbox"
        settings.PRODUCTS_RUNTIME_FILE = settings.DATA_DIR / "products.json"
        settings.FREE_LIMITS_RUNTIME_FILE = settings.DATA_DIR / "free_limits.json"
        settings.REPORT_TEXTS_RUNTIME_FILE = settings.DATA_DIR / "report_texts.json"
        settings.GROWTH_CHANGES_FILE = cls.tmp / "growth_changes.jsonl"
        settings.GROWTH_AGENT_TOKEN = TOKEN
        lines = [json.dumps(c) for c in CHANGES] + ["", "{not json", '{"id": "x"}']
        settings.GROWTH_CHANGES_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

        from app import create_app
        cls.app = create_app()
        cls.app.testing = True
        cls._seed()

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._saved.items():
            setattr(settings, k, v)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def _seed(cls):
        from app.db import connect
        c = connect()
        # Visits. Window under test: 2026-09-05 .. 2026-09-06.
        visits = [
            # visit, visitor, started, engaged, device, channel, utm, gclid, geo
            ("v0", "A", "2026-08-01T10:00:00+00:00", 1, "desktop", "organic", None, None, "US"),
            ("v1", "A", "2026-09-05T10:00:00+00:00", 1, "desktop", "ads",
             json.dumps({"utm_source": "facebook", "utm_medium": "social",
                         "utm_campaign": "freemium", "utm_content": "curious-drawing"}),
             "fbclid-x", "US"),
            ("v2", "B", "2026-09-05T11:00:00+00:00", 0, "mobile", "direct", None, None, "DE"),
            ("v3", "C", "2026-09-05T12:00:00+00:00", 0, "bot", "direct", None, None, None),
            ("v4", "A", "2026-09-06T09:00:00+00:00", 1, "mobile", "organic", None, None, "US"),
            ("v5", "D", "2026-09-06T10:00:00+00:00", 1, "desktop", "referral", None, None, "GB"),
            ("v9", "E", "2026-09-20T10:00:00+00:00", 1, "desktop", "direct", None, None, "US"),
        ]
        for v in visits:
            c.execute(
                "INSERT INTO web_visits (visit_id, visitor_id, started_at, last_at, entry_path,"
                " exit_path, pages, engaged, device, channel, utm_json, gclid, referer,"
                " geo_country) VALUES (?,?,?,?,'/en/','/en/',2,?,?,?,?,?,NULL,?)",
                (v[0], v[1], v[2], v[2], v[3], v[4], v[5], v[6], v[7], v[8]))
        fb = visits[1][6]
        events = [
            ("A", "v1", "home_view", None, fb, "desktop"),
            ("A", "v1", "engaged", None, fb, "desktop"),
            ("A", "v1", "free_view", None, fb, "desktop"),
            ("A", "v1", "free_upload", json.dumps({"concern": "black"}), fb, "desktop"),
            ("A", "v1", "free_to_order", None, fb, "desktop"),
            ("A", "v4", "engaged", None, fb, "mobile"),
            ("B", "v2", "home_view", None, None, "mobile"),
            ("B", "v2", "free_upload_failed", json.dumps({"reason": "too_big"}), None, "mobile"),
            ("C", "v3", "home_view", None, None, "bot"),
            ("D", "v5", "engaged", None, None, "desktop"),
        ]
        for i, e in enumerate(events):
            c.execute(
                "INSERT INTO events (visitor_id, visit_id, type, path, payload_json, utm_json,"
                " user_agent, device, created_at) VALUES (?,?,?,'/en/',?,?,?,?,?)",
                (e[0], e[1], e[2], e[3], e[4], "Mozilla/5.0 (test UA)", e[5],
                 f"2026-09-05T10:{i:02d}:00+00:00"))
        c.execute(
            "INSERT INTO free_analyses (token, visitor_id, visit_id, email, child_name,"
            " child_name_norm, age, address_form, concern_key, parent_text, image_path,"
            " status, result_json, elapsed_s, locale, created_at, uploaded_at, done_at)"
            " VALUES ('tok-secret-1','A','v1','pii@example.com','Zebulon','zebulon',6,'he',"
            " 'black','secret note','data/free/tok-secret-1.jpg','done','{\"flags\":[]}',20.5,"
            " 'en','2026-09-05T10:05:00+00:00','2026-09-05T10:06:00+00:00',"
            " '2026-09-05T10:07:00+00:00')")
        c.execute(
            "INSERT INTO free_analyses (token, visitor_id, visit_id, email, child_name, age,"
            " concern_key, status, locale, created_at) VALUES ('tok-2','B','v2',"
            " 'pii@example.com','Zebulon',4,'neutral','draft','en','2026-09-05T11:05:00+00:00')")
        c.execute(
            "INSERT INTO free_analyses (token, visitor_id, visit_id, child_name, age,"
            " concern_key, status, reason_key, locale, created_at, uploaded_at, done_at)"
            " VALUES ('tok-3','D','v5','Zebulon',8,'black','insufficient','photo_poor','en',"
            " '2026-09-06T10:05:00+00:00','2026-09-06T10:06:00+00:00',"
            " '2026-09-06T10:07:00+00:00')")
        c.execute(
            "INSERT INTO orders (email, product_code, price_cents, coupon_code, locale, status,"
            " payment_id, child_json, visitor_id, visit_id, utm_json, free_token, created_at,"
            " paid_at) VALUES ('pii@example.com','snapshot',1900,'X10','en','delivered',"
            " 'PAYPAL-1','{\"name\":\"Zebulon\"}','A','v1',?, 'tok-secret-1',"
            " '2026-09-05T10:10:00+00:00','2026-09-05T10:12:00+00:00')", (fb,))
        c.execute(
            "INSERT INTO orders (email, product_code, price_cents, locale, status, child_json,"
            " visitor_id, visit_id, created_at) VALUES ('pii@example.com','snapshot',2900,"
            " 'en','created','{\"name\":\"Zebulon\"}','B','v2','2026-09-05T11:10:00+00:00')")
        c.execute(
            "INSERT INTO drawings (order_id, file_path, uploaded_at) VALUES (1,"
            " 'data/drawings/1/drawing_1.jpg','2026-09-05T10:10:00+00:00')")
        c.execute(
            "INSERT INTO reports (order_id, pdf_path, public_token, generated_at, attempts)"
            " VALUES (1,'data/reports/1/report.pdf','rpt-secret','2026-09-05T10:40:00+00:00',1)")
        c.commit()
        c.close()

    def get(self, path, headers=AUTH):
        return self.app.test_client().get(path, headers=headers)

    def assert_envelope(self, body: dict):
        for k in ("schema_version", "project", "generated_at", "period", "data_quality", "data"):
            self.assertIn(k, body)
        self.assertEqual(body["schema_version"], "1")
        self.assertEqual(body["project"], "drawreport")
        self.assertEqual(body["period"]["timezone"], "UTC")
        self.assertIn(body["data_quality"]["status"], ("ok", "partial"))
        self.assertIsInstance(body["data_quality"]["warnings"], list)

    def assert_no_pii(self, resp):
        text = resp.get_data(as_text=True)
        for s in PII_STRINGS:
            self.assertNotIn(s, text)
        keys = _all_keys(resp.get_json(), set())
        self.assertFalse(keys & PII_KEYS, f"forbidden keys present: {keys & PII_KEYS}")


class TestAuth(GrowthApiBase):
    def test_missing_token_401(self):
        r = self.get("/internal/growth/summary?from=2026-09-05&to=2026-09-06", headers={})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json()["error"]["code"], "unauthorized")
        self.assertIn("Bearer", r.headers.get("WWW-Authenticate", ""))

    def test_wrong_token_401(self):
        r = self.get("/internal/growth/summary?from=2026-09-05&to=2026-09-06",
                     headers={"Authorization": "Bearer nope"})
        self.assertEqual(r.status_code, 401)
        r = self.get("/internal/growth/changes?since=2026-01-01T00:00:00Z",
                     headers={"Authorization": f"Basic {TOKEN}"})
        self.assertEqual(r.status_code, 401)

    def test_unconfigured_token_503(self):
        saved = settings.GROWTH_AGENT_TOKEN
        settings.GROWTH_AGENT_TOKEN = ""
        try:
            r = self.get("/internal/growth/summary?from=2026-09-05&to=2026-09-06")
            self.assertEqual(r.status_code, 503)
            self.assertEqual(r.get_json()["error"]["code"], "not_configured")
            # And an empty bearer must not match an empty configured token.
            r = self.get("/internal/growth/changes?since=2026-01-01T00:00:00Z",
                         headers={"Authorization": "Bearer "})
            self.assertEqual(r.status_code, 503)
        finally:
            settings.GROWTH_AGENT_TOKEN = saved

    def test_correct_token_200(self):
        r = self.get("/internal/growth/summary?from=2026-09-05&to=2026-09-06")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("Cache-Control"), "no-store")

    def test_no_visit_row_created_by_api_calls(self):
        from app.db import connect
        c = connect()
        before = c.execute("SELECT COUNT(*) c FROM web_visits").fetchone()["c"]
        self.get("/internal/growth/summary?from=2026-09-05&to=2026-09-06")
        self.get("/internal/growth/summary?from=2026-09-05&to=2026-09-06", headers={})
        after = c.execute("SELECT COUNT(*) c FROM web_visits").fetchone()["c"]
        c.close()
        self.assertEqual(before, after)


class TestUrlTokenFallback(GrowthApiBase):
    """?token= exists for clients that cannot set an Authorization header."""

    URL = "/internal/growth/summary?from=2026-09-05&to=2026-09-06"

    def test_correct_url_token_200(self):
        r = self.get(f"{self.URL}&token={TOKEN}", headers={})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["traffic"]["visits_engaged_human"], 3)

    def test_url_token_works_on_every_endpoint(self):
        for path in (f"/internal/growth/content?from=2026-09-05&to=2026-09-06&token={TOKEN}",
                     f"/internal/growth/changes?since=2026-09-01T00:00:00Z&token={TOKEN}"):
            self.assertEqual(self.get(path, headers={}).status_code, 200, path)

    def test_wrong_url_token_401(self):
        self.assertEqual(self.get(f"{self.URL}&token=nope", headers={}).status_code, 401)
        self.assertEqual(self.get(f"{self.URL}&token=", headers={}).status_code, 401)

    def test_url_token_does_not_bypass_the_503(self):
        saved = settings.GROWTH_AGENT_TOKEN
        settings.GROWTH_AGENT_TOKEN = ""
        try:
            r = self.get(f"{self.URL}&token={TOKEN}", headers={})
            self.assertEqual(r.status_code, 503)
        finally:
            settings.GROWTH_AGENT_TOKEN = saved

    def test_header_still_works_and_wins(self):
        # A valid header with a junk query token must still succeed.
        r = self.get(f"{self.URL}&token=nope")
        self.assertEqual(r.status_code, 200)

    def test_token_is_never_echoed_back(self):
        r = self.get(f"{self.URL}&token={TOKEN}", headers={})
        self.assertNotIn(TOKEN, r.get_data(as_text=True))
        r = self.get(f"{self.URL}&token=nope", headers={})
        self.assertNotIn("nope", r.get_data(as_text=True))

    def test_token_arg_does_not_disturb_validation(self):
        r = self.get(f"/internal/growth/summary?from=bad&to=2026-09-06&token={TOKEN}",
                     headers={})
        self.assertEqual(r.status_code, 400)


class TestValidation(GrowthApiBase):
    def test_invalid_dates_400(self):
        for q in ("from=2026-09-05", "to=2026-09-05", "from=bad&to=2026-09-05",
                  "from=2026-09-06&to=2026-09-05", "from=2026-9-5&to=2026-09-06",
                  "from=2020-01-01&to=2026-09-06"):
            r = self.get(f"/internal/growth/summary?{q}")
            self.assertEqual(r.status_code, 400, q)
            self.assertEqual(r.get_json()["error"]["code"], "bad_request")
            r = self.get(f"/internal/growth/content?{q}")
            self.assertEqual(r.status_code, 400, q)

    def test_bad_limit_400_and_cap(self):
        r = self.get("/internal/growth/content?from=2026-09-05&to=2026-09-06&limit=abc")
        self.assertEqual(r.status_code, 400)
        r = self.get("/internal/growth/content?from=2026-09-05&to=2026-09-06&limit=0")
        self.assertEqual(r.status_code, 400)
        r = self.get("/internal/growth/content?from=2026-09-05&to=2026-09-06&limit=99999")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["limit"], 200)

    def test_changes_since_required_and_validated(self):
        self.assertEqual(self.get("/internal/growth/changes").status_code, 400)
        self.assertEqual(self.get("/internal/growth/changes?since=yesterday").status_code, 400)


class TestChanges(GrowthApiBase):
    def test_parsing_and_ordering(self):
        from app.growth import load_changes
        entries, bad = load_changes(settings.GROWTH_CHANGES_FILE)
        self.assertEqual(bad, 2)
        self.assertEqual([e["id"] for e in entries],
                         ["DR-CHG-0001", "DR-CHG-0002", "DR-CHG-0003"])

    def test_endpoint_filters_and_sorts(self):
        r = self.get("/internal/growth/changes?since=2026-09-05T00:00:00Z")
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assert_envelope(body)
        self.assertEqual(body["data"]["count"], 2)
        self.assertEqual([c["id"] for c in body["data"]["changes"]],
                         ["DR-CHG-0002", "DR-CHG-0003"])
        self.assertNotIn("_ts", body["data"]["changes"][0])
        self.assertIn("malformed", " ".join(body["data_quality"]["warnings"]))
        self.assertNotIn(str(self.tmp), r.get_data(as_text=True))

    def test_real_change_log_is_valid(self):
        """The tracked growth/growth_changes.jsonl must parse cleanly with sequential ids."""
        from app.growth import load_changes
        real = Path(__file__).resolve().parent.parent / "growth" / "growth_changes.jsonl"
        entries, bad = load_changes(real)
        self.assertEqual(bad, 0)
        self.assertGreaterEqual(len(entries), 1)
        ids = [e["id"] for e in entries]
        self.assertEqual(ids, [f"DR-CHG-{i:04d}" for i in range(1, len(ids) + 1)])
        allowed = {"analytics", "attribution", "funnel", "landing_page", "pricing", "seo",
                   "social", "content", "retention", "product", "email", "infrastructure"}
        for e in entries:
            self.assertIn(e["category"], allowed)
            for k in ("title", "reason", "affected_area", "expected_metrics",
                      "experiment_id", "author", "notes"):
                self.assertIn(k, e)


class TestSummary(GrowthApiBase):
    def test_schema_and_counts(self):
        r = self.get("/internal/growth/summary?from=2026-09-05&to=2026-09-06")
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assert_envelope(body)
        self.assertEqual(body["period"], {"from": "2026-09-05", "to": "2026-09-06",
                                          "timezone": "UTC"})
        d = body["data"]
        for k in ("traffic", "funnel", "commercial", "attribution"):
            self.assertIn(k, d)
        t = d["traffic"]
        self.assertEqual(t["primary_metric"], "visits_engaged_human")
        self.assertEqual(t["visits_raw"], 5)             # v1..v5 (v0, v9 outside)
        self.assertEqual(t["visits_non_bot"], 4)
        self.assertEqual(t["visits_engaged_human"], 3)   # v1, v4, v5
        self.assertEqual(t["visitors_unique_engaged_human"], 2)   # A, D
        self.assertEqual(t["engaged_human_new_vs_returning"], {"new": 1, "returning": 2})
        self.assertEqual(t["device_engaged_human"], {"desktop": 2, "mobile": 1})
        self.assertEqual(t["countries_engaged_human"][0], {"country": "US", "engaged_visits": 2})
        # bot share is called out, not hidden
        self.assertTrue(any("bots" in w for w in body["data_quality"]["warnings"]))
        self.assertEqual(body["data_quality"]["status"], "partial")

        f = d["funnel"]["free"]
        self.assertEqual(f["questionnaires_completed"], 3)
        self.assertEqual(f["uploads"], 2)
        self.assertEqual(f["completions"], 1)
        self.assertEqual(f["email_only_no_drawing"], 1)
        self.assertEqual(f["failures_by_reason"], {"photo_poor": 1})
        self.assertEqual(f["uploads_refused_by_reason"], {"too_big": 1})
        self.assertEqual(f["to_paid_click_visitors"], 1)
        self.assertEqual(f["to_paid_transitions"]["direct"],
                         {"orders": 1, "paid_orders": 1, "gross_revenue_usd": 19.0})
        o = d["funnel"]["orders"]
        self.assertEqual(o["orders_created"], 2)
        self.assertEqual(o["paid_orders"], 1)
        self.assertEqual(o["reports_delivered"], 1)
        self.assertEqual(len(d["funnel"]["doors"]), 2)
        self.assertIn("steps", d["funnel"]["doors"][0])

        c = d["commercial"]
        self.assertEqual(c["gross_revenue_usd"], 19.0)
        self.assertEqual(c["paid_orders"], 1)
        self.assertEqual(c["average_order_value_usd"], 19.0)
        self.assertEqual(c["coupon_orders"], 1)
        for k in ("ad_spend_usd", "refunds_usd", "net_revenue_usd", "paypal_fees_usd"):
            self.assertIsNone(c[k])

        a = d["attribution"]
        self.assertIn("last_touch", a)
        self.assertIn("first_touch", a)
        lt_ch = {row["channel"]: row for row in a["last_touch"]["by_channel"]}
        self.assertEqual(lt_ch["ads"]["engaged_visits"], 1)
        self.assertEqual(lt_ch["ads"]["paid_orders"], 1)
        self.assertEqual(lt_ch["ads"]["gross_revenue_usd"], 19.0)
        self.assertEqual(lt_ch["direct"]["orders_created"], 1)
        self.assertEqual(lt_ch["direct"]["paid_orders"], 0)
        lt_camp = a["last_touch"]["by_utm_campaign"][0]
        self.assertEqual((lt_camp["source"], lt_camp["campaign"]), ("facebook", "freemium"))
        # First touch: visitor A's cookie says facebook on BOTH visits (v1 ads, v4 organic).
        ft_camp = a["first_touch"]["by_utm_campaign"][0]
        self.assertEqual(ft_camp["campaign"], "freemium")
        self.assertEqual(ft_camp["engaged_visits"], 2)
        self.assertEqual(a["last_touch"]["by_utm_campaign"][0]["engaged_visits"], 1)
        self.assertEqual(ft_camp["free_uploads"], 1)
        self.assertEqual(ft_camp["free_completions"], 1)
        self.assertEqual(ft_camp["paid_orders"], 1)
        self.assertEqual(a["first_touch"]["untagged"]["visitors"], 2)   # B, D
        self.assert_no_pii(r)

    def test_empty_window_is_valid(self):
        r = self.get("/internal/growth/summary?from=2025-01-01&to=2025-01-31")
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assert_envelope(body)
        self.assertEqual(body["data"]["traffic"]["visits_raw"], 0)
        self.assertIsNone(body["data"]["commercial"]["average_order_value_usd"])
        self.assertEqual(body["data"]["attribution"]["last_touch"]["by_channel"], [])
        self.assert_no_pii(r)


class TestContent(GrowthApiBase):
    def test_schema_and_rows(self):
        r = self.get("/internal/growth/content?from=2026-09-05&to=2026-09-06")
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assert_envelope(body)
        d = body["data"]
        for model in ("last_touch", "first_touch"):
            for level in ("content", "campaign", "source"):
                self.assertIsInstance(d[model][level], list)
            self.assertIn("untagged", d[model])
        row = d["last_touch"]["content"][0]
        for k in ("content_id", "source", "medium", "campaign", "engaged_visits",
                  "free_uploads", "free_completions", "orders_created", "paid_orders",
                  "gross_revenue_usd", "level", "visits", "visitors"):
            self.assertIn(k, row)
        self.assertEqual(row["content_id"], "curious-drawing")
        self.assertEqual(row["source"], "facebook")
        self.assertEqual(row["engaged_visits"], 1)
        self.assertEqual(row["free_uploads"], 1)
        self.assertEqual(row["free_completions"], 1)
        self.assertEqual(row["orders_created"], 1)
        self.assertEqual(row["paid_orders"], 1)
        self.assertEqual(row["gross_revenue_usd"], 19.0)
        # The two models disagree on visits for the same content id, and both are shown.
        self.assertEqual(d["first_touch"]["content"][0]["engaged_visits"], 2)
        self.assertEqual(d["last_touch"]["untagged"]["orders_created"], 1)
        self.assertEqual(d["last_touch"]["unattributed"]["orders_created"], 0)
        self.assert_no_pii(r)

    def test_limit_applies(self):
        r = self.get("/internal/growth/content?from=2026-09-05&to=2026-09-06&limit=1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["limit"], 1)
        self.assertLessEqual(len(r.get_json()["data"]["last_touch"]["source"]), 1)


class TestPrivacy(GrowthApiBase):
    def test_no_pii_in_any_endpoint(self):
        for path in ("/internal/growth/summary?from=2026-08-01&to=2026-09-30",
                     "/internal/growth/content?from=2026-08-01&to=2026-09-30",
                     "/internal/growth/changes?since=2026-01-01T00:00:00Z"):
            r = self.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assert_no_pii(r)

    def test_errors_are_opaque(self):
        r = self.get("/internal/growth/summary?from=bad&to=bad", headers={})
        # auth is checked before validation: an unauthenticated caller learns nothing
        self.assertEqual(r.status_code, 401)
        body = r.get_json()
        self.assertEqual(set(body), {"schema_version", "project", "error"})


if __name__ == "__main__":
    unittest.main()
