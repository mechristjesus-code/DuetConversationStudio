#!/data/data/com.termux/files/usr/bin/bash
set -eu
PORT="${DUET_PORT:-8765}"
if command -v pkill >/dev/null 2>&1; then
  pkill -f "server.py --.*--port ${PORT}" 2>/dev/null || true
fi
printf 'Stopped Duet Conversation Studio processes using port %s (if running).\n' "$PORT"
