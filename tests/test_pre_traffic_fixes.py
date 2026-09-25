"""Pre-traffic fixes (2026-09-25 technical sanity check, V0.078).

Run:  venv\\Scripts\\python.exe -m unittest discover -s tests -t .

  1. form_started: the order form sent it as a raw beacon (stored as
     click:form_started, no path) while the funnel counted "form_started", a name nothing
     ever stored. The funnel now counts click:form_started and the form sends it through
     drGoal like every other goal.
  2. The order form used class names no stylesheet defined.
  3. The free -> paid CTA promised "the drawing is already uploaded" and the order form
     arrived empty. It now continues the free reading: prefill + the drawing reused
     server-side, only for the browser that uploaded it.
  4. The free-reading token (the only key to a child's drawing) reached GA4 and the Meta
     Pixel through /en/order?free=<token> and through GA4 on /free/r/<token>.
  5. free_upload_submit (= Meta Lead) fired on every click, including rejected ones.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from config import settings

REPO = Path(__file__).resolve().parents[1]
TEST_PNG = REPO / "data" / "test_drawing.png"


class PreTrafficFixesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="dr-pretraffic-test-"))
        cls._saved = {k: getattr(settings, k) for k in (
            "DATA_DIR", "DB_PATH", "FREE_DIR", "DRAWINGS_DIR", "REPORTS_DIR", "OUTBOX_DIR",
            "PRODUCTS_RUNTIME_FILE", "FREE_LIMITS_RUNTIME_FILE", "REPORT_TEXTS_RUNTIME_FILE",
            "GA_MEASUREMENT_ID", "META_PIXEL_ID", "PAYMENT_BACKEND")}
        settings.DATA_DIR = cls.tmp / "data"
        settings.DB_PATH = settings.DATA_DIR / "test.sqlite3"
        settings.FREE_DIR = settings.DATA_DIR / "free"
        # orders.py stores drawing paths relative to BASE_DIR, so this test's order
        # drawings must live under it (data/ is gitignored); removed in tearDownClass.
        (settings.BASE_DIR / "data").mkdir(exist_ok=True)
        cls.drawings_tmp = Path(tempfile.mkdtemp(prefix="test-drawings-",
                                                 dir=settings.BASE_DIR / "data"))
        settings.DRAWINGS_DIR = cls.drawings_tmp
        settings.REPORTS_DIR = settings.DATA_DIR / "reports"
        settings.OUTBOX_DIR = settings.DATA_DIR / "outbox"
        settings.PRODUCTS_RUNTIME_FILE = settings.DATA_DIR / "products.json"
        settings.FREE_LIMITS_RUNTIME_FILE = settings.DATA_DIR / "free_limits.json"
        settings.REPORT_TEXTS_RUNTIME_FILE = settings.DATA_DIR / "report_texts.json"
        # Both third-party tags ON, so "not rendered" is a real assertion.
        settings.GA_MEASUREMENT_ID = "G-TEST123"
        settings.META_PIXEL_ID = "999999"
        settings.PAYMENT_BACKEND = "stub"

        from app import create_app
        cls.app = create_app()
        cls.app.testing = True

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._saved.items():
            setattr(settings, k, v)
        shutil.rmtree(cls.tmp, ignore_errors=True)
        shutil.rmtree(cls.drawings_tmp, ignore_errors=True)

    @property
    def base(self) -> str:
        return settings.PUBLIC_BASE_URL.rstrip("/")

    def client(self):
        return self.app.test_client()

    # A browser UA: the default "Werkzeug/x" has no "mozilla" and is booked as a bot,
    # which every funnel excludes.
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0 Safari/537.36"}

    def get(self, c, path, **kw):
        return c.get(path, base_url=self.base, headers=self.UA, **kw)

    def post(self, c, path, **kw):
        return c.post(path, base_url=self.base, headers=self.UA, **kw)

    def _db(self):
        import sqlite3
        conn = sqlite3.connect(settings.DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _free_reading(self, status="done", with_image=True, email="parent@example.com",
                      address="she") -> str:
        """A finished free reading, as free_jobs would leave it."""
        from app.db import new_token, now
        settings.FREE_DIR.mkdir(parents=True, exist_ok=True)
        token = new_token(12)
        path = None
        if with_image:
            path = settings.FREE_DIR / f"{token}.png"
            shutil.copyfile(TEST_PNG, path)
        conn = self._db()
        conn.execute(
            "INSERT INTO free_analyses (token, child_name, child_name_norm, age,"
            " address_form, concern_key, status, email, image_path, locale, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (token, "Mia", "mia", 6, address, "neutral", status, email,
             str(path) if path else None, "en", now()))
        conn.commit()
        conn.close()
        return token

    def _as_owner(self, c, token):
        """The browser that uploaded the drawing carries it in the dr_free scope cookie."""
        c.set_cookie("dr_free", json.dumps([token]))

    def _order_page(self, c):
        return self.get(c, f"/{settings.DEFAULT_LOCALE}/order").get_data(as_text=True)

    # --- 1. form_started --------------------------------------------------------------

    def test_funnel_counts_the_name_the_beacon_actually_stores(self):
        from app import admin_funnels as fn
        markers = {m for _l, m, _k in fn.PAID_STEPS}
        self.assertIn("click:form_started", markers)
        self.assertNotIn("form_started", markers)

    def test_form_started_beacon_lands_in_the_paid_funnel(self):
        """End to end: open the form, send the goal the way drGoal does, count it."""
        from app import admin_funnels as fn
        c = self.client()
        self.get(c, f"/{settings.DEFAULT_LOCALE}/report")
        self._order_page(c)
        self.post(c, "/t/e", data={"g": "form_started",
                                   "p": f"/{settings.DEFAULT_LOCALE}/order"})
        conn = self._db()
        row = conn.execute("SELECT type, path FROM events WHERE type LIKE '%form_started'"
                           " ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(row["type"], "click:form_started")
        self.assertEqual(row["path"], f"/{settings.DEFAULT_LOCALE}/order")
        out = fn.build(conn, "2000-01-01")
        conn.close()
        paid = next(d for d in out["doors"] if d["key"] == "paid")
        started = next(r for r in paid["steps"] if r["label"] == "Started filling it in")
        self.assertGreaterEqual(started["n"], 1)

    def test_order_form_sends_form_started_through_drgoal(self):
        js = (REPO / "static" / "js" / "order.js").read_text(encoding="utf-8")
        self.assertIn('drGoal("form_started")', js)
        html = self._order_page(self.client())
        self.assertNotIn("sendBeacon", html, "no raw beacon left in the template")
        self.assertIn("/static/js/order.js", html)

    # --- 2. styling ----------------------------------------------------------------------

    def test_order_form_uses_design_system_classes_only(self):
        html = self._order_page(self.client())
        for cls in ('class="field"', 'class="input', "form-card", "file-drop", "ym-row"):
            self.assertIn(cls, html)
        for dead in ('class="form-row', 'class="draw-block', "field-err", 'class="ym"'):
            self.assertNotIn(dead, html, f"{dead} has no CSS")
        css = (REPO / "static" / "css" / "components.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.input \{[^}]*font-size: 16px")   # no iOS focus-zoom

    def test_drawing_blocks_two_and_three_start_hidden(self):
        html = self._order_page(self.client())
        self.assertRegex(html, r'data-n="2"\s+hidden')
        self.assertRegex(html, r'data-n="3"\s+hidden')
        self.assertNotRegex(html, r'data-n="1"\s+hidden')

    # --- 3. free -> paid handoff ------------------------------------------------------------

    def test_to_order_redirect_carries_no_token_in_the_url(self):
        token = self._free_reading()
        c = self.client()
        r = self.post(c, f"/free/to-order/{token}")
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(token, r.headers["Location"])
        self.assertNotIn("free=", r.headers["Location"])
        self.assertIn(token, r.headers.get("Set-Cookie", ""))
        self.assertIn("HttpOnly", r.headers.get("Set-Cookie", ""))
        self.assertEqual(r.headers.get("Referrer-Policy"), "no-referrer")

    def test_owner_gets_prefill_and_reused_drawing_without_the_token_in_markup(self):
        token = self._free_reading()
        c = self.client()
        self._as_owner(c, token)
        self.post(c, f"/free/to-order/{token}")
        html = self._order_page(c)
        self.assertIn('value="Mia"', html)
        self.assertIn('value="parent@example.com"', html)
        self.assertRegex(html, r'<option value="f" selected>')
        self.assertIn("Already attached from your free reading", html)
        self.assertIn("data:image/jpeg;base64,", html)
        self.assertNotIn(token, html, "the token must not be in the page at all")
        self.assertNotIn('name="d1_file"', html, "drawing 1 must not ask for a file")

    def test_handoff_page_loads_no_third_party_tags(self):
        """It shows a drawing; the Privacy Policy says the pixel is not loaded there."""
        token = self._free_reading()
        c = self.client()
        self._as_owner(c, token)
        self.post(c, f"/free/to-order/{token}")
        html = self._order_page(c)
        self.assertNotIn("googletagmanager.com", html)
        self.assertNotIn("fbevents.js", html)
        self.assertIn("/static/js/track.js", html, "first-party tracking stays")

    def test_plain_order_page_still_loads_both_tags(self):
        html = self._order_page(self.client())
        self.assertIn("googletagmanager.com", html)
        self.assertIn("fbevents.js", html)

    def test_token_without_ownership_reuses_nothing(self):
        """A forwarded result link on another device: attribution yes, prefill no."""
        token = self._free_reading()
        c = self.client()
        self.post(c, f"/free/to-order/{token}")        # no dr_free scope cookie
        html = self._order_page(c)
        self.assertNotIn("Already attached", html)
        self.assertNotIn("parent@example.com", html)
        self.assertIn('name="d1_file"', html)

    def test_unfinished_or_deleted_reading_is_not_reused(self):
        for kw in ({"status": "insufficient"}, {"with_image": False}):
            token = self._free_reading(**kw)
            c = self.client()
            self._as_owner(c, token)
            self.post(c, f"/free/to-order/{token}")
            self.assertNotIn("Already attached", self._order_page(c), kw)

    def test_a_path_outside_free_dir_is_never_reused(self):
        token = self._free_reading()
        conn = self._db()
        conn.execute("UPDATE free_analyses SET image_path = ? WHERE token = ?",
                     (str(TEST_PNG), token))                       # outside FREE_DIR
        conn.commit()
        conn.close()
        c = self.client()
        self._as_owner(c, token)
        self.post(c, f"/free/to-order/{token}")
        self.assertNotIn("Already attached", self._order_page(c))

    def test_legacy_free_query_is_moved_into_the_cookie_before_any_page(self):
        token = self._free_reading()
        r = self.get(self.client(),
                     f"/{settings.DEFAULT_LOCALE}/order?free={token}&product=snapshot")
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(token, r.headers["Location"])
        self.assertIn("product=snapshot", r.headers["Location"])
        self.assertIn(token, r.headers.get("Set-Cookie", ""))

    def test_order_with_reused_drawing_needs_no_upload_and_keeps_attribution(self):
        token = self._free_reading()
        c = self.client()
        self._as_owner(c, token)
        self.post(c, f"/free/to-order/{token}")
        r = self.post(c, f"/{settings.DEFAULT_LOCALE}/order", data={
            "product": "snapshot", "child_name": "Mia", "child_gender": "f",
            "child_birth_ym_m": "03", "child_birth_ym_y": "2019",
            "d1_drawn_at_m": "08", "d1_drawn_at_y": "2026", "d1_theme": "A house",
            "email": "parent@example.com",
        })
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True)[:500])
        conn = self._db()
        o = conn.execute("SELECT id, free_token FROM orders ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(o["free_token"], token)
        d = conn.execute("SELECT file_path FROM drawings WHERE order_id = ?",
                         (o["id"],)).fetchall()
        conn.close()
        self.assertEqual(len(d), 1)
        self.assertTrue((settings.BASE_DIR / d[0]["file_path"]).exists()
                        or Path(d[0]["file_path"]).exists())
        self.assertIn("dr_order_free=;", r.headers.get("Set-Cookie", ""),
                      "the handoff cookie is cleared once the order exists")

    def test_validation_error_keeps_the_reused_drawing(self):
        token = self._free_reading()
        c = self.client()
        self._as_owner(c, token)
        self.post(c, f"/free/to-order/{token}")
        r = self.post(c, f"/{settings.DEFAULT_LOCALE}/order",
                      data={"product": "snapshot", "child_name": "Mia"})
        self.assertEqual(r.status_code, 400)
        html = r.get_data(as_text=True)
        self.assertIn("Already attached", html)
        self.assertNotIn("Upload at least one drawing", html)
        self.assertIn('class="err"', html)

    # --- 4. privacy -------------------------------------------------------------------------

    def test_reading_page_has_no_third_party_tags_and_no_referrer(self):
        token = self._free_reading(status="queued")    # same URL, the waiting state
        c = self.client()
        self._as_owner(c, token)
        r = self.get(c, f"/free/r/{token}")
        html = r.get_data(as_text=True)
        self.assertNotIn("googletagmanager.com", html)
        self.assertNotIn("fbevents.js", html)
        self.assertEqual(r.headers.get("Referrer-Policy"), "no-referrer")

    # --- 5. Lead only on an accepted upload ----------------------------------------------------

    def test_lead_goal_is_not_a_click_attribute_any_more(self):
        tpl = (REPO / "templates" / "_free_summary.html").read_text(encoding="utf-8")
        self.assertNotIn('data-goal="free_upload_submit"', tpl)
        js = (REPO / "static" / "js" / "free.js").read_text(encoding="utf-8")
        i_ok = js.index("res.s === 200 && res.j.ok")
        i_goal = js.index('drGoal("free_upload_submit")')
        self.assertGreater(i_goal, i_ok, "the goal must sit inside the success branch")
        self.assertEqual(js.count('drGoal("free_upload_submit")'), 1)


if __name__ == "__main__":
    unittest.main()
