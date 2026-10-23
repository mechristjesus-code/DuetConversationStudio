# Data Model

## Implemented tables

### `sources`

One row per managed imported video. Identity is `source_uuid` plus `sha256`; the managed path is a location, not identity. Metadata includes size, duration, dimensions, codecs, audio presence, verification status, and timestamps.

### `generations`

Reserved foundation table for immutable rendered records. It stores a UUID, monotonic generation number, recipe JSON, render status, output path/hash, timestamps, and error text.

### `input_refs`

Reserved relationship table for generation inputs. It supports `source` and `generation` references, ordinal order, trim points, sync offset, gain, mute state, and the source hash captured when the reference was created.

### `schema_meta`

Stores the current schema version for future migrations.

## Planned tables

- `backups`: separate MP4 and lineage Drive IDs, status, retries, timestamps, and errors.
- `analyses`: transcript, speaker turns, topics, Q/A links, summary, and analysis status.
- `library_items`: reviewed/approved generation entries, tags, notes, and attribution.

## Integrity rules

- SQLite foreign keys are enabled on every connection.
- Generation creation and restore must be transactional.
- A changed recipe creates a new generation; it does not mutate a completed generation.
- Restore matches sources by SHA-256 and generations by UUID before inserting anything.
- Re-importing the same lineage JSON is idempotent.
- Missing media is reported; it is never silently replaced.

## Conceptual lineage

```text
source A ─┐
          ├─ generation C ─┐
source B ─┘                ├─ generation D
source E ──────────────────┘
```

D must retain direct input references to C and E, while lineage traversal resolves C back to A and B.
