#!/usr/bin/env python3
"""Validate a Duet Conversation Studio portable sync manifest.

This utility is client-neutral: use it from the web/Galaxy integration, CI,
or a restore workflow. It validates source hashes, completed parent-generation
references, and cycles without requiring the Termux SQLite database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any


def load_manifest(location: str) -> dict[str, Any]:
    if location.startswith(("http://", "https://")):
        with urllib.request.urlopen(location, timeout=30) as response:
            return json.loads(response.read())
    return json.loads(Path(location).read_text(encoding="utf-8"))


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_manifest(manifest: dict[str, Any], *, media_root: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.get("protocolVersion") != 1:
        errors.append("protocolVersion must be 1")
    project = manifest.get("project")
    if not isinstance(project, dict) or not project.get("projectUuid"):
        errors.append("project.projectUuid is required")

    sources = manifest.get("sources", [])
    generations = manifest.get("generations", [])
    if not isinstance(sources, list) or not isinstance(generations, list):
        errors.append("sources and generations must be arrays")
        return {"valid": False, "errors": errors, "warnings": warnings, "chains": []}

    source_by_id = {item.get("id"): item for item in sources if isinstance(item, dict)}
    source_by_uuid = {item.get("sourceUuid"): item for item in sources if isinstance(item, dict)}
    generation_by_id = {item.get("id"): item for item in generations if isinstance(item, dict)}
    generation_by_uuid = {item.get("generationUuid"): item for item in generations if isinstance(item, dict)}
    parents: dict[Any, list[Any]] = {item.get("id"): [] for item in generations if isinstance(item, dict)}

    for generation in generations:
        if not isinstance(generation, dict):
            errors.append("generation entries must be objects")
            continue
        generation_id = generation.get("id")
        generation_uuid = generation.get("generationUuid")
        if not generation_uuid:
            errors.append(f"generation {generation_id} has no generationUuid")
        refs = generation.get("inputRefs", [])
        if not isinstance(refs, list) or len(refs) != 2:
            errors.append(f"generation {generation_uuid or generation_id} must contain exactly two inputRefs")
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                errors.append(f"generation {generation_uuid or generation_id} has a non-object inputRef")
                continue
            kind = ref.get("refKind")
            expected_hash = ref.get("sourceSha256")
            if kind == "source":
                source = source_by_id.get(ref.get("sourceId"))
                if source is None and ref.get("sourceUuid"):
                    source = source_by_uuid.get(ref.get("sourceUuid"))
                if source is None:
                    errors.append(f"generation {generation_uuid} references missing source {ref.get('sourceId') or ref.get('sourceUuid')}")
                elif expected_hash and source.get("sha256") != expected_hash:
                    errors.append(f"generation {generation_uuid} source hash does not match source registry")
            elif kind == "generation":
                parent = generation_by_id.get(ref.get("parentGenerationId"))
                if parent is None and ref.get("parentGenerationUuid"):
                    parent = generation_by_uuid.get(ref.get("parentGenerationUuid"))
                if parent is None:
                    errors.append(f"generation {generation_uuid} references missing parent generation")
                else:
                    parent_id = parent.get("id")
                    parents.setdefault(generation_id, []).append(parent_id)
                    if parent.get("renderStatus") != "completed":
                        errors.append(f"generation {generation_uuid} parent is not completed")
                    if not parent.get("renderSha256"):
                        errors.append(f"generation {generation_uuid} parent has no renderSha256")
                    elif expected_hash and parent.get("renderSha256") != expected_hash:
                        errors.append(f"generation {generation_uuid} parent render hash does not match inputRef")
            else:
                errors.append(f"generation {generation_uuid} has unsupported refKind {kind!r}")

    visiting: set[Any] = set()
    visited: set[Any] = set()

    def visit(node: Any) -> None:
        if node in visiting:
            errors.append(f"lineage cycle detected at generation {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for parent in parents.get(node, []):
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for generation_id in generation_by_id:
        visit(generation_id)

    chains: list[list[str]] = []
    for generation in generations:
        if not isinstance(generation, dict):
            continue
        node = generation.get("id")
        chain: list[str] = [str(generation.get("generationUuid", node))]
        while parents.get(node):
            node = parents[node][0]
            parent = generation_by_id.get(node, {})
            chain.append(str(parent.get("generationUuid", node)))
        if len(chain) > 1:
            chains.append(chain)

    if media_root:
        for source in sources:
            managed_key = source.get("managedKey")
            expected = source.get("sha256")
            if not managed_key or not expected:
                continue
            candidate = media_root / managed_key
            if candidate.is_file() and digest_file(candidate) != expected:
                errors.append(f"media hash mismatch for source {source.get('sourceUuid')}")
            elif not candidate.is_file():
                warnings.append(f"media unavailable for source {source.get('sourceUuid')}")

    return {"valid": not errors, "errors": errors, "warnings": warnings, "generationCount": len(generations), "chains": chains}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="manifest JSON path or URL")
    parser.add_argument("--media-root", type=Path, help="optional local root for managed source hash checks")
    parser.add_argument("--json", action="store_true", help="print the complete JSON report")
    args = parser.parse_args()
    try:
        report = validate_manifest(load_manifest(args.manifest), media_root=args.media_root)
    except Exception as exc:  # noqa: BLE001 - CLI must return a useful failure envelope.
        report = {"valid": False, "errors": [str(exc)], "warnings": [], "chains": []}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("VALID" if report["valid"] else "INVALID")
        for message in report["errors"]:
            print(f"ERROR: {message}")
        for message in report["warnings"]:
            print(f"WARNING: {message}")
        for chain in report.get("chains", []):
            print("CHAIN: " + " <- ".join(chain))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
