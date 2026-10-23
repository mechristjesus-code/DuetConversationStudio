#!/usr/bin/env python3
from __future__ import annotations

import argparse
import cgi
import hashlib
import json
import mimetypes
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ffmpeg_builder import InputSpec, build_split_screen_command, build_tiktok_duet_command

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "studio.sqlite3"
SOURCE_DIR = ROOT / "projects" / "sources"
RENDER_DIR = ROOT / "projects" / "renders"
STAGING_DIR = ROOT / "projects" / "staging"
PUBLIC_DIR = ROOT / "public"
LOG_PATH = ROOT / "logs" / "audit.log"
HOST = "127.0.0.1"
PORT = 8765
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
RENDER_THREADS: dict[int, threading.Thread] = {}
RENDER_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_layout() -> None:
    for path in (ROOT / "data", SOURCE_DIR, RENDER_DIR, STAGING_DIR,
                 ROOT / "logs", ROOT / "backups"):
        path.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch(exist_ok=True)


def audit(event: str, **fields: object) -> None:
    safe = {"time": utc_now(), "event": event, **fields}
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe, sort_keys=True) + "\n")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY,
            source_uuid TEXT NOT NULL UNIQUE,
            original_name TEXT NOT NULL,
            managed_path TEXT NOT NULL UNIQUE,
            original_path TEXT,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            duration_ms INTEGER,
            width INTEGER,
            height INTEGER,
            has_audio INTEGER NOT NULL DEFAULT 0,
            video_codec TEXT,
            audio_codec TEXT,
            status TEXT NOT NULL DEFAULT 'ok',
            imported_at TEXT NOT NULL,
            last_verified_at TEXT,
            last_error TEXT
        );
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY,
            generation_uuid TEXT NOT NULL UNIQUE,
            generation_number INTEGER NOT NULL UNIQUE,
            recipe_json TEXT NOT NULL,
            render_status TEXT NOT NULL DEFAULT 'draft',
            render_path TEXT,
            render_sha256 TEXT,
            created_at TEXT NOT NULL,
            rendered_at TEXT,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS input_refs (
            id INTEGER PRIMARY KEY,
            generation_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            ref_kind TEXT NOT NULL CHECK(ref_kind IN ('source','generation')),
            source_id INTEGER,
            parent_generation_id INTEGER,
            trim_start_ms INTEGER NOT NULL DEFAULT 0,
            trim_end_ms INTEGER,
            sync_offset_ms INTEGER NOT NULL DEFAULT 0,
            gain REAL NOT NULL DEFAULT 1.0,
            muted INTEGER NOT NULL DEFAULT 0,
            source_sha256 TEXT,
            FOREIGN KEY(generation_id) REFERENCES generations(id),
            FOREIGN KEY(source_id) REFERENCES sources(id),
            FOREIGN KEY(parent_generation_id) REFERENCES generations(id),
            CHECK((ref_kind='source' AND source_id IS NOT NULL AND parent_generation_id IS NULL) OR
                  (ref_kind='generation' AND source_id IS NULL AND parent_generation_id IS NOT NULL)),
            UNIQUE(generation_id, ordinal)
        );
        INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('schema_version', '1');
        """)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_file(path: Path) -> dict:
    command = ["ffprobe", "-v", "error", "-show_streams", "-show_format",
               "-of", "json", str(path)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if proc.returncode != 0:
        raise ValueError(proc.stderr.strip() or "ffprobe failed")
    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video:
        raise ValueError("file has no video stream")
    duration = video.get("duration") or data.get("format", {}).get("duration")
    return {
        "duration_ms": round(float(duration) * 1000) if duration else None,
        "width": video.get("width"), "height": video.get("height"),
        "has_audio": int(audio is not None),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name") if audio else None,
    }


def parse_json_body(handler: BaseHTTPRequestHandler) -> dict:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2 * 1024 * 1024:
            raise ValueError("invalid JSON body size")
        value = json.loads(handler.rfile.read(length).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON body") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON body must be an object")
    return value


def generation_row(generation_id: int) -> dict | None:
    with connect() as conn:
        generation = conn.execute(
            "SELECT * FROM generations WHERE id=?", (generation_id,)
        ).fetchone()
        if not generation:
            return None
        refs = conn.execute(
            "SELECT * FROM input_refs WHERE generation_id=? ORDER BY ordinal",
            (generation_id,),
        ).fetchall()
    result = row_json(generation)
    result["recipe"] = json.loads(result.pop("recipe_json"))
    result["input_refs"] = [row_json(ref) for ref in refs]
    return result


def lineage_payload(generation_id: int) -> dict | None:
    generation = generation_row(generation_id)
    if not generation:
        return None
    return {
        "protocol_version": 1,
        "generation_uuid": generation["generation_uuid"],
        "generation_number": generation["generation_number"],
        "recipe": generation["recipe"],
        "render_status": generation["render_status"],
        "render_path": generation["render_path"],
        "render_sha256": generation["render_sha256"],
        "inputs": [
            {"ordinal": ref["ordinal"], "ref_kind": ref["ref_kind"],
             "source_id": ref["source_id"], "parent_generation_id": ref["parent_generation_id"],
             "source_sha256": ref["source_sha256"],
             "trim_start_ms": ref["trim_start_ms"], "trim_end_ms": ref["trim_end_ms"],
             "sync_offset_ms": ref["sync_offset_ms"], "gain": ref["gain"],
             "muted": bool(ref["muted"])}
            for ref in generation["input_refs"]
        ],
        "analysis": {"status": "not_yet_analyzed"},
    }


def validate_recipe(payload: dict) -> tuple[dict, list[dict]]:
    inputs = payload.get("inputs")
    if not isinstance(inputs, list) or len(inputs) != 2:
        raise ValueError("recipe.inputs must contain exactly two inputs")
    recipe = payload.get("recipe")
    if recipe is None:
        recipe = {"schema_version": 1, "layout": {"type": "split_screen"},
                  "inputs": inputs}
    if not isinstance(recipe, dict):
        raise ValueError("recipe must be an object")
    clean: list[dict] = []
    for ordinal, item in enumerate(inputs):
        if not isinstance(item, dict):
            raise ValueError("each input must be an object")
        source_id = item.get("source_id")
        generation_id = item.get("generation_id")
        if source_id is None and generation_id is None:
            raise ValueError("each input requires source_id or generation_id")
        if source_id is not None and generation_id is not None:
            raise ValueError("each input cannot contain both source_id and generation_id")
        start = int(item.get("trim_start_ms", 0))
        end = item.get("trim_end_ms")
        end = None if end is None else int(end)
        sync = int(item.get("sync_offset_ms", 0))
        gain = float(item.get("gain", 1.0))
        muted = bool(item.get("muted", False))
        if start < 0 or (end is not None and end <= start):
            raise ValueError("trim range is invalid")
        if gain < 0 or gain > 8:
            raise ValueError("gain must be between 0 and 8")
        if source_id is not None:
            try:
                source_id = int(source_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("source_id must be an integer") from exc
            source = find_source(source_id)
            if not source:
                raise ValueError(f"source {source_id} does not exist")
            if source["status"] in ("missing", "changed"):
                raise ValueError(f"source {source_id} is {source['status']}")
            if end is not None and source["duration_ms"] and end > source["duration_ms"]:
                raise ValueError(f"input {ordinal} ends beyond source duration")
            clean.append({"ref_kind": "source", "source_id": source_id, "generation_id": None,
                          "trim_start_ms": start, "trim_end_ms": end, "sync_offset_ms": sync,
                          "gain": gain, "muted": muted, "source_sha256": source["sha256"]})
        else:
            try:
                generation_id = int(generation_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("generation_id must be an integer") from exc
            parent = generation_row(generation_id)
            if not parent or parent["render_status"] != "ok" or not parent["render_path"]:
                raise ValueError(f"generation {generation_id} is not a completed render")
            parent_path = Path(parent["render_path"])
            if not parent_path.is_file():
                raise ValueError(f"generation {generation_id} render is missing")
            if end is not None and parent["recipe"].get("duration_ms") and end > parent["recipe"]["duration_ms"]:
                raise ValueError(f"input {ordinal} ends beyond generation duration")
            clean.append({"ref_kind": "generation", "source_id": None, "generation_id": generation_id,
                          "trim_start_ms": start, "trim_end_ms": end, "sync_offset_ms": sync,
                          "gain": gain, "muted": muted, "source_sha256": parent["render_sha256"]})
    recipe = dict(recipe)
    recipe.setdefault("schema_version", 1)
    recipe["inputs"] = clean
    return recipe, clean


def validate_render_output(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("FFmpeg produced no output file")
    metadata = probe_file(path)
    if not metadata.get("has_audio"):
        raise ValueError("rendered output has no audio stream")
    return metadata


def tiktok_caption(base_caption: str, credits: list[dict]) -> str:
    lines = [base_caption.strip()] if base_caption.strip() else []
    for credit in credits:
        username = str(credit.get("creator_username", "")).strip().lstrip("@")
        url = str(credit.get("video_url", "")).strip()
        if username and url:
            lines.append(f"Credit: @{username} — {url}")
        elif username:
            lines.append(f"Credit: @{username}")
        elif url:
            lines.append(f"Credit: {url}")
    return "\n".join(lines)


def build_tiktok_packet(generation_id: int, payload: dict) -> tuple[Path, Path, dict]:
    if payload.get("rights_confirmed") is not True:
        raise ValueError("rights_confirmed=true is required before creating a TikTok export packet")
    generation = generation_row(generation_id)
    if not generation:
        raise ValueError("generation not found")
    credits = payload.get("credits", [])
    if not isinstance(credits, list) or len(credits) > 3:
        raise ValueError("credits must be a list with at most three entries")
    with connect() as conn:
        refs = conn.execute("SELECT * FROM input_refs WHERE generation_id=? ORDER BY ordinal", (generation_id,)).fetchall()
    if len(refs) != 2:
        raise ValueError("TikTok duet export requires exactly two inputs")
    specs: list[InputSpec] = []
    for ref in refs:
        if ref["ref_kind"] == "generation":
            parent = generation_row(int(ref["parent_generation_id"]))
            if not parent or parent["render_status"] != "ok" or not parent["render_path"]:
                raise ValueError("parent generation render is unavailable")
            input_path = Path(parent["render_path"])
            has_audio = bool(probe_file(input_path)["has_audio"])
        else:
            source = find_source(int(ref["source_id"]))
            if not source or source["status"] in ("missing", "changed"):
                raise ValueError("every source must be present and hash-verified")
            input_path = Path(source["managed_path"])
            has_audio = bool(source["has_audio"])
        specs.append(InputSpec(input_path, ref["trim_start_ms"], ref["trim_end_ms"],
                               ref["sync_offset_ms"], ref["gain"], bool(ref["muted"]), has_audio))
    output_name = f"duet_{int(generation['generation_number']):03d}.tiktok.mp4"
    final_path = RENDER_DIR / output_name
    temp_path = STAGING_DIR / f"{generation['generation_uuid']}.tiktok.tmp.mp4"
    command = build_tiktok_duet_command(specs, temp_path)
    proc = subprocess.run(command, capture_output=True, text=True, timeout=6 * 60 * 60, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "FFmpeg TikTok export failed")[-4000:])
    validate_render_output(temp_path)
    digest = sha256_file(temp_path)
    os.replace(temp_path, final_path)
    packet = {
        "protocol_version": 1,
        "platform": "tiktok",
        "posting_mode": "manual_review_only",
        "direct_posting_enabled": False,
        "generation_uuid": generation["generation_uuid"],
        "source_hashes": [ref["source_sha256"] for ref in refs],
        "format": {"width": 1080, "height": 1920, "aspect_ratio": "9:16", "fps": 30, "video": "H.264", "audio": "AAC", "faststart": True},
        "rights_confirmed": True,
        "caption": tiktok_caption(str(payload.get("caption", "")), credits),
        "credits": credits,
        "credit_instruction": "Review the caption and use TikTok's Mention > Videos credit control when posting. This app does not auto-post.",
        "copyright_note": "Only post media you own or have permission or another lawful basis to use.",
        "render_sha256": digest,
    }
    packet_path = RENDER_DIR / f"duet_{int(generation['generation_number']):03d}.tiktok.json"
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit("tiktok_export_packet_created", generation_id=generation_id, generation_number=generation["generation_number"], sha256=digest)
    return final_path, packet_path, packet


def run_render_job(generation_id: int) -> None:
    try:
        with connect() as conn:
            row = conn.execute("SELECT * FROM generations WHERE id=?", (generation_id,)).fetchone()
            refs = conn.execute("SELECT * FROM input_refs WHERE generation_id=? ORDER BY ordinal", (generation_id,)).fetchall()
        if not row:
            return
        specs: list[InputSpec] = []
        for ref in refs:
            if ref["ref_kind"] == "generation":
                parent = generation_row(int(ref["parent_generation_id"]))
                if not parent or parent["render_status"] != "ok" or not parent["render_path"]:
                    raise ValueError("parent generation render is unavailable")
                input_path = Path(parent["render_path"])
                metadata = probe_file(input_path)
                has_audio = bool(metadata["has_audio"])
            else:
                source = find_source(int(ref["source_id"]))
                if not source:
                    raise ValueError("render source no longer exists")
                input_path = Path(source["managed_path"])
                has_audio = bool(source["has_audio"])
            specs.append(InputSpec(input_path, ref["trim_start_ms"], ref["trim_end_ms"],
                                   ref["sync_offset_ms"], ref["gain"], bool(ref["muted"]), has_audio))
        output_name = f"duet_{int(row['generation_number']):03d}.mp4"
        final_path = RENDER_DIR / output_name
        # Keep the final extension visible to FFmpeg for muxer autodetection;
        # the file remains private in staging until atomic publication.
        temp_path = STAGING_DIR / f"{row['generation_uuid']}.tmp.mp4"
        temp_path.unlink(missing_ok=True)
        command = build_split_screen_command(specs, temp_path)
        audit("render_started", generation_id=generation_id, generation_number=row["generation_number"])
        with connect() as conn:
            conn.execute("UPDATE generations SET render_status='running', error=NULL WHERE id=?", (generation_id,))
        proc = subprocess.run(command, capture_output=True, text=True, timeout=6 * 60 * 60, check=False)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or "FFmpeg failed")[-4000:])
        validate_render_output(temp_path)
        digest = sha256_file(temp_path)
        os.replace(temp_path, final_path)
        with connect() as conn:
            conn.execute("UPDATE generations SET render_status='ok', render_path=?, render_sha256=?, rendered_at=?, error=NULL WHERE id=?",
                         (str(final_path), digest, utc_now(), generation_id))
        audit("render_succeeded", generation_id=generation_id, generation_number=row["generation_number"], sha256=digest)
    except Exception as exc:
        audit("render_failed", generation_id=generation_id, error=str(exc))
        with connect() as conn:
            conn.execute("UPDATE generations SET render_status='failed', error=? WHERE id=?", (str(exc)[-4000:], generation_id))
    finally:
        with RENDER_LOCK:
            RENDER_THREADS.pop(generation_id, None)


def safe_filename(name: str) -> str:
    base = Path(name).name.strip() or "imported_video"
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    return "".join(ch if ch in allowed else "_" for ch in base)[:180]


def json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True).encode("utf-8")


def row_json(row: sqlite3.Row) -> dict:
    return dict(row)


def find_source(source_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()


class Handler(BaseHTTPRequestHandler):
    server_version = "DuetConversationStudio/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"error": message}, status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/api/status":
                self.send_json(self.status_payload()); return
            if path == "/api/sources":
                with connect() as conn:
                    rows = conn.execute("SELECT * FROM sources ORDER BY imported_at DESC").fetchall()
                self.send_json({"sources": [row_json(row) for row in rows]}); return
            if path == "/api/generations":
                with connect() as conn:
                    rows = conn.execute("SELECT id FROM generations ORDER BY generation_number DESC").fetchall()
                self.send_json({"generations": [generation_row(row["id"]) for row in rows]}); return
            if path.startswith("/api/generations/") and path.endswith("/lineage"):
                generation_id = int(path.split("/")[3])
                payload = lineage_payload(generation_id)
                if not payload:
                    self.send_error_json(404, "generation not found"); return
                self.send_json(payload); return
            if path.startswith("/api/generations/"):
                parts = path.split("/")
                generation_id = int(parts[3])
                if len(parts) in (5, 6) and parts[4] == "render" and (len(parts) == 5 or parts[5] == "status"):
                    generation = generation_row(generation_id)
                    if not generation:
                        self.send_error_json(404, "generation not found"); return
                    self.send_json({"id": generation_id, "render_status": generation["render_status"],
                                    "render_path": generation["render_path"], "error": generation["error"]}); return
                generation = generation_row(generation_id)
                if not generation:
                    self.send_error_json(404, "generation not found"); return
                self.send_json(generation); return
            if path.startswith("/api/sources/"):
                source_id = int(path.rsplit("/", 1)[1])
                row = find_source(source_id)
                if not row:
                    self.send_error_json(404, "source not found"); return
                self.send_json(row_json(row)); return
            if path.startswith("/projects/sources/"):
                name = Path(path.rsplit("/", 1)[1]).name
                file_path = SOURCE_DIR / name
                if not file_path.is_file():
                    self.send_error_json(404, "file not found"); return
                self.send_file(file_path); return
            if path.startswith("/projects/renders/"):
                name = Path(path.rsplit("/", 1)[1]).name
                file_path = RENDER_DIR / name
                if not file_path.is_file():
                    self.send_error_json(404, "file not found"); return
                self.send_file(file_path); return
            if path == "/" or not path.startswith("/api/"):
                self.send_static(path); return
            self.send_error_json(404, "not found")
        except (ValueError, IndexError):
            self.send_error_json(400, "invalid request")
        except Exception as exc:
            audit("request_error", path=path, error=str(exc))
            self.send_error_json(500, "internal server error")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/sources":
                self.import_source(); return
            if parsed.path == "/api/generations":
                self.create_generation(); return
            if parsed.path == "/api/restore/lineage":
                self.restore_lineage(); return
            if parsed.path.startswith("/api/generations/") and parsed.path.endswith("/export/tiktok"):
                generation_id = int(parsed.path.split("/")[3])
                video_path, packet_path, packet = build_tiktok_packet(generation_id, parse_json_body(self))
                self.send_json({"platform": "tiktok", "video_path": str(video_path), "credit_packet_path": str(packet_path), "packet": packet}, 201); return
            if parsed.path.startswith("/api/generations/") and parsed.path.endswith("/render"):
                generation_id = int(parsed.path.split("/")[3])
                self.start_render(generation_id); return
            if parsed.path.startswith("/api/sources/") and parsed.path.endswith("/verify"):
                source_id = int(parsed.path.split("/")[3])
                self.verify_source(source_id); return
            self.send_error_json(404, "not found")
        except ValueError as exc:
            self.send_error_json(400, str(exc))
        except Exception as exc:
            audit("request_error", path=parsed.path, error=str(exc))
            self.send_error_json(500, "internal server error")

    def status_payload(self) -> dict:
        def version(name: str) -> dict:
            path = shutil.which(name)
            if not path: return {"present": False}
            proc = subprocess.run([name, "-version"], capture_output=True, text=True, timeout=3, check=False)
            first = (proc.stdout or proc.stderr).splitlines()
            return {"present": True, "path": path, "version": first[0] if first else None}
        with connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        return {"ok": True, "service": "Duet Conversation Studio", "sources": count,
                "tools": {name: version(name) for name in ("ffmpeg", "ffprobe")}}

    def import_source(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_UPLOAD_BYTES:
            raise ValueError("invalid or oversized upload")
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("expected multipart/form-data")
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={
            "REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": str(content_length),
        })
        field = form["video"] if "video" in form else None
        if field is None or not getattr(field, "file", None):
            raise ValueError("missing video field")
        original_name = safe_filename(getattr(field, "filename", "imported_video"))
        token = uuid.uuid4().hex
        managed_name = f"{token}_{original_name}"
        staging = ROOT / "projects" / "staging" / f"{token}.upload"
        managed = SOURCE_DIR / managed_name
        with staging.open("wb") as out:
            shutil.copyfileobj(field.file, out, length=1024 * 1024)
        try:
            if staging.stat().st_size == 0:
                raise ValueError("empty upload")
            metadata = probe_file(staging)
            digest = sha256_file(staging)
            os.replace(staging, managed)
            source_uuid = f"src-{uuid.uuid4()}"
            now = utc_now()
            with connect() as conn:
                cur = conn.execute("""INSERT INTO sources
                    (source_uuid, original_name, managed_path, original_path, sha256,
                     size_bytes, duration_ms, width, height, has_audio, video_codec,
                     audio_codec, status, imported_at, last_verified_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?)""",
                    (source_uuid, original_name, str(managed), None, digest,
                     managed.stat().st_size, metadata["duration_ms"], metadata["width"],
                     metadata["height"], metadata["has_audio"], metadata["video_codec"],
                     metadata["audio_codec"], now, now))
                source_id = cur.lastrowid
                row = conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
            audit("source_imported", source_id=source_id, sha256=digest, size_bytes=managed.stat().st_size)
            self.send_json(row_json(row), 201)
        finally:
            staging.unlink(missing_ok=True)

    def verify_source(self, source_id: int) -> None:
        row = find_source(source_id)
        if not row: self.send_error_json(404, "source not found"); return
        path = Path(row["managed_path"])
        now = utc_now()
        if not path.is_file():
            status, error = "missing", "managed file not found"
        else:
            try:
                digest = sha256_file(path)
                status = "ok" if digest == row["sha256"] else "changed"
                error = None if status == "ok" else "sha256 mismatch"
            except OSError as exc:
                status, error = "unverified", str(exc)
        with connect() as conn:
            conn.execute("UPDATE sources SET status=?, last_verified_at=?, last_error=? WHERE id=?",
                         (status, now, error, source_id))
            updated = conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        audit("source_verified", source_id=source_id, status=status)
        self.send_json(row_json(updated))

    def create_generation(self) -> None:
        payload = parse_json_body(self)
        recipe, inputs = validate_recipe(payload)
        now = utc_now()
        with connect() as conn:
            number = conn.execute("SELECT COALESCE(MAX(generation_number), 0) + 1 FROM generations").fetchone()[0]
            generation_uuid = f"gen-{uuid.uuid4()}"
            cur = conn.execute("INSERT INTO generations(generation_uuid, generation_number, recipe_json, created_at) VALUES (?, ?, ?, ?)",
                               (generation_uuid, number, json.dumps(recipe, sort_keys=True), now))
            generation_id = cur.lastrowid
            for ordinal, item in enumerate(inputs):
                conn.execute("""INSERT INTO input_refs
                    (generation_id, ordinal, ref_kind, source_id, trim_start_ms,
                     trim_end_ms, sync_offset_ms, gain, muted, source_sha256,
                     parent_generation_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (generation_id, ordinal, item["ref_kind"], item["source_id"], item["trim_start_ms"],
                     item["trim_end_ms"], item["sync_offset_ms"], item["gain"],
                     int(item["muted"]), item["source_sha256"], item["generation_id"]))
        audit("generation_created", generation_id=generation_id, generation_number=number)
        self.send_json(generation_row(generation_id), 201)

    def start_render(self, generation_id: int) -> None:
        generation = generation_row(generation_id)
        if not generation:
            self.send_error_json(404, "generation not found"); return
        if generation["render_status"] == "ok":
            self.send_error_json(409, "generation already has a successful render; create a new generation for a new recipe")
            return
        with RENDER_LOCK:
            existing = RENDER_THREADS.get(generation_id)
            if existing and existing.is_alive():
                self.send_json({"id": generation_id, "render_status": "running"}, 202); return
            thread = threading.Thread(target=run_render_job, args=(generation_id,), daemon=True)
            RENDER_THREADS[generation_id] = thread
            thread.start()
        self.send_json({"id": generation_id, "render_status": "queued"}, 202)

    def restore_lineage(self) -> None:
        payload = parse_json_body(self)
        generation_uuid = payload.get("generation_uuid")
        if not isinstance(generation_uuid, str) or not generation_uuid:
            raise ValueError("generation_uuid is required")
        with connect() as conn:
            existing = conn.execute("SELECT id FROM generations WHERE generation_uuid=?", (generation_uuid,)).fetchone()
            if existing:
                restored = generation_row(existing["id"])
                self.send_json({"restored": False, "duplicate": True, "generation": restored}); return
        inputs = payload.get("inputs")
        if not isinstance(inputs, list) or len(inputs) != 2:
            raise ValueError("lineage restore requires exactly two inputs")
        refs: list[tuple] = []
        for item in inputs:
            digest = item.get("source_sha256") if isinstance(item, dict) else None
            if not isinstance(digest, str):
                raise ValueError("each input requires source_sha256")
            with connect() as conn:
                source = conn.execute("SELECT id, sha256 FROM sources WHERE sha256=?", (digest,)).fetchone()
            if not source:
                self.send_error_json(409, f"source with hash {digest} is unavailable"); return
            refs.append((source["id"], item))
        recipe = payload.get("recipe")
        if not isinstance(recipe, dict):
            raise ValueError("recipe is required")
        with connect() as conn:
            number = conn.execute("SELECT COALESCE(MAX(generation_number), 0) + 1 FROM generations").fetchone()[0]
            cur = conn.execute("INSERT INTO generations(generation_uuid, generation_number, recipe_json, render_status, render_path, render_sha256, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (generation_uuid, number, json.dumps(recipe, sort_keys=True), payload.get("render_status", "draft"), payload.get("render_path"), payload.get("render_sha256"), utc_now()))
            generation_id = cur.lastrowid
            for ordinal, (source_id, item) in enumerate(refs):
                conn.execute("INSERT INTO input_refs(generation_id, ordinal, ref_kind, source_id, trim_start_ms, trim_end_ms, sync_offset_ms, gain, muted, source_sha256) VALUES (?, ?, 'source', ?, ?, ?, ?, ?, ?, ?)",
                             (generation_id, ordinal, source_id, int(item.get("trim_start_ms", 0)), item.get("trim_end_ms"), int(item.get("sync_offset_ms", 0)), float(item.get("gain", 1.0)), int(bool(item.get("muted", False))), item["source_sha256"]))
        audit("lineage_restored", generation_id=generation_id, generation_uuid=generation_uuid)
        self.send_json({"restored": True, "duplicate": False, "generation": generation_row(generation_id)}, 201)

    def send_file(self, path: Path) -> None:
        size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.end_headers()
        with path.open("rb") as handle:
            shutil.copyfileobj(handle, self.wfile)

    def send_static(self, path: str) -> None:
        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (PUBLIC_DIR / relative).resolve()
        if PUBLIC_DIR.resolve() not in target.parents and target != PUBLIC_DIR.resolve():
            self.send_error_json(403, "forbidden"); return
        if not target.is_file():
            self.send_error_json(404, "not found"); return
        self.send_file(target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    ensure_layout()
    init_db()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    audit("server_started", host=args.host, port=args.port)
    print(f"Duet Conversation Studio listening at http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        audit("server_stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
