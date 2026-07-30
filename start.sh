#!/bin/sh

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

mkdir -p /nowlert/logs/emails
touch /nowlert/logs/nowlert.log

cd /nowlert/src

echo
echo "[1/1] Starting Nowlert..."

exec python3 main.py
