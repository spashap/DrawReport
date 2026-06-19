# DrawReport — deployment

The full, ready-to-run deployment kit lives in **[`drawreportDeploy/`](drawreportDeploy/README.md)**.

On the server:
- Project code: **`/var/www/DrawReport`** (this repo; `.env` placed there by the owner)
- Deploy scripts: copy `drawreportDeploy/` → **`/var/www/drawreportDeploy`** and run as root

Runs in parallel with **cosmyday-api** (port 8001), fully isolated:
gunicorn on **127.0.0.1:8002**, systemd `drawreport-web` + `drawreport-worker`,
own nginx vhost for `drawreport.com`, own Let's Encrypt cert, own venv + SQLite.

## Quick start
```bash
# DNS: drawreport.com + www -> server IP (DNS-only), then on the server as root:
cd /var/www/drawreportDeploy
bash provision.sh                                   # one-time: deps, code, venv, systemd, nginx
certbot --nginx -d drawreport.com -d www.drawreport.com   # TLS once DNS resolves
```
Routine updates: `cd /var/www/drawreportDeploy && bash deploy.sh`.

See `drawreportDeploy/README.md` for the full runbook, the production `.env` checklist
(change `PUBLIC_BASE_URL` and `ADMIN_PASS`; switch `MAIL_BACKEND`/`PAYMENT_BACKEND` when ready),
and health-check commands.

> `deploy.sh` / `restart.sh` also exist in the repo root (same actions, run from
> `/var/www/DrawReport`). WeasyPrint system libs (Pango/Cairo/GDK-Pixbuf) are installed by
> `provision.sh`.
