# Changelog — Duet Conversation Studio

## [0.1.0] - 2026-10-22
### Added
- Complete standalone project structure in `~/DuetConversationStudio`.
- Python HTTP backend (`server.py`) bound to `127.0.0.1:8765`.
- SQLite database initialization (`database.py`) with tables for assets, segments, conversation turns, and generations.
- Video processing module (`video_processor.py`) using FFmpeg/FFprobe for metadata extraction, checksum computation, trimming, and duet rendering with robust audio stream fallback.
- PWA frontend shell (`index.html`, `app.js`, `style.css`).
- Comprehensive automated test suite (`backend/test_studio.py`) validating syntax, DB integrity, metadata extraction, audio mixing, render failure isolation, and recursive A+B → C → D lineage workflows.
- Complete documentation suite under `docs/`.
