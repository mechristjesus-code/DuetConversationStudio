#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
echo "Starting Duet Conversation Studio..."
python3 backend/server.py
