# Roadmap — Duet Conversation Studio

## Phase 0 — Read-Only Audit & Blueprint (COMPLETE)
- Environment verified (Python 3.14.6, FFmpeg/FFprobe 9.0.2).
- Master blueprints and specs established.

## Phase 1 — Working Editor & Video Pipeline (COMPLETE)
- Backend multipart upload & metadata extraction.
- FFmpeg side-by-side & stacked rendering with mixed audio support.
- Automated test suite (`test_studio.py`) passing successfully.

## Phase 2 — Persistent History & Recursive Duets (COMPLETE)
- SQLite schema with generations, assets, and turn tracking.
- Recursive generation support (`A + B → C`, then `C + D → E`).

## Phase 3 — Conversation Intelligence (NEXT)
- Offline speech transcription and speaker turn annotations.
- Graph visualization of conversation lineages.

## Phase 4 — Knowledge Library & External Sync
- Searchable turn library and backup synchronization.
