# API Specification — Duet Conversation Studio

## Base URL
`http://127.0.0.1:8765`

## Endpoints

### 1. `GET /api/assets`
- **Description**: Returns all registered media assets ordered by creation time.
- **Response**: JSON array of asset objects (`asset_id`, `file_path`, `duration`, `width`, `height`, `checksum`, `created_at`).

### 2. `POST /api/assets/upload`
- **Description**: Uploads a video file via multipart form-data (`video`), validates size, computes SHA-256 checksum, inspects metadata, and registers asset.
- **Response**: `{"success": true, "asset_id": "...", "file_path": "...", "duration": 0.0, "width": 0, "height": 0}`.

### 3. `GET /api/generations`
- **Description**: Returns all recorded generations (render lineage).
- **Response**: JSON array of generation records.

### 4. `POST /api/render/duet`
- **Description**: Renders a side-by-side or stacked duet video from two input assets with optional trim ranges.
- **Payload**:
  ```json
  {
    "asset1_id": "...",
    "asset2_id": "...",
    "layout": "side-by-side",
    "trim1": {"start": 0.0, "duration": 5.0},
    "trim2": {"start": 0.0, "duration": 5.0}
  }
  ```
- **Response**: `{"success": true, "generation_id": "...", "output_asset_id": "...", "output_url": "..."}`.

### 5. `GET /api/turns` & `POST /api/turns`
- **Description**: Manages conversation turns and question-answer relationships.
