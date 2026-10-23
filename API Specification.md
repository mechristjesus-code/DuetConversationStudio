# API Specification

All endpoints are local-only and served from `http://127.0.0.1:8765`.

## Implemented

### `GET /api/status`

Returns service health, registered source count, and FFmpeg/FFprobe availability.

### `POST /api/sources`

Accepts `multipart/form-data` with field `video`. The server copies the upload to the managed source directory, probes it, hashes it, and inserts a source record.

Success: `201` with the source record.

Errors: `400` for invalid/oversized/non-video input; `500` for unexpected server errors.

### `GET /api/sources`

Returns `{ "sources": [...] }`, newest imports first.

### `GET /api/sources/{id}`

Returns one source record.

### `POST /api/sources/{id}/verify`

Re-hashes the managed file and updates `status` to `ok`, `changed`, `missing`, or `unverified`.

### `GET /projects/sources/{managed_filename}`

Serves only files inside the managed source directory. It does not provide arbitrary filesystem access.

## Planned Phase 2 routes

```text
POST /api/generations
GET  /api/generations
GET  /api/generations/{id}
POST /api/generations/{id}/render
GET  /api/generations/{id}/render/status
```

These routes must validate trim boundaries, source IDs, recipe schema, output paths, and render state. Long renders should move to a durable job model rather than blocking the request handler.

## API rules

- Bind to loopback by default.
- Never trust browser-supplied paths.
- Use parameterized SQL.
- Restrict media reads to approved directories.
- Use explicit status and error responses.
- Never silently overwrite a successful export.
