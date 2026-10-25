#!/usr/bin/env bash
# Starts the harmless demo site (:8001) and the analyzer dashboard (:5000) together.
set -e
cd "$(dirname "$0")"
python3 demo_server.py >/dev/null 2>&1 &
DEMO=$!
trap 'kill $DEMO 2>/dev/null' EXIT
echo "Open http://127.0.0.1:5000  and click 'fake scam page' -> Analyze"
ALLOW_PRIVATE=1 python3 app.py
