# Security & Data Preservation Rules — Duet Conversation Studio

1. **Isolation**: Duet Conversation Studio is strictly isolated in `~/DuetConversationStudio`. It does not touch Galaxy Mind, LUNA, Script Library, or other workspaces.
2. **Local Binding**: The development and runtime server binds exclusively to `127.0.0.1:8765`.
3. **Immutable Originals**: Source media files are never overwritten or modified. All operations create derived assets.
4. **Path Traversal Protection**: Static file serving and media routing validate paths to prevent directory traversal outside `data/`.
5. **Secrets & Credentials**: No API keys, credentials, or secrets are stored in frontend code or Git.
6. **Error Handling**: API errors return safe JSON messages without exposing internal stack traces or absolute server paths.
