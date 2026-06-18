# DrawReport — deploy runbook (Hetzner, shared with cosmyday-api)

Server: **root@5.78.181.152**. DrawReport runs **in parallel, isolated** from cosmyday-api
(which is on port 8001). Nothing here touches cosmyday.

| DrawReport | value |
|---|---|
| code | `/var/www/drawreport` |
| app port | `127.0.0.1:8002` (gunicorn) |
| systemd | `drawreport-web`, `drawreport-worker` |
| nginx vhost | `drawreport.com` (+ www) |
| TLS | Let's Encrypt (certbot, drawreport.com only) |
| DB | SQLite at `/var/www/drawreport/data/drawreport.sqlite3` |
| venv | `/var/www/drawreport/venv` (own, not shared) |

## First-time setup
1. Point DNS **A records** for `drawreport.com` and `www.drawreport.com` at `5.78.181.152`
   (DNS-only — no proxy).
2. On the server as root:
   ```bash
   git clone https://github.com/spashap/DrawReport.git /var/www/drawreport
   cd /var/www/drawreport
   bash scripts/deploy/provision.sh
   ```
   This installs the WeasyPrint system libs (Pango/Cairo/GDK-Pixbuf), creates the venv,
   installs deps + gunicorn, copies the systemd units + nginx vhost, and starts the services.
3. Edit `/var/www/drawreport/.env` with real secrets:
   `GEMINI_API_KEY`, `RESEND_API_KEY`, `MAIL_BACKEND=resend`,
   `PAYPAL_CLIENT_ID`/`PAYPAL_CLIENT_SECRET`/`PAYPAL_WEBHOOK_ID`, `PAYMENT_BACKEND=paypal`,
   `PAYPAL_ENV=sandbox` (then `live`), `ADMIN_PASS`, `GA_MEASUREMENT_ID`,
   `PUBLIC_BASE_URL=https://drawreport.com`, `MAIL_FROM_EMAIL`. Then `./restart.sh`.
4. Issue the cert (after DNS resolves):
   ```bash
   certbot --nginx -d drawreport.com -d www.drawreport.com
   ```
5. In PayPal, set the webhook URL to `https://drawreport.com/pay/paypal/webhook`
   (event PAYMENT.CAPTURE.COMPLETED) and put its id in `PAYPAL_WEBHOOK_ID`.

## Routine deploys
```bash
cd /var/www/drawreport && ./deploy.sh      # git pull + deps + compile translations + restart
```
`./restart.sh` restarts just the two services. From the dev machine, `release.bat "msg"`
bumps the version, commits, and pushes.

## Notes
- WeasyPrint apt packages: `libpango-1.0-0 libpangocairo-1.0-0 libcairo2
  libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info`.
- Email: dev writes to `data/outbox/`; prod uses Resend (`MAIL_BACKEND=resend`). Verify the
  sending domain (SPF/DKIM) in Resend for `MAIL_FROM_EMAIL`.
- GeoIP (optional, for admin geo): run `scripts/build_geoip.py` ON THE SERVER to build
  `data/geoip.db`; without it analytics simply records no geo.
- Logo/hero: drop real art into `data/Images/` and run `build_logos.py` / `build_hero_image.py`
  (placeholders ship otherwise).
- Add a second language later: set `LOCALES=en,es` in `.env`, add the `es` catalog +
  per-locale prompt/content. No code change.
