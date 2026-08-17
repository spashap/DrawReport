#!/usr/bin/env bash
# deploy.sh - pull latest code, refresh deps, restart the DrawReport services.
# Run as root from the app folder:  cd /var/www/DrawReport && ./deploy.sh
#
# Scoped to drawreport ONLY - never touches the co-tenant cosmyday-api (port 8001).
# DB schema is created/migrated idempotently on startup. Secrets live in .env (untouched).
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run as root"; exit 1; }

APP_DIR=/var/www/DrawReport
SVC_USER=www-data
cd "$APP_DIR"

# SELF-UPDATE GUARD. This script lives in the repo it pulls, and bash reads a script
# INCREMENTALLY as it runs - so `git pull` rewriting this file mid-execution leaves bash
# running a mix of the old and new versions from whatever byte offset it had reached.
# That is not theoretical: the first deploy after the free-worker unit was added ran the
# OLD script end to end, so the unit was never installed and data/free was never created,
# while the deploy reported success.
#
# The fix: pull, then immediately re-exec. `exec` replaces the process and reads the new
# file from byte zero, so every step after the pull runs entirely from the new version.
# The stage variable stops it looping.
if [ "${DR_DEPLOY_STAGE:-1}" = "1" ]; then
  echo "== pull =="
  git pull --ff-only
  echo "now at $(git rev-parse --short HEAD)  (V$(cat VERSION 2>/dev/null || echo '?'))"
  DR_DEPLOY_STAGE=2 exec bash "$0" "$@"
fi

echo "== python deps =="
venv/bin/pip install -q -r requirements.txt
venv/bin/pip install -q 'gunicorn>=21'

echo "== data dirs / ownership =="
# data/free holds uploaded free-reading drawings; without it the first upload fails on a
# missing directory owned by root.
mkdir -p data/drawings data/reports data/outbox data/free
chown -R "$SVC_USER:$SVC_USER" data
[ -d static/img ] && chown -R "$SVC_USER:$SVC_USER" static/img || true

echo "== compile translations =="
venv/bin/pybabel compile -d translations 2>/dev/null || true

# Units are installed HERE, not only in provision.sh: a unit added after the box was
# first provisioned would otherwise never appear, and the feature it runs would sit in a
# queue forever with nothing to say why. Idempotent - only copies when the file differs.
echo "== systemd units =="
UNITS_CHANGED=0
for u in drawreport-web drawreport-worker drawreport-free; do
  SRC="$APP_DIR/drawreportDeploy/$u.service"
  DST="/etc/systemd/system/$u.service"
  if [ -f "$SRC" ] && ! cmp -s "$SRC" "$DST"; then
    cp "$SRC" "$DST"
    echo "  installed/updated $u.service"
    UNITS_CHANGED=1
  fi
done
if [ "$UNITS_CHANGED" = "1" ]; then
  systemctl daemon-reload
fi
systemctl enable --quiet drawreport-web.service drawreport-worker.service drawreport-free.service

echo "== restart services =="
systemctl restart drawreport-web.service drawreport-worker.service drawreport-free.service
sleep 2
for u in drawreport-web drawreport-worker drawreport-free; do
  printf '  %-20s %s\n' "$u:" "$(systemctl is-active $u.service)"
done

# A unit that is "active" can still be crash-looping. Fail loudly rather than reporting
# a green deploy that is quietly restarting every five seconds.
FAILED=0
for u in drawreport-web drawreport-worker drawreport-free; do
  if [ "$(systemctl is-active $u.service)" != "active" ]; then
    echo "ERROR: $u is not active - last log lines:"
    journalctl -u "$u.service" -n 15 --no-pager || true
    FAILED=1
  fi
done
[ "$FAILED" = "0" ] || { echo "DEPLOY FAILED"; exit 1; }

echo "deployed."
