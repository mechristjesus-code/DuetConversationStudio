# Master Blueprint — Duet Conversation Studio

## 1. Vision & Core Philosophy
Duet Conversation Studio is an offline-first Android/Termux application for recording, composing, and tracing recursive video conversations.

- **Lineage First (`ONE != ALL`)**: Every generated video is a permanent record with a unique generation ID, parent generations, source file hashes, and reproducible edit recipes.
- **Immutable Originals**: Source media is never modified.
- **Recursive Branching**: Rendered outputs become inputs for future conversations.
- **Local-First Runtime**: Runs on Python 3, SQLite, and FFmpeg/FFprobe on `127.0.0.1:8765`.

## 2. System Architecture
- **Studio Interface**: HTML/CSS/JS PWA running in browser/WebView.
- **Local API**: Python `http.server` backend.
- **Media Engine**: FFmpeg / FFprobe wrapper handling trimming, layouts, and audio mixing.
- **Storage**: SQLite database (`studio.sqlite3`) + filesystem media storage (`data/uploads/`, `data/outputs/`).
