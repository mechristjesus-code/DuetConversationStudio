# File Map

This map describes the current repository, not an unverified pre-existing project.

| Path | Status | Responsibility |
|---|---|---|
| `preflight.py` | IMPLEMENTED | Read-only dependency and port audit |
| `server.py` | IMPLEMENTED | Local HTTP API, static serving, import, probe, hash, verify |
| `ffmpeg_builder.py` | IMPLEMENTED | Phase 2 two-input filter graph and argv builder |
| `public/index.html` | IMPLEMENTED | Phone-friendly source dashboard |
| `public/app.js` | IMPLEMENTED | Import, list, refresh, integrity verification |
| `public/styles.css` | IMPLEMENTED | Responsive dashboard styling |
| `start.sh` | IMPLEMENTED | Termux localhost launcher |
| `stop.sh` | IMPLEMENTED | Scoped local stop helper |
| `termux-setup.sh` | IMPLEMENTED | Offline dependency and file check; does not install |
| `data/` | RUNTIME | SQLite database, created on first start |
| `projects/sources/` | RUNTIME | Managed source copies |
| `projects/renders/` | RUNTIME | Validated generated exports |
| `projects/staging/` | RUNTIME | Temporary upload/render files |
| `logs/` | RUNTIME | Audit log |
| `docs/` | IMPLEMENTED | Blueprint and operational documentation |

Future modules such as `database.py`, `video_processor.py`, PWA service worker,
queue service, communication adapters, and AI adapters should be added only when
the corresponding feature is approved and tested.
