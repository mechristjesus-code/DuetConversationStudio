#!/data/data/com.termux/files/usr/bin/bash
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"
HOST="${DUET_HOST:-127.0.0.1}"
PORT="${DUET_PORT:-8765}"
exec python3 server.py --host "$HOST" --port "$PORT"
