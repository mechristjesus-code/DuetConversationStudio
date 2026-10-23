# Security and Data Preservation

## Current rules

- Bind the server to `127.0.0.1`; LAN access is not enabled by default.
- Preserve imported originals; write only to managed project directories.
- Validate filenames with basename-only handling and reject path traversal.
- Use parameterized SQL for all database values.
- Keep secrets, OAuth tokens, email keys, and private content out of code, logs, and frontend files.
- Use FFmpeg argument arrays rather than shell-interpolated command strings.
- Write future renders to staging and publish only after FFprobe validation.
- Never overwrite a previous successful render.
- Keep audit logs limited to operational metadata.
- Do not change Galaxy Mind, LUNA, Nexus, Sunny, Atom, Eve, Adam, or unrelated projects.

## Phone-specific risks

Android may suspend Termux during long renders. The application must treat interrupted jobs as recoverable failures and retain prior successful outputs. `termux-wake-lock` may be used by the operator during a long render, but it is not required by the foundation and is not invoked automatically.

Shared Android storage access must be granted by the user through Termux. Browser file selection is copied into managed storage; browser paths are never trusted as server paths.

## Future external actions

Google Drive uploads, email sends, sharing, and AI network calls require explicit opt-in or approval. Local video creation must continue to work when those services are unavailable.
