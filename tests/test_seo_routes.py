"""SEO surface tests: canonical redirects, robots.txt, sitemap.xml, /llms.txt.

Run:  venv\\Scripts\\python.exe -m unittest discover -s tests -t .

These cover the three things a live audit on 2026-09-22 found or nearly missed:

  1. www + a legacy article URL cost TWO 301s. Google's indexed URL for the
     best-performing article is https://www.drawreport.com/blog/<old>.html, and it
     was redirected once to the apex and again to /en/blog/<slug>. Both app-side
     redirects must therefore emit an ABSOLUTE url on the canonical host, so the
     nginx www block can proxy them and the chain collapses to one hop. nginx is
     not exercised here - only the half of the contract that lives in Python, which
     is the half that can regress silently.

  2. /llms.txt existed with nothing pointing at it. The link must appear on BOTH
     page frames: landing.html has its own <head> and does not extend _base.html,
     and that exact split is how the footer lost its legal links once already.

  3. The sitemap must keep listing the commercial page and every article.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from config import settings


class SeoRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="dr-seo-test-"))
        cls._saved = {k: getattr(settings, k) for k in (
            "DATA_DIR", "DB_PATH", "FREE_DIR", "DRAWINGS_DIR", "REPORTS_DIR", "OUTBOX_DIR",
            "PRODUCTS_RUNTIME_FILE", "FREE_LIMITS_RUNTIME_FILE", "REPORT_TEXTS_RUNTIME_FILE")}
        settings.DATA_DIR = cls.tmp / "data"
        settings.DB_PATH = settings.DATA_DIR / "test.sqlite3"
        settings.FREE_DIR = settings.DATA_DIR / "free"
        settings.DRAWINGS_DIR = settings.DATA_DIR / "drawings"
        settings.REPORTS_DIR = settings.DATA_DIR / "reports"
        settings.OUTBOX_DIR = settings.DATA_DIR / "outbox"
        settings.PRODUCTS_RUNTIME_FILE = settings.DATA_DIR / "products.json"
        settings.FREE_LIMITS_RUNTIME_FILE = settings.DATA_DIR / "free_limits.json"
        settings.REPORT_TEXTS_RUNTIME_FILE = settings.DATA_DIR / "report_texts.json"

        from app import create_app
        cls.app = create_app()
        cls.app.testing = True

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._saved.items():
            setattr(settings, k, v)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def client(self):
        return self.app.test_client()

    @property
    def base(self) -> str:
        return settings.PUBLIC_BASE_URL.rstrip("/")

    # --- one-hop canonicalisation ----------------------------------------

    def test_root_redirect_is_absolute_and_on_the_canonical_host(self):
        """A relative target here is what made www/ cost two hops."""
        r = self.client().get("/")
        self.assertEqual(r.status_code, 301 if len(settings.LOCALES) == 1 else 302)
        loc = r.headers["Location"]
        self.assertTrue(loc.startswith(self.base + "/"),
                        f"root redirect must be absolute on {self.base}, got {loc}")
        self.assertTrue(loc.endswith("/"), loc)

    def test_root_redirect_is_301_only_while_there_is_one_locale(self):
        """The cached-301 footgun is supposed to disarm itself, not be remembered."""
        saved = settings.LOCALES
        try:
            settings.LOCALES = ["en", "de"]
            self.assertEqual(self.client().get("/").status_code, 302)
            settings.LOCALES = ["en"]
            self.assertEqual(self.client().get("/").status_code, 301)
        finally:
            settings.LOCALES = saved

    def test_legacy_html_article_reaches_the_new_slug_in_one_redirect(self):
        """The URL Google actually has indexed for the best-performing article."""
        r = self.client().get("/blog/drawreport-blog-missing-body-parts.html")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(
            r.headers["Location"],
            f"{self.base}/{settings.DEFAULT_LOCALE}"
            "/blog/kids-drawings-missing-body-parts-meaning")

    def test_every_legacy_slug_resolves_to_a_real_article(self):
        """A mapping whose target no longer exists is a 404 dressed as a redirect."""
        from app.routes import LEGACY_BLOG_SLUGS
        c = self.client()
        for old in LEGACY_BLOG_SLUGS:
            with self.subTest(slug=old):
                r = c.get(f"/blog/{old}")
                self.assertEqual(r.status_code, 301)
                self.assertTrue(r.headers["Location"].startswith(self.base + "/"))
                self.assertEqual(c.get(r.headers["Location"][len(self.base):]).status_code,
                                 200)

    def test_legacy_blog_index_redirects_absolutely(self):
        r = self.client().get("/blog")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.headers["Location"],
                         f"{self.base}/{settings.DEFAULT_LOCALE}/blog")

    def test_unknown_legacy_slug_still_404s(self):
        """Redirecting every /blog/<anything> would turn probes into soft 404s."""
        self.assertEqual(self.client().get("/blog/no-such-article-here").status_code, 404)

    # --- /llms.txt discoverability ---------------------------------------

    def test_llms_txt_is_served(self):
        r = self.client().get("/llms.txt")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/plain", r.headers["Content-Type"])

    def test_robots_points_at_llms_txt_and_the_sitemap(self):
        body = self.client().get("/robots.txt").get_data(as_text=True)
        self.assertIn(f"Sitemap: {self.base}/sitemap.xml", body)
        self.assertIn(f"{self.base}/llms.txt", body)
        for path in ("/admin", "/cabinet", "/free"):
            self.assertIn(f"Disallow: {path}", body)

    def test_both_page_frames_link_llms_txt(self):
        """_base.html and landing.html are separate <head>s; one of them WILL be
        forgotten, and nothing on a rendered page would show it."""
        loc = settings.DEFAULT_LOCALE
        for path in (f"/{loc}/", f"/{loc}/report", f"/{loc}/blog"):
            with self.subTest(path=path):
                html = self.client().get(path).get_data(as_text=True)
                self.assertIn('href="/llms.txt"', html,
                              f"{path} has no pointer to /llms.txt")

    # --- sitemap ----------------------------------------------------------

    def test_sitemap_lists_the_commercial_page_and_every_article(self):
        from app.blog import get_posts
        xml = self.client().get("/sitemap.xml").get_data(as_text=True)
        locs = set(re.findall(r"<loc>(.*?)</loc>", xml))
        loc = settings.DEFAULT_LOCALE
        self.assertIn(f"{self.base}/{loc}/report", locs)
        for p in get_posts(loc):
            self.assertIn(f"{self.base}/{loc}/blog/{p.slug}", locs)

    def test_sitemap_lists_nothing_that_robots_disallows(self):
        """A URL in both files is a contradiction, and Search Console reports it."""
        from app.routes import SEO_DISALLOW
        xml = self.client().get("/sitemap.xml").get_data(as_text=True)
        for url in re.findall(r"<loc>(.*?)</loc>", xml):
            path = url[len(self.base):]
            for bad in SEO_DISALLOW:
                self.assertFalse(path.startswith(bad), f"{url} is disallowed in robots.txt")

    def test_sitemap_lastmod_is_a_real_date_not_today(self):
        """lastmod = today() on every URL every day is what V0.043 removed."""
        import datetime as dt
        xml = self.client().get("/sitemap.xml").get_data(as_text=True)
        stamps = set(re.findall(r"<lastmod>(.*?)</lastmod>", xml))
        self.assertTrue(stamps)
        for s in stamps:
            dt.date.fromisoformat(s)  # raises if malformed
        self.assertNotEqual(stamps, {dt.date.today().isoformat()},
                            "every lastmod is today - the stale-lastmod bug is back")


if __name__ == "__main__":
    unittest.main()
