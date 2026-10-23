# File Map — Duet Conversation Studio

## Root Structure
- `start-studio.sh`: Startup script.
- `backend/`: Python server, database, and video processing.
- `frontend/`: Studio user interface (HTML, CSS, JS).
- `data/`: SQLite database and media files (uploads, outputs).
- `logs/`: Application logs and diagnostics.
- `tests/`: Automated test suite.
- `docs/`: Documentation suite.

## Key Files
- `backend/server.py`: HTTP server and REST endpoints (`/api/assets`, `/api/render/duet`, `/api/turns`, etc.).
- `backend/database.py`: SQLite schema and connection management (`assets`, `segments`, `conversation_turns`, `generations`).
- `backend/video_processor.py`: FFprobe metadata extraction, SHA-256 checksums, and FFmpeg duet rendering with mixed audio support.
- `frontend/index.html`: Studio UI shell and tab navigation.
- `frontend/app.js`: Frontend state management and API integration.
- `frontend/style.css`: Responsive mobile styling.
- `backend/test_studio.py`: Comprehensive test suite verifying recursive workflows.
