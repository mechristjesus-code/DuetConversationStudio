#!/data/data/com.termux/files/usr/bin/bash
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
printf '%s\n' 'Duet Conversation Studio offline Termux setup check'
fail=0
for command in python3 ffmpeg ffprobe sqlite3; do
  if command -v "$command" >/dev/null 2>&1; then
    printf 'OK   %-8s %s\n' "$command" "$(command -v "$command")"
  else
    printf 'MISS %-8s install it in Termux before continuing\n' "$command"
    fail=1
  fi
done
if [ ! -r "$ROOT/server.py" ]; then
  echo "MISS server.py is not readable"
  fail=1
fi
if [ "$fail" -ne 0 ]; then
  echo 'No network action was attempted. Install missing tools manually, then rerun.'
  exit 1
fi
chmod +x "$ROOT/start.sh" "$ROOT/stop.sh" "$ROOT/termux-setup.sh"
printf '\nReady. Start with:\n  %s/start.sh\n' "$ROOT"
printf 'Open on the phone at: http://127.0.0.1:${DUET_PORT:-8765}/\n'
