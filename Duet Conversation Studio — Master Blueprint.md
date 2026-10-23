# Duet Conversation Studio — Master Blueprint

**Version:** 0.1.0 foundation
**Runtime:** Android phone + Termux + Python standard library + FFmpeg/FFprobe + SQLite
**Network model:** offline-first; server binds to `127.0.0.1` by default

## Product boundary

The foundation imports two videos, preserves the originals, records metadata and SHA-256 identity, and prepares the Phase 2 renderer. The editor must remain useful without Google Drive, AI, email, TikTok, or any other network service.

## Architecture

```text
Android browser
    │ localhost HTTP
    ▼
Python local API ─── SQLite project history
    │
    ├── managed source files
    ├── render staging and exports
    ├── audit log
    └── FFmpeg / FFprobe subprocesses
```

The browser owns presentation and user input. The backend validates requests, manages SQLite, owns approved filesystem paths, and invokes FFmpeg. The database describes media; it does not contain video bytes.

## Storage rules

- Imported media is copied into `projects/sources/`; originals are never edited.
- Renders are written to `projects/renders/`; temporary files use `projects/staging/`.
- Database state lives in `data/studio.sqlite3`.
- Operational events live in `logs/audit.log`; contents, secrets, and credentials are excluded.
- Paths are resolved relative to the application root, not the current shell directory.

## Capability status

- **IMPLEMENTED:** Phase 0 read-only audit.
- **IMPLEMENTED:** Phase 1 source import, FFprobe metadata, SHA-256, SQLite persistence, browser dashboard, verification.
- **IMPLEMENTED AS BUILDER:** Phase 2 split-screen FFmpeg command builder, independently smoke-tested.
- **PLANNED:** Phase 2 generation API and editor controls.
- **PLANNED:** recursive lineage, backup, communication queue, AI, library, external integrations.

## Non-goals for the foundation

No AI training, cloud synchronization, email sending, TikTok scraping, APK build, or modification of Galaxy Mind, LUNA, Nexus, Sunny, Atom, Eve, or Adam.
