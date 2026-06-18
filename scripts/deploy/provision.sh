#!/usr/bin/env bash
# provision.sh - one-time setup of DrawReport on the shared Hetzner box (root@5.78.181.152),
# IN PARALLEL with cosmyday-api. Run as root. Idempotent-ish; read before running.
#
# It NEVER touches cosmyday-api: its own dir (/var/www/drawreport), port (8002),
# systemd units, nginx vhost, venv, SQLite, and Let's Encrypt cert (drawreport.com only).
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run as root"; exit 1; }

APP_DIR=/var/www/drawreport
REPO=https://github.com/spashap/DrawReport.git

echo "== system deps (WeasyPrint needs Pango/Cairo/GDK-Pixbuf) =="
apt-get update
apt-get install -y python3-venv python3-pip git nginx \
  libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
  libffi-dev shared-mime-info fonts-dejavu-core
# certbot for TLS (skip if already installed for cosmyday)
apt-get install -y certbot python3-certbot-nginx || true

echo "== clone / update =="
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"
git pull --ff-only || true

echo "== venv + deps =="
[ -d venv ] || python3 -m venv venv
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt 'gunicorn>=21'

echo "== .env (fill in real secrets!) =="
[ -f .env ] || cp .env.example .env
echo "EDIT $APP_DIR/.env now: GEMINI_API_KEY, RESEND_API_KEY, PAYPAL_*, ADMIN_PASS,"
echo "GA_MEASUREMENT_ID, MAIL_BACKEND=resend, PAYMENT_BACKEND=paypal,"
echo "PUBLIC_BASE_URL=https://drawreport.com"

echo "== data dirs =="
mkdir -p data/drawings data/reports data/outbox
chown -R www-data:www-data data static/img

echo "== translations =="
venv/bin/pybabel compile -d translations 2>/dev/null || true

echo "== systemd units =="
cp scripts/deploy/drawreport-web.service /etc/systemd/system/
cp scripts/deploy/drawreport-worker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now drawreport-web.service drawreport-worker.service

echo "== nginx vhost (drawreport.com only) =="
cp scripts/deploy/nginx-drawreport.conf /etc/nginx/sites-available/drawreport.com
ln -sf /etc/nginx/sites-available/drawreport.com /etc/nginx/sites-enabled/drawreport.com
nginx -t && systemctl reload nginx

echo "== TLS (after DNS points drawreport.com -> this server) =="
echo "Run:  certbot --nginx -d drawreport.com -d www.drawreport.com"

echo
echo "web:    $(systemctl is-active drawreport-web.service)"
echo "worker: $(systemctl is-active drawreport-worker.service)"
echo "cosmyday untouched. Provision done - finish .env + certbot, then ./deploy.sh for updates."
