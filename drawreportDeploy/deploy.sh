#!/usr/bin/env bash
# deploy.sh - thin wrapper. The REAL deploy script is /var/www/DrawReport/deploy.sh,
# in the application repo.
#
# Why a wrapper instead of a second copy: there used to be two full deploy scripts, one
# here and one in the repo. Two copies of the same logic drift, and the failure is silent
# - you fix a step in one, deploy through the other, and the fix simply never runs. The
# repo copy is also the one `git pull` updates as part of the deploy itself, so it is
# always the current one; this file cannot be.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run as root"; exit 1; }

APP_DEPLOY=/var/www/DrawReport/deploy.sh
[ -x "$APP_DEPLOY" ] || [ -f "$APP_DEPLOY" ] || {
  echo "ERROR: $APP_DEPLOY not found - has provision.sh run yet?"; exit 1; }

exec bash "$APP_DEPLOY"
