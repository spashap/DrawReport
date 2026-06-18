#!/usr/bin/env bash
# restart.sh - restart the DrawReport services. Run as root from the app folder:
#   cd /var/www/drawreport && ./restart.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run as root"; exit 1; }

systemctl restart drawreport-web.service drawreport-worker.service
sleep 1
echo "web:    $(systemctl is-active drawreport-web.service)"
echo "worker: $(systemctl is-active drawreport-worker.service)"
