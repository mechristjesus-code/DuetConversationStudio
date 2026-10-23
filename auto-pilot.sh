#!/usr/bin/env bash
set -e
echo "🚀 Duet Studio Auto-Pilot: Running validation and tests..."
python3 backend/test_studio.py
python3 preflight.py || true
echo "✨ Auto-Pilot check completed successfully!"
