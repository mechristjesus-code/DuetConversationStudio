# Duet Conversation Studio — Stage 1–4 Verification

**Date:** 2026-10-22
**Scope:** actual delivered Termux scaffold and managed online companion
**Method:** isolated temporary Termux copy; online TypeScript/test/build checks; no production code changed during the verification pass

## Stage 1 — Video editing and export

**VERIFIED BY TEST for the delivered Termux scaffold.**

Commands included Python syntax compilation, FFmpeg-generated temporary source media, multipart import, recipe creation, asynchronous render, and FFprobe validation. The isolated project was `/tmp/duet-stage-audit`; temporary source media was `/tmp/duet-stage-media`.

Observed result: two videos imported, including one silent video. The renderer produced `/tmp/duet-stage-audit/projects/renders/duet_001.mp4` with H.264 video, AAC audio, 1920×1080 dimensions, and one second duration. The silent input used the `anullsrc` fallback. Original source SHA-256 values remained unchanged.

**VERIFIED FROM SOURCE.** The filter graph is implemented in `ffmpeg_builder.py`; output is staged, FFprobe-validated, hashed, and atomically published by `server.py`.

## Stage 2 — Projects and source lineage

**VERIFIED BY TEST for the delivered Termux scaffold.**

The isolated SQLite database persisted two sources, one generation, ordered input references, trim values, gain values, mute values, frozen source hashes, render path, render hash, and `render_status = ok`. The server was stopped and restarted; the generation and sources were returned afterward.

**NOT VERIFIED for recursive lineage.** The current delivered Termux implementation stores source input references. It does not yet accept a generation as a new input or expose a full ancestor/descendant lineage query.

## Stage 3 — Conversation Builder / Understanding Lab

**NOT IMPLEMENTED in the delivered Termux scaffold.** No Understanding Lab tab, conversation-turn table, transcript route, reply relationship route, or conversation-turn persistence was found in the actual project directory.

The attachment’s statements about `backend/test_studio.py`, `conversation_turns`, and Understanding Lab are therefore **NOT VERIFIED** and do not describe the delivered scaffold currently under test.

## Online companion

**VERIFIED BY TEST.** `pnpm check`, the existing six-test suite, and `pnpm build` all passed. The responsive browser workspace serves successfully, and `client/public/manus-routes.json` is valid.

**VERIFIED FROM SOURCE.** The online app persists source metadata, hashes, portable recipes, input references, generation numbers, and explicit render states through Drizzle/MySQL. Recipe JSON now embeds source UUIDs and SHA-256 values for cross-edition portability. The UI has source selection, split-screen layout intent, gain, mute, recipe creation, generation history, and Online/Termux status messaging.

**BLOCKED / EXPLICIT LIMITATION.** The online app has no connected durable media object upload and no online FFmpeg render worker. An online render request becomes `media_unavailable` with an explicit explanation. It does not claim to create an online MP4.

## Stage 4 — Web and Galaxy phone experience

**PARTIALLY VERIFIED.** The online workspace is responsive and touch-oriented at a phone viewport. The Termux edition has a localhost browser UI and offline FFmpeg engine.

**NOT TESTED.** Physical Android file selection, Android process suspension during a long render, browser reload hydration on a real phone, and a separate Galaxy phone client were not tested.

## Minimum Stage 4 work

1. Add project identity and ownership scope to online records.
2. Add recipe reload/import/export controls and a portable JSON handoff endpoint.
3. Add a durable media upload path and an approved online render worker before advertising online MP4 output.
4. Add sync manifests, revision numbers, conflict states, interrupted-transfer recovery, and device media availability.
5. Keep Termux as the offline renderer and make Online/Offline/Waiting states explicit.
6. Implement the Galaxy phone client as a separate project using the documented API; do not share databases or source files.
7. Add conversation turns only after the current editor and lineage contracts are stable.

## Temporary artifacts

- Isolated project: `/tmp/duet-stage-audit`
- Test media: `/tmp/duet-stage-media`
- First server log: `/tmp/duet-stage-server.log`
- Restart server log: `/tmp/duet-stage-server-restart.log`
- Output probe: `/tmp/duet-stage-output.json`

These artifacts were created only for verification and were not uploaded to any external service.
