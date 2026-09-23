#!/bin/bash
# outlook-daily-digest daily entry point (used by launchd and manual runs).
# Locate a usable python3 (framework build first, to match the manual-run environment).
PY=""
for p in /Library/Frameworks/Python.framework/Versions/*/bin/python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$p" ]; then PY="$p"; break; fi
done
if [ -z "$PY" ]; then
    echo "$(date '+%F %T') [ERROR] python3 not found" >> "$(dirname "$0")/logs/launchd.log"
    exit 1
fi
cd "$(dirname "$0")" || exit 1
exec "$PY" main.py "$@"
