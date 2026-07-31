#!/bin/sh

set -eu

APP_VERSION=$(python3 - <<'PY'
import sys
sys.path.insert(0, "/nowlert/src")
from version import VERSION
print(VERSION)
PY
)

echo "========================================="
echo " Nowlert ${APP_VERSION}"
echo " Infrastructure Notification Engine"
echo "========================================="

/nowlert/bootstrap-config.sh

mkdir -p /nowlert/logs/emails
mkdir -p /nowlert/state /nowlert/external-backups
touch /nowlert/logs/nowlert.log

cd /nowlert/src

echo
echo "[1/1] Starting Nowlert..."

exec python3 main.py
