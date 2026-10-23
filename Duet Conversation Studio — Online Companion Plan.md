# Duet Conversation Studio — Online Companion Plan

## Product decision

The product has two editions with one portable contract:

- **Online edition:** managed web app, persistent project records, browser-first workspace, and a visible Online badge. The first web milestone stores source metadata, hashes, recipes, generations, and render-job records. Large media upload and server rendering remain behind explicit media-runtime readiness rather than being falsely presented as complete.
- **Termux edition:** Android localhost app, offline operation, FFmpeg rendering, local SQLite, and private managed media files. It remains the authoritative offline renderer.

Both editions use the same recipe shape (`schema_version`, `layout`, `canvas`, `audio`, `inputs`) and generation concepts (`generation_uuid`, ordered input references, source hashes, render status). A portable JSON export/import bridge will be the compatibility seam.

The long-term architecture has three access points over one shared foundation: the browser web app, a separate Galaxy phone client, and the local Termux engine. They do not share source code or databases. A future synchronization layer will exchange project revisions, media transfer manifests, conflict state, interrupted transfers, and device media availability. Termux is not treated as an always-available remote server: when the phone is asleep or offline, the online edition must say that a local job is unavailable rather than pretending it is running.

Data ownership is explicit. Duet Studio owns project settings, revisions, relationships, source references, generations, and render records. Approved media storage owns original and rendered media objects. Galaxy Mind/LUNA retain their own agent memory and state. Shared action and audit records own external approvals. AI suggestions, when added, remain proposals until approved and never rewrite authoritative project history.

## Design

Three visual directions were considered: industrial timeline (0.07), soft media notebook (0.08), and **signal-console editorial (0.06)**. Choose signal-console editorial: a dark ink workspace with warm paper cards, bright cyan status signals, and an orange action accent. It reads as a serious production console without copying generic SaaS dashboards.

Core principles are provenance before polish, one decisive render action, and clear separation between online records and offline media. The layout uses a left project rail, a central stage with paired source cards, and a right lineage/status rail rather than a centered grid. Signature elements are a thin signal line, compact status chips, and numbered generation markers. Interactions use immediate validation and visible state transitions. Motion is restrained: status dots pulse only while work is processing; cards lift slightly on selection; no decorative animation competes with media controls.

Typography uses a clean system sans for interface text and a condensed monospace for IDs, hashes, and statuses. The brand essence is “a traceable conversation editor for people who need every cut to remember where it came from”; personality: precise, calm, inspectable. Voice is direct: “Build the next response without losing the chain.” and “Online records stay compatible with your offline studio.”

## Implementation

Use React, Tailwind, tRPC, Drizzle, and the managed MySQL database. Add `sources`, `generations`, and `inputRefs` tables with portable JSON fields for recipes and source-reference metadata. Add tRPC queries/mutations for source registration, generation creation, generation listing, and render-job state. Keep online render state explicit: `draft`, `queued`, `processing`, `completed`, `failed`, and `media_unavailable`. Do not claim a real MP4 exists until a managed media upload plus FFmpeg-capable render worker is connected.

The frontend is one responsive workspace with Online/Offline edition labeling, an import dropzone, source registry, compose controls, generation history, and lineage cards. It can compute SHA-256 in the browser and persist metadata through tRPC. The Termux export contract is shown in the UI and documented so a recipe JSON can move between editions. TikTok support begins as a local vertical export profile plus a credit packet: 1080×1920 H.264/AAC output, manual review, creator/video credit fields, and no automatic posting.

## Project structure

- `client/src/pages/Home.tsx`: primary workspace.
- `client/src/index.css`: signal-console editorial system.
- `server/routers.ts`: typed feature API.
- `server/db.ts`: persistence queries.
- `drizzle/schema.ts`: MySQL tables.
- `docs/`: contract notes and implementation boundary.
- `public/manus-routes.json`: route manifest.

## Out of scope for this online milestone

No Google Drive, AI analysis, email, automatic TikTok posting, model training, or changes to Galaxy Mind, LUNA, Nexus, Sunny, Atom, or Eve/Adam systems. The Termux app remains the offline renderer until a durable online media-runtime path is approved.
