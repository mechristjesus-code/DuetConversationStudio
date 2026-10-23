# Shared Duet Conversation Studio Architecture

The product has one shared capability with multiple access points: the managed web app, a future Galaxy phone client, and the local Android Termux engine. The clients must not maintain conflicting project databases or independent rendering rules.

Duet Studio owns project settings, revisions, source references, recipes, generations, lineage, and render records. Approved media storage owns original and rendered media objects. Galaxy Mind and LUNA keep their own authorized memory and agent state. Shared action/audit records own approvals for consequential external actions.

The portable seam is a versioned JSON contract containing stable project/source/generation IDs, recipe JSON, ordered input references, trim and audio settings, source hashes, and render status. An input reference may point to a source or a completed parent generation; parent references carry the parent render hash and must remain acyclic. The online edition exposes a project sync manifest through tRPC and accepts either `sourceId` or `generationId` when creating a generation. The Termux edition exposes generation lineage export plus idempotent restore. The shared Python validator at `tools/validate_lineage_manifest.py` checks these rules for web and Galaxy clients. A future sync service will add revision conflict detection, interrupted-transfer recovery, and per-device media availability.

Termux is not an always-available remote server. If the phone is asleep, disconnected, or the local engine is not reachable, the online app must show `media_unavailable` or `waiting_for_connection`; it must not claim a render is processing. The Termux app remains the offline FFmpeg renderer until a separate durable media service and render worker are approved.

Galaxy Mind, LUNA, Nexus, Sunny, Atom, Eve, and Adam remain outside this milestone and are not modified.
