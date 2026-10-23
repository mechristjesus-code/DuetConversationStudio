# Duet Conversation Studio — Verification and Stage 4 Preflight

**Date:** 2026-10-22

## Verified

The delivered Termux scaffold passed Python syntax compilation and an isolated end-to-end test using temporary media. It imported an audio video and a silent video, rendered a real 1920×1080 H.264/AAC MP4, verified the output with FFprobe, and kept both original source SHA-256 hashes unchanged. The temporary SQLite database preserved sources, ordered input references, trim values, gain values, render path, render hash, and successful render status across a server restart. A follow-up test created a second generation using source 1 plus completed generation 1, rendered `duet_002.mp4`, and confirmed `parent_generation_id` in the exported lineage.

The new lineage handoff also passed in the isolated project. `GET /api/generations/{id}/lineage` returned a portable JSON record, and restoring the same generation UUID returned `duplicate: true` without creating a second generation.

The reusable dependency-free test `python3 -m unittest -v tests/test_lineage_chain.py` now automates this coverage. It creates temporary media, validates A+B→C and A+C→D, checks parent lineage and source hashes, restarts the server, verifies persistence, checks duplicate-safe restore, and validates the TikTok credit packet. The test passed with `OK`.

The TikTok export profile passed an isolated real render. `POST /api/generations/{id}/export/tiktok` produced a 1080×1920 H.264/AAC MP4 and a `.tiktok.json` credit packet containing the generation UUID, source hashes, creator/video credit, caption credit line, rights acknowledgment, and `manual_review_only` status. No external TikTok request was made.

The online companion passed `pnpm check`, six existing tests, and `pnpm build`. Its managed schema now includes project UUID and revision records, and its sync manifest includes project, source, generation, recipe, input-reference, hash, and render-state data.

## Not verified or still open

The Termux scaffold does not currently contain the Understanding Lab, transcript routes, or conversation-turn tables described in the attachment. Those claims remain unverified for this delivered codebase. Recursive parent-generation rendering is now implemented and verified for the A+B→C then source+C→D pattern.

The online edition still does not produce an online MP4. Durable media upload and an online FFmpeg render worker are not connected. Physical Android testing, browser reload hydration on a phone, and a separate Galaxy client were not performed.

The TikTok profile does not grant permission, guarantee credit, guarantee Creator Rewards eligibility, or automatically post. The user must own or have lawful permission to use the sources, review the credit packet, and post manually through TikTok. TikTok’s creator/video credit controls and Duet permissions remain authoritative.

## Temporary test artifacts

The isolated test project was `/tmp/duet-stage-audit`. Test media was `/tmp/duet-stage-media`. The FFprobe output was `/tmp/duet-stage-output.json`. The TikTok credit packet was generated at `/tmp/duet-stage-audit/projects/renders/duet_001.tiktok.json`. None of these files were uploaded externally.

## Next recommended sequence

First add project UUID and ownership scope to the Termux database so both editions share a complete project identity. Then add recipe reload/import/export UI, followed by sync revision conflict handling. Only after that should an online durable media worker and a separate Galaxy phone client be added.
