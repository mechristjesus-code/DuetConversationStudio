# Roadmap

## Phase 0 — Read-only inspection

**Status: IMPLEMENTED and TESTED.** Audit tools, project existence, loopback port, and write intent without creating application state.

## Phase 1 — Foundation

**Status: IMPLEMENTED and TESTED.** Import two local videos, copy them into managed storage, inspect metadata with FFprobe, hash them, persist them in SQLite, verify integrity, and reopen after restart.

## Phase 2 — Working editor

**Status: PARTIALLY IMPLEMENTED.** The exact split-screen FFmpeg builder is implemented and smoke-tested. The generation API, trim UI, preview, durable render jobs, alternating playback, cancellation, and output publication remain to be added.

Acceptance requires side-by-side and alternating modes, valid clip boundaries, audio configuration, a playable MP4, progress/failure states, and preservation of earlier exports.

## Phase 3 — Durable projects and recursive duets

**Status: PLANNED.** Add persistent recipes, full lineage traversal, source moved/changed detection, restart recovery, idempotent restore, and optional Google Drive MP4 plus lineage backup.

## Phase 4 — Communication queue

**Status: PLANNED and OUT OF FOUNDATION SCOPE.** Add reviewable local message drafts and delivery states. No email provider is required for video creation.

## Phase 5 — Conversation intelligence

**Status: PLANNED.** Add transcript extraction, local search, optional offline model adapters, and reviewed datasets. Saving or searching conversations must never imply training.

## Phase 6 — External collaboration

**Status: PLANNED.** Evaluate sanctioned imports, optional sharing, synchronization, and mail adapters only after permissions and device behavior are verified.

Every phase requires a backup/recovery plan, acceptance tests, and a changelog entry before the next phase begins.
