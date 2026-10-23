# Shared lineage contract

## Portable manifest

Use a versioned JSON object with:

- `protocolVersion`: `1`.
- `project`: stable `projectUuid`, revision, and metadata.
- `sources`: stable `sourceUuid`, local/database ID when available, original reference, SHA-256, media status, and optional managed media key.
- `generations`: stable `generationUuid`, generation number, recipe JSON, render status, render path/key when available, and render SHA-256.
- `inputRefs`: exactly two ordered references per generation. A source ref uses `refKind: "source"`, `sourceId` or `sourceUuid`, and `sourceSha256`. A recursive ref uses `refKind: "generation"`, `parentGenerationId` or `parentGenerationUuid`, and the parent `renderSha256` copied into `sourceSha256`.

A recursive ref is valid only when the parent render status is `completed`/`ok`, its render hash exists, and the graph remains acyclic. Never silently convert a generation ref into a source ref.

## Online implementation

The managed web project uses React/tRPC/Drizzle/MySQL. `server/routers.ts` exposes `protocol`, `project.current`, `sync.manifest`, `sources.list/register`, and `generations.list/create/requestRender`. Online generation creation accepts exactly one of `sourceId` or `generationId` for each input. Parent generation inputs must point to a completed record with `renderSha256`. The online milestone can persist lineage but must return `media_unavailable` when no render worker is connected.

Use `tools/validate_lineage_manifest.py` against a saved manifest or the deployed manifest URL. It checks source and parent references, hashes, completion state, cycles, and optional local media hashes.

## Termux implementation

The local server uses SQLite tables `sources`, `generations`, and `input_refs`. Its recursive input uses `generation_id`; the renderer resolves the parent `render_path`; the lineage route includes `parent_generation_id`; and `/api/restore/lineage` is duplicate-safe by generation UUID. Run:

```bash
python3 -m unittest -v tests/test_lineage_chain.py
```

The test must cover temporary media, silent-input handling, A+B→C, A+C→D, restart persistence, source hash integrity, duplicate-safe restore, and TikTok credit packet validation.

## Galaxy synchronization

A Galaxy client should treat the online manifest as the record index and media availability as a separate state. It should show `online`, `offline`, `waiting_for_connection`, and `media_unavailable` distinctly. Use stable UUIDs instead of local integer IDs when exchanging records. Resolve conflicts by revision and never overwrite a newer recipe or render record without an explicit user-approved merge.

## TikTok boundary

TikTok exports are vertical 1080×1920 H.264/AAC packets with manual review, creator/video credit fields, and rights confirmation. Credit does not establish permission. Do not enable direct posting without a separate approved TikTok developer integration, authorization flow, audit record, and final confirmation.
