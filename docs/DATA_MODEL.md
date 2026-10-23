# Data Model — Duet Conversation Studio

## Database: SQLite (`data/studio.sqlite3`)

### `assets`
Stores metadata and file references for all source and generated media.
- `asset_id` TEXT PRIMARY KEY
- `file_path` TEXT NOT NULL
- `duration` REAL
- `width` INTEGER
- `height` INTEGER
- `checksum` TEXT (SHA-256)
- `created_at` TIMESTAMP

### `segments`
Defines time-bounded clips from assets.
- `segment_id` TEXT PRIMARY KEY
- `asset_id` TEXT REFERENCES assets(asset_id)
- `start_ms` INTEGER
- `end_ms` INTEGER
- `speaker_id` TEXT

### `conversation_turns`
Records dialog and response relationships.
- `turn_id` TEXT PRIMARY KEY
- `segment_id` TEXT REFERENCES segments(segment_id)
- `transcript` TEXT
- `reply_to` TEXT
- `relationship` TEXT
- `confidence` REAL

### `generations`
Tracks the lineage, edit recipes, and outputs of compositions.
- `generation_id` TEXT PRIMARY KEY
- `parent_assets` TEXT (JSON list)
- `segments` TEXT (JSON list)
- `layout` TEXT
- `edit_recipe` TEXT (JSON recipe)
- `output_asset_id` TEXT REFERENCES assets(asset_id)
- `created_at` TIMESTAMP
