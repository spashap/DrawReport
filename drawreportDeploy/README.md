# DrawReport — deployment kit

Copy this whole folder to **`/var/www/drawreportDeploy`** on the server and run the
scripts from there as root. They act on the project at **`/var/www/DrawReport`** and
never touch cosmyday-api (which stays on port 8001).

| DrawReport | value |
|---|---|
| code | `/var/www/DrawReport` |
| app port | `127.0.0.1:8002` (gunicorn) |
| systemd | `drawreport-web`, `drawreport-worker` |
| nginx vhost | `drawreport.com` (+ www) → 8002 |
| TLS | Let's Encrypt (certbot, drawreport.com only) |
| DB | SQLite at `/var/www/DrawReport/data/drawreport.sqlite3` |
| venv | `/var/www/DrawReport/venv` (own, not shared) |

## Files
- `provision.sh` — one-time setup (apt deps, code, venv, systemd units, nginx).
- `deploy.sh` — routine update (git pull + deps + restart).
- `restart.sh` — restart the two services.
- `drawreport-web.service`, `drawreport-worker.service` — systemd units.
- `nginx-drawreport.conf` — the vhost.

## First-time install
```bash
# 1) DNS: point drawreport.com + www  ->  this server's IP (DNS-only, no proxy)

# 2) on the server, as root:
mkdir -p /var/www/drawreportDeploy
#    ...copy this folder's contents into /var/www/drawreportDeploy...
cd /var/www/drawreportDeploy
bash provision.sh
```
`provision.sh` pulls the repo into `/var/www/DrawReport` **without overwriting the `.env`
you already placed there**, builds the venv, installs deps + gunicorn, installs and starts
the two systemd services, and installs the nginx vhost.

```bash
# 3) issue the certificate (after DNS resolves):
certbot --nginx -d drawreport.com -d www.drawreport.com

# 4) PayPal (when going live): set the webhook URL to
#    https://drawreport.com/pay/paypal/webhook   (event PAYMENT.CAPTURE.COMPLETED)
#    and put its id in .env as PAYPAL_WEBHOOK_ID
```

## Routine updates
```bash
cd /var/www/drawreportDeploy && bash deploy.sh      # pull + deps + restart
cd /var/www/drawreportDeploy && bash restart.sh     # just restart
```

## Check the `.env` on the server  (`/var/www/DrawReport/.env`)
You copied the **dev** `.env`. Change these for production:

| Key | Dev value (copied) | Set for production |
|---|---|---|
| `PUBLIC_BASE_URL` | `http://localhost:3000` | **`https://drawreport.com`** |
| `ADMIN_PASS` | `devadmin` | **a strong, unique password** |
| `SITE_DOMAIN` | `drawreport.com` | keep |
| `LLM_PROVIDER` / `LLM_MODEL` / `LLM_FALLBACK_MODEL` | anthropic / sonnet-4-6 / haiku-4-5 | keep |
| `ANTHROPIC_API_KEY` | (already set) | keep |
| `MAIL_BACKEND` | `outbox` | `resend` once `RESEND_API_KEY` + `MAIL_FROM_EMAIL` are set (outbox is fine to start) |
| `PAYMENT_BACKEND` | `stub` | `paypal` once `PAYPAL_CLIENT_ID/SECRET/WEBHOOK_ID` are set (stub is fine to start) |
| `PAYPAL_ENV` | `sandbox` | `sandbox` first, then `live` |
| `GA_MEASUREMENT_ID` | (empty) | your `G-XXXXXXXXXX` when ready |

There is no `PORT` in prod — gunicorn binds `127.0.0.1:8002` (set in the web unit).
After editing `.env`, run `bash restart.sh`.

## Health checks
```bash
systemctl status drawreport-web drawreport-worker
journalctl -u drawreport-web -n 50 --no-pager
journalctl -u drawreport-worker -n 50 --no-pager
curl -I http://127.0.0.1:8002/            # 302 -> /en/
```

## Notes
- WeasyPrint system libs are installed by `provision.sh` (Pango/Cairo/GDK-Pixbuf).
- Logo/hero already built and committed in `static/img/`. To change later: drop new art
  in `data/Images/` and run `venv/bin/python scripts/build_hero_image.py` / `build_logos.py`.
- Optional admin geo labels: run `venv/bin/python scripts/build_geoip.py` on the server to
  build `data/geoip.db` (without it, analytics simply records no geo).
- Add a second language later: set `LOCALES=en,es` in `.env` + add the `es` catalog/content;
  no code change.
