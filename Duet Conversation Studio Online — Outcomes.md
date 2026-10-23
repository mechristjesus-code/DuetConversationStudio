# Duet Conversation Studio Online — Outcomes

## Shared contract and edition boundary

- [ ] The web app and Termux edition use the same project IDs, asset/source IDs, recipe schema, generation IDs, input references, hashes, and render status vocabulary. Source UUID/hash and recipe/lineage handoff are implemented; shared project UUIDs remain open.
- [ ] The UI clearly identifies Online versus Offline/Termux operation and states that the Termux installation is not an always-available remote server when the phone is asleep or offline.
- [ ] The web and future Galaxy phone app communicate through documented APIs rather than sharing databases or application source files.

## Online source registry

- [ ] Importing a browser video validates the file, computes a content hash, records metadata and permissions/provenance, and never edits the original browser file.
- [ ] Source records persist in the managed project database and distinguish metadata availability from media-object availability.

## Recipe and render records

- [ ] A user can save and reload a versioned two-input side-by-side recipe with trim and audio settings.
- [ ] Generation records retain ordered input references, source hashes, recipe JSON, render record, and lineage links. Source-level lineage is implemented; recursive parent-generation links remain open.
- [ ] Render state is explicit: draft, queued, processing, completed, failed, or media_unavailable.
- [ ] The web app never claims a playable MP4 exists until an actual managed media-runtime path has completed and validated it.

## Phone-oriented workspace

- [ ] The workspace is responsive and touch-friendly, with source assignment, layout configuration, audio mixing controls, status visibility, and playable output access.
- [ ] The UI explains which work is online, local on Termux, waiting for a connection, or unavailable.

## Sync foundation

- [x] Online projects have a stable project UUID and revision record.
- [x] Online sync exposes a portable manifest containing the project, sources, recipes, input references, hashes, and render states.
- [x] Termux exports generation lineage JSON and restores it idempotently when referenced source hashes are available locally.
- [ ] Add revision conflict detection, interrupted-transfer recovery, and per-device media availability.

## Explicit exclusions

- [ ] Do not modify Galaxy Mind, LUNA, Nexus, Sunny, Atom, Eve, or Adam.
- [ ] Do not add Google Drive, AI analysis, email, TikTok imports, or model training to this milestone.
