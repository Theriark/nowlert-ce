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

if [ "${NOWLERT_DDTRACE_ENABLED:-false}" = "true" ]; then
    if ! command -v ddtrace-run >/dev/null 2>&1; then
        echo "ERROR: NOWLERT_DDTRACE_ENABLED=true but ddtrace-run is unavailable." >&2
        exit 1
    fi

    echo
    echo "[1/1] Starting Nowlert with Datadog runtime instrumentation..."
    exec ddtrace-run python3 main.py
fi

echo
echo "[1/1] Starting Nowlert..."

exec python3 main.py
