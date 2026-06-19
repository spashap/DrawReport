#!/usr/bin/env bash
# provision.sh — one-time DrawReport setup on the shared Hetzner box, IN PARALLEL
# with cosmyday-api. Run as root from this folder:
#     cd /var/www/drawreportDeploy && bash provision.sh
#
# Never touches cosmyday-api: own dir (/var/www/DrawReport), port (8002), systemd
# units, nginx vhost, venv, SQLite, and Let's Encrypt cert (drawreport.com only).
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run as root"; exit 1; }

APP_DIR=/var/www/DrawReport
REPO=https://github.com/spashap/DrawReport.git
SVC_USER=www-data
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"   # where this script + the unit/conf files live

echo "== system deps (WeasyPrint needs Pango/Cairo/GDK-Pixbuf) =="
apt-get update
apt-get install -y python3-venv python3-pip git nginx \
  libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libffi-dev shared-mime-info fonts-dejavu-core
# gdk-pixbuf package name differs by Ubuntu version
apt-get install -y libgdk-pixbuf-2.0-0 || apt-get install -y libgdk-pixbuf2.0-0 || true
# certbot (skip silently if already present for cosmyday)
apt-get install -y certbot python3-certbot-nginx || true

echo "== code into $APP_DIR (preserves your existing .env) =="
mkdir -p "$APP_DIR"
cd "$APP_DIR"
if [ ! -d .git ]; then
  git init -q
  git remote add origin "$REPO" 2>/dev/null || git remote set-url origin "$REPO"
  git fetch origin main
  git checkout -f -B main origin/main
else
  git pull --ff-only
fi
if [ ! -f .env ]; then
  echo "WARNING: $APP_DIR/.env not found — copy your .env there before starting the services."
fi

echo "== venv + python deps =="
[ -d venv ] || python3 -m venv venv
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt 'gunicorn>=21'

echo "== data dirs + ownership =="
mkdir -p data/drawings data/reports data/outbox
chown -R "$SVC_USER:$SVC_USER" data static/img
# .env readable by the service user only
[ -f .env ] && chown root:"$SVC_USER" .env && chmod 640 .env || true

echo "== compile translations =="
venv/bin/pybabel compile -d translations 2>/dev/null || true

echo "== systemd units =="
cp "$DEPLOY_DIR/drawreport-web.service"    /etc/systemd/system/
cp "$DEPLOY_DIR/drawreport-worker.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now drawreport-web.service drawreport-worker.service

echo "== nginx vhost (drawreport.com only) =="
cp "$DEPLOY_DIR/nginx-drawreport.conf" /etc/nginx/sites-available/drawreport.com
ln -sf /etc/nginx/sites-available/drawreport.com /etc/nginx/sites-enabled/drawreport.com
nginx -t && systemctl reload nginx

echo
echo "web:    $(systemctl is-active drawreport-web.service)"
echo "worker: $(systemctl is-active drawreport-worker.service)"
echo
echo "== NEXT =="
echo "1) Point DNS: drawreport.com + www -> this server (DNS-only)."
echo "2) Issue TLS:  certbot --nginx -d drawreport.com -d www.drawreport.com"
echo "3) In PayPal, set webhook -> https://drawreport.com/pay/paypal/webhook (PAYMENT.CAPTURE.COMPLETED)."
echo "Done. cosmyday-api untouched. For updates later: bash deploy.sh"
