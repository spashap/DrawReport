"""Announce changed URLs to IndexNow (Bing, Yandex, Seznam - Google does not take part).

    venv\\Scripts\\python.exe scripts\\indexnow_submit.py /en/blog/my-new-post
    venv\\Scripts\\python.exe scripts\\indexnow_submit.py --sitemap        # everything

Paths may be given as a full URL or as a path; either way they are resolved against
PUBLIC_BASE_URL, because IndexNow rejects a list whose host does not match the key
file's host.

Manual on purpose. IndexNow is for pages that CHANGED: re-announcing the whole site
on every deploy is the behaviour that gets a host rate-limited or ignored, which
costs exactly the fast indexing it was added for. --sitemap exists for the first run
and for a genuine site-wide rewrite, not for routine use.

Console output is ASCII-only (spec law: these scripts run in cp1251/cp866 consoles).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402

ENDPOINT = "https://api.indexnow.org/indexnow"
# One submission may carry at most 10000 URLs; we are nowhere near that, but a
# batch limit keeps a future programmatic caller honest.
MAX_URLS = 10000


def _sitemap_urls() -> list[str]:
    """Read our own sitemap route rather than re-deriving the URL list, so the two
    can never disagree about what is indexable."""
    from app import create_app
    app = create_app()
    with app.test_client() as c:
        xml = c.get("/sitemap.xml").get_data(as_text=True)
    return re.findall(r"<loc>(.*?)</loc>", xml)


def main(argv: list[str]) -> int:
    key = settings.INDEXNOW_KEY
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    host = urllib.parse.urlparse(base).netloc

    if not key:
        print("ERROR: INDEXNOW_KEY is not set in .env - nothing submitted.")
        return 1
    if "localhost" in host or "127.0.0.1" in host:
        print(f"ERROR: PUBLIC_BASE_URL is {base} - IndexNow needs the public host.")
        return 1

    args = argv[1:]
    if not args:
        print(__doc__.strip().splitlines()[0])
        print("Usage: indexnow_submit.py <path|url> [...]  |  --sitemap")
        return 2

    urls = _sitemap_urls() if args[0] == "--sitemap" else [
        a if a.startswith("http") else f"{base}/{a.lstrip('/')}" for a in args]
    urls = [u for u in urls if urllib.parse.urlparse(u).netloc == host][:MAX_URLS]
    if not urls:
        print(f"ERROR: no URLs on host {host} to submit.")
        return 1

    payload = json.dumps({
        "host": host,
        "key": key,
        "keyLocation": f"{base}/{key}.txt",
        "urlList": urls,
    }).encode("utf-8")

    print(f"Submitting {len(urls)} URL(s) to IndexNow as {host}:")
    for u in urls:
        print(f"  {u}")

    req = urllib.request.Request(ENDPOINT, data=payload,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.status
            body = resp.read().decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode("utf-8", "replace").strip()
    except urllib.error.URLError as e:
        print(f"FAILED: could not reach IndexNow ({e.reason})")
        return 1

    # 200 accepted, 202 accepted but the key is still being verified. 403 means the
    # key file did not answer at keyLocation - check that /<key>.txt is live first.
    if code in (200, 202):
        print(f"OK ({code}){' - key pending verification' if code == 202 else ''}")
        return 0
    print(f"FAILED ({code}): {body[:400]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
