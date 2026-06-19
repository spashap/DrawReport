#!/usr/bin/env bash
# deploy.sh — pull latest code, refresh deps, restart the DrawReport services.
# Run as root from this folder (after provision.sh has run once):
#     cd /var/www/drawreportDeploy && bash deploy.sh
#
# Scoped to DrawReport ONLY — never touches cosmyday-api (port 8001).
# DB schema is created/migrated idempotently on startup. .env is untouched.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run as root"; exit 1; }

APP_DIR=/var/www/DrawReport
SVC_USER=www-data
cd "$APP_DIR"

echo "== pull =="
git pull --ff-only
echo "now at $(git rev-parse --short HEAD)  (V$(cat VERSION 2>/dev/null || echo '?'))"

echo "== python deps =="
venv/bin/pip install -q -r requirements.txt 'gunicorn>=21'

echo "== data dirs / ownership =="
mkdir -p data/drawings data/reports data/outbox
chown -R "$SVC_USER:$SVC_USER" data static/img

echo "== compile translations =="
venv/bin/pybabel compile -d translations 2>/dev/null || true

echo "== restart services =="
systemctl restart drawreport-web.service drawreport-worker.service
sleep 1
echo "web:    $(systemctl is-active drawreport-web.service)"
echo "worker: $(systemctl is-active drawreport-worker.service)"
echo "deployed."
