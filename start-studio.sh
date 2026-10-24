#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
echo "Starting Duet Conversation Studio..."

# Open browser automatically in background after server starts
(
  sleep 1
  if command -v termux-open-url >/dev/null 2>&1; then
    termux-open-url "http://127.0.0.1:8765"
  else
    python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8765')" 2>/dev/null || true
  fi
) &

python3 backend/server.py
