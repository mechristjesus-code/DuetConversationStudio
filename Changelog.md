# Changelog

## 0.1.0 — Foundation

### Implemented

- Added read-only `preflight.py`.
- Added loopback Python HTTP server.
- Added SQLite schema for sources, generations, and input references.
- Added copy-on-import behavior.
- Added FFprobe metadata extraction.
- Added SHA-256 hashing and source verification.
- Added phone-friendly browser dashboard.
- Added Termux start, stop, and offline setup-check scripts.
- Added exact Phase 2 split-screen FFmpeg command builder.
- Added Phase 2 generation creation and asynchronous render-status API.
- Added atomic staging-to-render publication and successful-output protection.
- Added phone compose UI with trim, gain, mute, and render polling controls.
- Added silent-input handling through `anullsrc`.
- Added offline-first architecture and safety documentation.

### Tested

- Python syntax compilation passed.
- Local `/api/status` responded successfully.
- SQLite schema initialized successfully through Python’s built-in `sqlite3` module.
- Two generated MP4 test sources imported successfully.
- Imported source metadata and SHA-256 hashes were recorded.
- The Phase 2 builder produced a playable H.264/AAC split-screen MP4.
- The complete Phase 2 API produced a playable 1920×1080 H.264/AAC MP4 from one audio source and one silent source.
- Temporary smoke-test media and database state were removed after testing.

### Known limitations

The current sandbox did not have the `sqlite3` command-line executable, so the preflight audit reports that dependency as missing even though Python SQLite is available. Phase 2 rendering is currently a tested builder, not yet a complete generation endpoint or editor workflow. Silent-video fallback, alternating playback, durable render queues, cancellation, lineage restore, and Drive backup remain planned.

### Documentation addition

Added `MASTER_BLUEPRINT.md`, `FILE_MAP.md`, `API_SPEC.md`, `DATA_MODEL.md`, `SECURITY.md`, and `ROADMAP.md`, with implemented, tested, planned, and limited features explicitly labeled.

## 0.2.0 — Recursive handoff and TikTok-safe export

### Implemented

- Added portable lineage export and idempotent restore endpoints.
- Added completed-generation inputs so A+B→C can feed C into the next duet.
- Added parent-generation references to lineage JSON and render resolution.
- Added a manual-review TikTok profile producing 1080×1920 H.264/AAC MP4 plus a credit packet.
- Added a dashboard action for TikTok export with rights confirmation, creator handle, source URL, and caption prompts.
- Added `tests/test_lineage_chain.py`, a dependency-free temporary-project integration test for recursive lineage, restart persistence, restore idempotency, source integrity, and TikTok packet validation.

### Tested

- Recursive A+B→C then source+C→D render passed with parent lineage preserved.
- TikTok export produced a valid vertical MP4 and a validated `.tiktok.json` credit packet.
- No external TikTok request or automatic post was performed.
- The automated recursive test passed with `Ran 1 test ... OK`.
