# Duet Conversation Studio

Local-first Phase 0–1 scaffold for an Android phone running Termux. The core
editor is offline: it uses only Python’s standard library, FFmpeg/FFprobe, and
SQLite. Google Drive and AI are not required for importing, verifying, or
rendering local media.

## Phone-first Termux setup

Copy this directory into Termux, preferably under `$HOME` (the default is
`/data/data/com.termux/files/home`). No pip package or network connection is
needed:

```bash
cd ~/DuetConversationStudio
bash termux-setup.sh
bash start.sh
```

Open `http://127.0.0.1:8765/` in the phone’s browser. Keep the Termux session
running while the server is in use. Stop it with `bash stop.sh` or `Ctrl-C`.

For files in shared Android storage, run `termux-setup-storage` once in
Termux, then use the browser’s file picker. The app copies selected files into
the project’s private `projects/sources/` directory, so rendering remains
available offline even if the original shared-storage path later changes.

The server binds to `127.0.0.1` by default and is not exposed on Wi-Fi. To use
a different local port without editing code:

```bash
DUET_PORT=8876 bash start.sh
```

## Phase 0: read-only audit

From this directory:

```bash
python3 preflight.py --pretty
```

The script only inspects tool availability, project existence, and port 8765. It reports `writes_performed: false` and does not initialize the database or server. Run it before Phase 1 if you want a read-only preflight.

## Phase 1: start the foundation server

```bash
python3 server.py
```

Open `http://127.0.0.1:8765/`. Imports are copied into `projects/sources/`; originals are not modified. The server stores FFprobe metadata and a SHA-256 hash in `data/studio.sqlite3`.

API:

```text
GET  /api/status
POST /api/sources              multipart field: video
GET  /api/sources
GET  /api/sources/{id}
POST /api/sources/{id}/verify
POST /api/generations
GET  /api/generations
GET  /api/generations/{id}
POST /api/generations/{id}/render
GET  /api/generations/{id}/render/status
GET  /api/generations/{id}/lineage
POST /api/restore/lineage
POST /api/generations/{id}/export/tiktok
```

## Exact Phase 2 FFmpeg graph

`ffmpeg_builder.py` builds argv safely (no shell string interpolation). For two inputs, each branch is:

```text
[0:v]trim=start=S:end=E,setpts=PTS-STARTPTS,
  scale=960:1080:force_original_aspect_ratio=decrease,
  pad=960:1080:(ow-iw)/2:(oh-ih)/2:color=black,
  fps=30,setsar=1[v0]

[0:a]atrim=start=S:end=E,setpts=PTS-STARTPTS,
  aresample=async=1:first_pts=0,
  adelay=OFFSET|OFFSET,volume=GAIN,aresample=48000[a0]
```

The same branches are created for input 1. They are combined as:

```text
[v0][v1]hstack=inputs=2:shortest=0[vout];
[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[aout]
```

The complete command shape is:

```bash
ffmpeg -hide_banner -y \
  -i SOURCE_A -i SOURCE_B \
  -filter_complex 'VIDEO_AND_AUDIO_GRAPH' \
  -map '[vout]' -map '[aout]' \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -movflags +faststart -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -shortest OUTPUT.mp4
```

The builder validates two inputs, nonnegative trim values, valid trim ranges, canvas dimensions, and file existence. It supports silent inputs by generating a synchronized silent audio branch.

## Phase 2 renderer

Phase 2 now includes the generation API and asynchronous renderer. Create a generation with JSON shaped like:

```json
{
  "inputs": [
    {"source_id": 1, "trim_start_ms": 0, "trim_end_ms": 12000, "gain": 1.0, "muted": false},
    {"source_id": 2, "trim_start_ms": 500, "trim_end_ms": 12500, "gain": 0.8, "muted": false}
  ]
}
```

`POST /api/generations` saves the recipe and input references. `POST /api/generations/{id}/render` returns `202` and runs FFmpeg in a background thread. Poll `/api/generations/{id}/render/status` until the state is `ok` or `failed`. The renderer writes a unique staging file, validates it with FFprobe, hashes it, and atomically publishes `projects/renders/duet_NNN.mp4`. A previous successful output is never used as a partial render target, and completed generations cannot be silently re-rendered over; create a new generation for a changed recipe.

Inputs without an audio stream receive an `anullsrc` branch, so silent phone videos can still be composed and mixed. Positive sync offsets delay an input’s audio; negative offsets trim leading audio. The browser dashboard now supports importing sources, choosing two sources, setting trims/gain/mute, creating a generation, starting a render, polling status, and opening the result.

## Cross-edition handoff

`GET /api/generations/{id}/lineage` exports a portable JSON record containing the generation UUID, recipe, ordered input references, source hashes, render status, and analysis placeholder. `POST /api/restore/lineage` restores the record only when both referenced source hashes already exist locally; importing the same generation UUID twice is idempotent and returns a duplicate response instead of creating a second generation. This is the first sync seam for the online companion and future Galaxy client.

Generation inputs may reference either `source_id` or a completed `generation_id`. A parent-generation input uses the parent MP4 as the next renderer input, stores `parent_generation_id` in `input_refs`, and is included in the lineage export. This supports recursive chains such as A+B→C, then C+B→D without modifying the earlier renders.

## Automated validation

Run the dependency-free integration test with `python3 -m unittest -v tests/test_lineage_chain.py`. It creates temporary media and an isolated project, validates A+B→C and A+C→D rendering, checks parent lineage and source hashes, restarts the server, verifies persistence, checks duplicate-safe lineage restore, and validates a manual-review TikTok credit packet. Temporary test projects are removed automatically.

### TikTok-safe export

`POST /api/generations/{id}/export/tiktok` creates a 1080×1920, 9:16 H.264/AAC MP4 plus a `.tiktok.json` credit packet. The request must include `rights_confirmed: true` and may include a caption plus up to three `{creator_username, video_url}` credit entries. The packet preserves source hashes, prints a caption credit line, and reminds the publisher to use TikTok's built-in Mention → Videos credit control. The endpoint is manual-review only; it never logs into TikTok, auto-posts, or bypasses creator permissions.

## Phase 1 limitations

No trimming, composition, rendering, recursive generations, Google Drive, AI, or Android share target is implemented in this phase.

## Project documentation

The evolving architecture is documented in [`docs/MASTER_BLUEPRINT.md`](docs/MASTER_BLUEPRINT.md), with the current file map, API contract, data model, security rules, roadmap, and changelog alongside it. Each document distinguishes implemented, tested, planned, and limited behavior.
